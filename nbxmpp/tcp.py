# Copyright (C) 2020 Philipp Hörist <philipp AT hoerist.com>
#
# This file is part of nbxmpp.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; If not, see <http://www.gnu.org/licenses/>.

import logging
import struct
from collections import deque

from gi.repository import GLib
from gi.repository import Gio
from gi.repository import GObject

from nbxmpp.const import TCPState
from nbxmpp.const import ConnectionType
from nbxmpp.util import utf8_decode
from nbxmpp.util import convert_tls_error_flags
from nbxmpp.connection import Connection

log = logging.getLogger('nbxmpp.tcp')

READ_BUFFER_SIZE = 8192


class TCPConnection(Connection):
    def __init__(self, *args, **kwargs):
        Connection.__init__(self, *args, **kwargs)

        self._client = Gio.SocketClient.new()

        if self._address.proxy is not None:
            self._proxy_resolver = self._address.proxy.get_resolver()
            self._client.set_proxy_resolver(self._proxy_resolver)

        GObject.Object.connect(self._client, 'event', self._on_event)

        self._con = None

        self._read_buffer = b''

        self._write_queue = deque([])
        self._write_stanza_buffer = None

        self._connect_cancellable = Gio.Cancellable()
        self._read_cancellable = Gio.Cancellable()

        self._input_closed = False
        self._output_closed = False

        self._keepalive_id = None

    def connect(self):
        self.state = TCPState.CONNECTING

        if self._address.is_service:
            self._client.connect_to_service_async(self._address.domain,
                                                  self._address.service,
                                                  self._connect_cancellable,
                                                  self._on_connect_finished,
                                                  None)
        elif self._address.is_host:
            self._client.connect_to_host_async(self._address.host,
                                               0,
                                               self._connect_cancellable,
                                               self._on_connect_finished,
                                               None)

        else:
            raise ValueError('Invalid Address')

    def _on_event(self, _socket_client, event, _connectable, connection):
        if event == Gio.SocketClientEvent.CONNECTING:
            remote_address = connection.get_remote_address()
            use_proxy = self._address.proxy is not None
            target = 'proxy' if use_proxy else self._address.domain
            log.info('Connecting to %s (%s)',
                     target,
                     remote_address.to_string())

    def _check_certificate(self, _connection, certificate, errors):
        self._peer_certificate = certificate
        self._peer_certificate_errors = convert_tls_error_flags(errors)

        if self._accept_certificate():
            return True

        self.notify('bad-certificate')
        return False

    def _on_certificate_set(self, connection, _param):
        self._peer_certificate = connection.props.peer_certificate
        self._peer_certificate_errors = convert_tls_error_flags(
            connection.props.peer_certificate_errors)
        self.notify('certificate-set')

    def _on_connect_finished(self, client, result, _user_data):
        try:
            if self._address.proxy is not None:
                self._con = client.connect_to_host_finish(result)
            elif self._address.is_service:
                self._con = client.connect_to_service_finish(result)
            elif self._address.is_host:
                self._con = client.connect_to_host_finish(result)
            else:
                raise ValueError('Address must be a service or host')
        except GLib.Error as error:
            log.error('Connect Error: %s', error)
            self._finalize('connection-failed')
            return

        self._con.set_graceful_disconnect(True)
        self._con.get_socket().set_keepalive(True)

        self.state = TCPState.CONNECTED

        use_proxy = self._address.proxy is not None
        target = 'proxy' if use_proxy else self._address.domain
        log.info('Connected to %s (%s)',
                 target,
                 self._con.get_remote_address().to_string())

        self._on_connected()

    def _on_connected(self):
        self.notify('connected')
        self._read_async()

    def _remove_keepalive_timer(self):
        if self._keepalive_id is not None:
            GLib.source_remove(self._keepalive_id)
            self._keepalive_id = None

    def _renew_keepalive_timer(self):
        self._remove_keepalive_timer()
        self._keepalive_id = GLib.timeout_add_seconds(5, self._send_keepalive)

    def _send_keepalive(self):
        log.info('Send keepalive')
        self._keepalive_id = None
        if not self._con.get_output_stream().has_pending():
            self._write_all_async(' '.encode())

    def start_tls_negotiation(self):
        log.info('Start TLS negotiation')
        remote_address = self._con.get_remote_address()
        identity = Gio.NetworkAddress.new(self._address.domain,
                                          remote_address.props.port)

        tls_client = Gio.TlsClientConnection.new(self._con, identity)

        if self._address.type == ConnectionType.DIRECT_TLS:
            tls_client.set_advertised_protocols(['xmpp-client'])
        tls_client.set_rehandshake_mode(Gio.TlsRehandshakeMode.NEVER)
        tls_client.set_validation_flags(Gio.TlsCertificateFlags.VALIDATE_ALL)
        tls_client.connect('accept-certificate', self._check_certificate)
        tls_client.connect('notify::peer-certificate', self._on_certificate_set)

        # This Wraps the Gio.TlsClientConnection and the Gio.Socket together
        # so we get back a Gio.SocketConnection
        self._con = Gio.TcpWrapperConnection.new(tls_client,
                                                 self._con.get_socket())

    def _read_async(self):
        if self._input_closed:
            return

        self._con.get_input_stream().read_bytes_async(
            READ_BUFFER_SIZE,
            GLib.PRIORITY_DEFAULT,
            self._read_cancellable,
            self._on_read_async_finish,
            None)

    def _on_read_async_finish(self, stream, result, _user_data):
        try:
            data = stream.read_bytes_finish(result)
        except GLib.Error as error:
            quark = GLib.quark_try_string('g-io-error-quark')
            if error.matches(quark, Gio.IOErrorEnum.CANCELLED):
                if self._input_closed:
                    return

            quark = GLib.quark_try_string('g-tls-error-quark')
            if error.matches(quark, Gio.TlsError.EOF):
                log.info('Incoming stream closed: TLS EOF')
                self._finalize('disconnected')
                return

            if error.matches(quark, Gio.TlsError.BAD_CERTIFICATE):
                log.info('Certificate Error: %s', error)
                self._finalize('disconnected')
                return

            log.error('Read Error: %s', error)
            return

        data = data.get_data()
        if not data:
            if self._state == TCPState.DISCONNECTING:
                log.info('Reveived zero data on _read_async()')
                self._finalize('disconnected')
            else:
                log.warning('Reveived zero data on _read_async()')
            return

        self._renew_keepalive_timer()

        self._read_buffer += data
        data, self._read_buffer = utf8_decode(self._read_buffer)

        self._log_stanza(data, received=True)
        self.notify('data-received', data)

        self._read_async()

    def _write_stanzas(self):
        self._write_stanza_buffer = self._write_queue
        self._write_queue = deque([])
        data = ''.join(map(str, self._write_stanza_buffer)).encode()
        self._write_all_async(data)

    def _write_all_async(self, data):
        # We have to pass data to the callback, because GLib takes no
        # reference on the passed data and python would gc collect it
        # bevor GLib has a chance to write it to the stream
        self._con.get_output_stream().write_all_async(
            data,
            GLib.PRIORITY_DEFAULT,
            None,
            self._on_write_all_async_finished,
            data)

    def _on_write_all_async_finished(self, stream, result, data):
        try:
            stream.write_all_finish(result)
        except GLib.Error as error:
            quark = GLib.quark_try_string('g-tls-error-quark')
            if error.matches(quark, Gio.TlsError.BAD_CERTIFICATE):
                self._write_stanza_buffer = None
                return

            log.error('Write Error: %s', error)
            return

        self._renew_keepalive_timer()

        data = data.decode()
        if data == ' ':
            # keepalive whitespace
            return

        for stanza in self._write_stanza_buffer:
            self._log_stanza(stanza, received=False)
        self._write_stanza_buffer = None

        self.notify('data-sent', data)

        if self._output_closed and not self._write_queue:
            self._check_for_shutdown()
            return

        if self._write_queue:
            self._write_stanzas()

    def send(self, stanza, now=False):
        if self._state in (TCPState.DISCONNECTED, TCPState.DISCONNECTING):
            log.warning('send() not possible in state: %s', self._state)
            return

        if now:
            self._write_queue.appendleft(stanza)
        else:
            self._write_queue.append(stanza)

        if not self._con.get_output_stream().has_pending():
            self._write_stanzas()

    def disconnect(self):
        self._remove_keepalive_timer()
        if self.state == TCPState.CONNECTING:
            self.state = TCPState.DISCONNECTING
            self._connect_cancellable.cancel()
            return

        if self._state in (TCPState.DISCONNECTED, TCPState.DISCONNECTING):
            log.warning('Called disconnect on state: %s', self._state)
            return

        self.state = TCPState.DISCONNECTING
        self._finalize('disconnected')

    def _check_for_shutdown(self):
        if self._input_closed and self._output_closed:
            self._finalize('disconnected')

    def shutdown_input(self):
        self._remove_keepalive_timer()
        log.info('Shutdown input')
        self._input_closed = True
        self._read_cancellable.cancel()
        self._check_for_shutdown()

    def shutdown_output(self):
        self._remove_keepalive_timer()
        self.state = TCPState.DISCONNECTING
        log.info('Shutdown output')
        self._output_closed = True

    def _finalize(self, signal_name):
        self._remove_keepalive_timer()
        if self._con is not None:
            try:
                self._con.get_socket().shutdown(True, True)
            except GLib.Error as error:
                log.info(error)
        self.state = TCPState.DISCONNECTED
        self.notify(signal_name)
        self.destroy()

    def destroy(self):
        super().destroy()
        self._con = None
        self._client = None