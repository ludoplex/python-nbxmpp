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

from nbxmpp.protocol import NS_SIGNED
from nbxmpp.structs import StanzaHandler

log = logging.getLogger('nbxmpp.m.signed')


class Signed:
    def __init__(self, client):
        self._client = client
        self.handlers = [
            StanzaHandler(name='presence',
                          callback=self._process_signed,
                          ns=NS_SIGNED,
                          priority=15)
        ]

    @staticmethod
    def _process_signed(_con, stanza, properties):
        signed = stanza.getTag('x', namespace=NS_SIGNED)
        if signed is None:
            return

        properties.signed = signed.getData()
