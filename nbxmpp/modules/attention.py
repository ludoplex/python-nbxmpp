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

from nbxmpp.protocol import NS_ATTENTION
from nbxmpp.protocol import NS_DELAY2
from nbxmpp.structs import StanzaHandler

log = logging.getLogger('nbxmpp.m.attention')


class Attention:
    def __init__(self, client):
        self._client = client
        self.handlers = [
            StanzaHandler(name='message',
                          callback=self._process_message_attention,
                          ns=NS_ATTENTION,
                          priority=15),
        ]

    def _process_message_attention(self, _con, stanza, properties):
        attention = stanza.getTag('attention', namespace=NS_ATTENTION)
        if attention is None:
            return

        if properties.is_mam_message:
            return

        if properties.is_carbon_message and properties.carbon.is_sent:
            return

        if stanza.getTag('delay', namespace=NS_DELAY2) is not None:
            return

        properties.attention = True