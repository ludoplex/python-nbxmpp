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

from nbxmpp.protocol import NS_BLOCKING
from nbxmpp.protocol import Iq
from nbxmpp.protocol import isResultNode
from nbxmpp.structs import BlockingListResult
from nbxmpp.structs import CommonResult
from nbxmpp.util import call_on_response
from nbxmpp.util import callback

log = logging.getLogger('nbxmpp.m.blocking')


class Blocking:
    def __init__(self, client):
        self._client = client
        self.handlers = []

    @call_on_response('_blocking_list_received')
    def get_blocking_list(self):
        iq = Iq('get', NS_BLOCKING)
        iq.setQuery('blocklist')
        return iq

    @callback
    def _blocking_list_received(self, stanza):
        blocked = []
        if not isResultNode(stanza):
            log.info('Error: %s', stanza.getErrorMsg())
            return BlockingListResult(blocking_list=blocked,
                                      error=stanza.getErrorMsg())

        blocklist = stanza.getTag('blocklist', namespace=NS_BLOCKING)
        for item in blocklist.getTags('item'):
            blocked.append(item.getAttr('jid'))

        log.info('Received blocking list: %s', blocked)
        return BlockingListResult(blocking_list=blocked)

    @call_on_response('_default_response')
    def block(self, jids):
        log.info('Block: %s', jids)
        iq = Iq('set', NS_BLOCKING)
        query = iq.setQuery(name='block')
        for jid in jids:
            query.addChild(name='item', attrs={'jid': jid})
        return iq

    @call_on_response('_default_response')
    def unblock(self, jids):
        log.info('Unblock: %s', jids)
        iq = Iq('set', NS_BLOCKING)
        query = iq.setQuery(name='unblock')
        for jid in jids:
            query.addChild(name='item', attrs={'jid': jid})
        return iq

    @callback
    def _default_response(self, stanza):
        if not isResultNode(stanza):
            log.info('Error: %s', stanza.getErrorMsg())
            return CommonResult(jid=stanza.getFrom(),
                                error=stanza.getErrorMsg())
        return CommonResult(jid=stanza.getFrom())
