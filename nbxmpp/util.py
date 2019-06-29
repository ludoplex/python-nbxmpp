# Copyright (C) 2018 Philipp Hörist <philipp AT hoerist.com>
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
import socket
import base64
import weakref
import hashlib
from functools import wraps
from functools import lru_cache

import precis_i18n.codec

from nbxmpp.protocol import JID
from nbxmpp.protocol import InvalidJid
from nbxmpp.protocol import DiscoInfoMalformed
from nbxmpp.stringprepare import nameprep
from nbxmpp.structs import Properties
from nbxmpp.structs import IqProperties
from nbxmpp.structs import MessageProperties
from nbxmpp.structs import PresenceProperties
from nbxmpp.structs import CommonError
from nbxmpp.third_party.hsluv import hsluv_to_rgb

log = logging.getLogger('nbxmpp.util')


def b64decode(data, return_type=str):
    if not data:
        raise ValueError('No data to decode')
    if isinstance(data, str):
        data = data.encode()
    result = base64.b64decode(data)
    if return_type == bytes:
        return result
    return result.decode()


def b64encode(data, return_type=str):
    if not data:
        raise ValueError('No data to encode')
    if isinstance(data, str):
        data = data.encode()
    result = base64.b64encode(data)
    if return_type == bytes:
        return result
    return result.decode()


def get_properties_struct(name):
    if name == 'message':
        return MessageProperties()
    if name == 'iq':
        return IqProperties()
    if name == 'presence':
        return PresenceProperties()
    return Properties()


def validate_jid(jid_string):
    jid = JID(jid_string)
    return prep(jid.getNode() or None,
                jid.getDomain() or None,
                jid.getResource() or None)


def prep(user, server, resource):
    """
    Perform stringprep on all JID fragments and return the full jid
    """

    ip_address = False

    try:
        socket.inet_aton(server)
        ip_address = True
    except socket.error:
        pass

    if not ip_address and hasattr(socket, 'inet_pton'):
        try:
            socket.inet_pton(socket.AF_INET6, server.strip('[]'))
            server = '[%s]' % server.strip('[]')
            ip_address = True
        except (socket.error, ValueError):
            pass

    if not ip_address:
        if server is not None:
            if server.endswith('.'):  # RFC7622, 3.2
                server = server[:-1]
            if not server or len(server.encode('utf-8')) > 1023:
                raise InvalidJid('Server must be between 1 and 1023 bytes')
            try:
                server = nameprep.prepare(server)
            except UnicodeError:
                raise InvalidJid('Invalid character in hostname')
        else:
            raise InvalidJid('Server address required')

    if user is not None:
        if not user or len(user.encode('utf-8')) > 1023:
            raise InvalidJid('Username must be between 1 and 1023 bytes')
        try:
            user = user.encode('UsernameCaseMapped').decode('utf-8')
        except UnicodeError:
            raise InvalidJid('Invalid character in username')
    else:
        user = None

    if resource is not None:
        if not resource or len(resource.encode('utf-8')) > 1023:
            raise InvalidJid('Resource must be between 1 and 1023 bytes')
        try:
            resource = resource.encode('OpaqueString').decode('utf-8')
        except UnicodeError:
            raise InvalidJid('Invalid character in resource')
    else:
        resource = None

    if user:
        if resource:
            return '%s@%s/%s' % (user, server, resource)
        return '%s@%s' % (user, server)

    if resource:
        return '%s/%s' % (server, resource)
    return server


def call_on_response(cb):
    def response_decorator(func):
        @wraps(func)
        def func_wrapper(self, *args, **kwargs):
            user_data = kwargs.pop('user_data', None)
            callback_ = kwargs.pop('callback', None)

            stanza = func(self, *args, **kwargs)
            if isinstance(stanza, tuple):
                stanza, attrs = stanza
            else:
                stanza, attrs = stanza, {}

            if user_data is not None:
                attrs['user_data'] = user_data

            if callback_ is not None:
                attrs['callback'] = weakref.WeakMethod(callback_)

            self._client.SendAndCallForResponse(stanza,
                                                getattr(self, cb),
                                                attrs)
        return func_wrapper
    return response_decorator


def callback(func):
    @wraps(func)
    def func_wrapper(self, _con, stanza, **kwargs):
        cb = kwargs.pop('callback', None)
        user_data = kwargs.pop('user_data', None)

        result = func(self, stanza, **kwargs)
        if cb is not None and cb() is not None:
            if user_data is not None:
                cb()(result, user_data)
            else:
                cb()(result)
    return func_wrapper


def from_xs_boolean(value):
    if value in ('1', 'true', 'True'):
        return True

    if value in ('0', 'false', 'False', ''):
        return False

    raise ValueError('Cant convert %s to python boolean' % value)


def to_xs_boolean(value):
    # Convert to xs:boolean ('true', 'false')
    # from a python boolean (True, False) or None
    if value is True:
        return 'true'

    if value is False:
        return 'false'

    if value is None:
        return 'false'

    raise ValueError(
        'Cant convert %s to xs:boolean' % value)


