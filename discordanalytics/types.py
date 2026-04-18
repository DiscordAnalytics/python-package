from dataclasses import dataclass, field
from typing import Dict, List, Optional

CustomEvents = Dict[str, int]


@dataclass
class GuildStat:
    guildId: str
    icon: Optional[str]
    interactions: int
    members: int
    name: str


@dataclass
class GuildMembers:
    little: int = 0
    medium: int = 0
    big: int = 0
    huge: int = 0


@dataclass
class LocaleStat:
    locale: str
    number: int


@dataclass
class InteractionStat:
    name: str
    number: int
    type: int
    commandType: Optional[int] = None


@dataclass
class UsersType:
    admin: int = 0
    moderator: int = 0
    newMember: int = 0
    other: int = 0
    privateMessage: int = 0


@dataclass
class Stats:
    date: str
    addedGuilds: int = 0
    customEvents: CustomEvents = field(default_factory=dict)
    guilds: List[GuildStat] = field(default_factory=list)
    guildCount: int = 0
    guildLocales: List[LocaleStat] = field(default_factory=list)
    guildMembers: GuildMembers = field(default_factory=GuildMembers)
    interactions: List[InteractionStat] = field(default_factory=list)
    interactionsLocales: List[LocaleStat] = field(default_factory=list)
    removedGuilds: int = 0
    userCount: int = 0
    userInstallCount: int = 0
    usersType: UsersType = field(default_factory=UsersType)
