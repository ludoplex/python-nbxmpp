# Copyright (C) 2018 Philipp Hörist <philipp AT hoerist.com>
#
# This file is part of nbxmpp.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; If not, see <http://www.gnu.org/licenses/>.

from enum import Enum
from enum import IntEnum
from enum import unique


@unique
class Realm(Enum):
    CONNECTING = 'Connecting'

    def __str__(self):
        return self.value


@unique
class Event(Enum):
    AUTH_SUCCESSFUL = 'Auth successful'
    AUTH_FAILED = 'Auth failed'
    BIND_FAILED = 'Bind failed'
    SESSION_FAILED = 'Session failed'
    RESUME_SUCCESSFUL = 'Resume successful'
    RESUME_FAILED = 'Resume failed'
    CONNECTION_ACTIVE = 'Connection active'

    def __str__(self):
        return self.value


class GSSAPIState(IntEnum):
    STEP = 0
    WRAP = 1


class MessageType(Enum):
    NORMAL = 'normal'
    CHAT = 'chat'
    GROUPCHAT = 'groupchat'
    HEADLINE = 'headline'
    ERROR = 'error'


class PresenceType(Enum):
    PROBE = 'probe'
    SUBSCRIBE = 'subscribe'
    SUBSCRIBED = 'subscribed'
    AVAILABLE = None
    UNAVAILABLE = 'unavailable'
    UNSUBSCRIBE = 'unsubscribe'
    UNSUBSCRIBED = 'unsubscribed'
    ERROR = 'error'

    @property
    def is_available(self):
        return self == PresenceType.AVAILABLE

    @property
    def is_unavailable(self):
        return self == PresenceType.UNAVAILABLE


class PresenceShow(Enum):
    ONLINE = 'online'
    CHAT = 'chat'
    AWAY = 'away'
    XA = 'xa'
    DND = 'dnd'


class StatusCode(Enum):
    NON_ANONYMOUS = '100'
    AFFILIATION_CHANGE = '101'
    SHOWING_UNAVAILABLE = '102'
    NOT_SHOWING_UNAVAILABLE = '103'
    CONFIG_NON_PRIVACY_RELATED = '104'
    SELF = '110'
    CONFIG_ROOM_LOGGING = '170'
    CONFIG_NO_ROOM_LOGGING = '171'
    CONFIG_NON_ANONYMOUS = '172'
    CONFIG_SEMI_ANONYMOUS = '173'
    CONFIG_FULL_ANONYMOUS = '174'
    CREATED = '201'
    NICKNAME_MODIFIED = '210'
    REMOVED_BANNED = '301'
    NICKNAME_CHANGE = '303'
    REMOVED_KICKED = '307'
    REMOVED_AFFILIATION_CHANGE = '321'
    REMOVED_NONMEMBER_IN_MEMBERS_ONLY = '322'
    REMOVED_SERVICE_SHUTDOWN = '332'
    REMOVED_ERROR = '333'


class InviteType(Enum):
    MEDIATED = 'mediated'
    DIRECT = 'direct'


class AvatarState(Enum):
    IGNORE = 'ignore'
    NOT_READY = 'not ready'
    EMPTY = 'empty'
    ADVERTISED = 'advertised'


class Affiliation(Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'
    OUTCAST = 'outcast'
    NONE = 'none'

    @property
    def is_owner(self):
        return self == Affiliation.OWNER

    @property
    def is_admin(self):
        return self == Affiliation.ADMIN

    @property
    def is_member(self):
        return self == Affiliation.MEMBER

    @property
    def is_outcast(self):
        return self == Affiliation.OUTCAST

    @property
    def is_none(self):
        return self == Affiliation.NONE


class Role(Enum):
    MODERATOR = 'moderator'
    PARTICIPANT = 'participant'
    VISITOR = 'visitor'
    NONE = 'none'

    @property
    def is_moderator(self):
        return self == Role.MODERATOR

    @property
    def is_participant(self):
        return self == Role.PARTICIPANT

    @property
    def is_visitor(self):
        return self == Role.VISITOR

    @property
    def is_none(self):
        return self == Role.NONE


class Error(Enum):
    BAD_REQUEST = 'bad-request'
    CONFLICT = 'conflict'
    FEATURE_NOT_IMPLEMENTED = 'feature-not-implemented'
    FORBIDDEN = 'forbidden'
    GONE = 'gone'
    INTERNAL_SERVER_ERROR = 'internal-server-error'
    ITEM_NOT_FOUND = 'item-not-found'
    JID_MALFORMED = 'jid-malformed'
    NOT_ACCEPTABLE = 'not-acceptable'
    NOT_ALLOWED = 'not-allowed'
    NOT_AUTHORIZED = 'not-authorized'
    PAYMENT_REQUIRED = 'payment-required'
    RECIPIENT_UNAVAILABLE = 'recipient-unavailable'
    REDIRECT = 'redirect'
    REGISTRATION_REQUIRED = 'registration-required'
    REMOTE_SERVER_NOT_FOUND = 'remote-server-not-found'
    REMOTE_SERVER_TIMEOUT = 'remote-server-timeout'
    RESOURCE_CONSTRAINT = 'resource-constraint'
    SERVICE_UNAVAILABLE = 'service-unavailable'
    SUBSCRIPTION_REQUIRED = 'subscription-required'
    UNDEFINED_CONDITION = 'undefined-condition'
    UNEXPECTED_REQUEST = 'unexpected-request'