def raise_error(log_method, stanza, type_=None, message=None):
    if message is not None:
        message = str(message)
    if type_ is None:
        type_ = stanza.getError()
        message = stanza.getErrorMsg()
    jid = stanza.getFrom()
    error = CommonError(type_, message, jid)
    log_method(error)
    if log_method.__name__ in ('warning', 'error'):
        log_method(stanza)
    return error


def is_error_result(result):
    return isinstance(result, CommonError)


def clip_rgb(red, green, blue):
    return (
        min(max(red, 0), 1),
        min(max(green, 0), 1),
        min(max(blue, 0), 1),
    )


@lru_cache(maxsize=1024)
def text_to_color(text, background_color):
    # background color = (rb, gb, bb)
    hash_ = hashlib.sha1()
    hash_.update(text.encode())
    hue = int.from_bytes(hash_.digest()[:2], 'little') / 65536

    red, green, blue = clip_rgb(*hsluv_to_rgb((hue * 360, 100, 50)))

    rb, gb, bb = background_color

    rb_inv = 1 - rb
    gb_inv = 1 - gb
    bb_inv = 1 - bb

    rc = 0.2 * rb_inv + 0.8 * red
    gc = 0.2 * gb_inv + 0.8 * green
    bc = 0.2 * bb_inv + 0.8 * blue

    return rc, gc, bc


def compute_caps_hash(info):
    """
    Compute caps hash according to XEP-0115, V1.5
    https://xmpp.org/extensions/xep-0115.html#ver-proc

    :param: info    DiscoInfo
    """
    # Initialize an empty string S.
    string_ = ''

    # Sort the service discovery identities by category and then by type and
    # then by xml:lang (if it exists), formatted as
    # CATEGORY '/' [TYPE] '/' [LANG] '/' [NAME]. Note that each slash is
    # included even if the LANG or NAME is not included (in accordance with
    # XEP-0030, the category and type MUST be included).
    # For each identity, append the 'category/type/lang/name' to S, followed by
    # the '<' character.
    # Sort the supported service discovery features.

    def sort_identities_key(i):
        return (i.category, i.type, i.lang or '')

    identities = sorted(info.identities, key=sort_identities_key)
    for identity in identities:
        string_ += '%s<' % str(identity)

    # If the response includes more than one service discovery identity with
    # the same category/type/lang/name, consider the entire response
    # to be ill-formed.
    if len(set(identities)) != len(identities):
        raise DiscoInfoMalformed('Non-unique identity found')

    # Sort the supported service discovery features.
    # For each feature, append the feature to S, followed by the '<' character.
    features = sorted(info.features)
    for feature in features:
        string_ += '%s<' % feature

    # If the response includes more than one service discovery feature with the
    # same XML character data, consider the entire response to be ill-formed.
    if len(set(features)) != len(features):
        raise DiscoInfoMalformed('Non-unique feature found')

    # If the response includes more than one extended service discovery
    # information form with the same FORM_TYPE or the FORM_TYPE field contains
    # more than one <value/> element with different XML character data,
    # consider the entire response to be ill-formed.

    # If the response includes an extended service discovery information form
    # where the FORM_TYPE field is not of type "hidden" or the form does not
    # include a FORM_TYPE field, ignore the form but continue processing.

    dataforms = []
    form_type_values = []
    for dataform in info.dataforms:
        form_type = dataform.vars.get('FORM_TYPE')
        if form_type is None:
            # Ignore dataform because of missing FORM_TYPE
            continue
        if form_type.type_ != 'hidden':
            # Ignore dataform because of wrong type
            continue

        values = form_type.getTags('value')
        if len(values) != 1:
            raise DiscoInfoMalformed('Form should have exactly '
                                     'one FORM_TYPE value')
        value = values[0].getData()

        dataforms.append(dataform)
        form_type_values.append(value)

    if len(set(form_type_values)) != len(form_type_values):
        raise DiscoInfoMalformed('Non-unique FORM_TYPE value found')

    # If the service discovery information response includes XEP-0128 data
    # forms, sort the forms by the FORM_TYPE (i.e., by the XML character data
    # of the <value/> element).

    # For each extended service discovery information form:
    #   - Append the XML character data of the FORM_TYPE field's <value/>
    #     element, followed by the '<' character.
    #   - Sort the fields by the value of the "var" attribute.
    #   - For each field other than FORM_TYPE:
    #       - Append the value of the "var" attribute, followed by the
    #         '<' character.
    #       - Sort values by the XML character data of the <value/> element.
    #       - For each <value/> element, append the XML character data,
    #         followed by the '<' character.

    def sort_dataforms_key(dataform):
        return dataform['FORM_TYPE'].getTagData('value')

    dataforms = sorted(dataforms, key=sort_dataforms_key)
    for dataform in dataforms:
        string_ += '%s<' % dataform['FORM_TYPE'].getTagData('value')

        fields = {}
        for field in dataform.iter_fields():
            if field.var == 'FORM_TYPE':
                continue
            values = field.getTags('value')
            fields[field.var] = sorted([value.getData() for value in values])

        for var in sorted(fields.keys()):
            string_ += '%s<' % var
            for value in fields[var]:
                string_ += '%s<' % value

    hash_ = hashlib.sha1(string_.encode())
    return b64encode(hash_.digest())
