import asyncio
import sys
from collections import Counter
from datetime import datetime
from typing import List, Literal, cast, Any, Dict, Optional, TYPE_CHECKING

import aiohttp
import discord
from discord.client import Client
from discord.enums import InteractionType
from discord.guild import Guild
from discord.interactions import Interaction
from discord.member import Member
from dataclasses import asdict

if TYPE_CHECKING:
    from discord.types.interactions import (
        ApplicationCommandInteractionData,
        MessageComponentInteractionData,
    )

from .__init__ import __version__
from .types import GuildStat, InteractionStat, LocaleStat, Stats, GuildMembers


class ApiEndpoints:
    BASE_URL = "https://discordanalytics.xyz/api"
    BOT_URL = "/bots/:id"
    STATS_URL = "/bots/:id/stats"
    EVENT_URL = "/bots/:id/events/:event_key"


class ErrorCodes:
    INVALID_CLIENT_TYPE = "Invalid client type, please use a valid client."
    CLIENT_NOT_READY = "Client is not ready, please start the client first."
    INVALID_RESPONSE = "Invalid response from the API, please try again later."
    INVALID_API_TOKEN = (
        "Invalid API token, please get one at "
        + ApiEndpoints.BASE_URL.split("/api")[0]
        + " and try again."
    )
    DATA_NOT_SENT = "Data cannot be sent to the API, I will try again in a minute."
    SUSPENDED_BOT = (
        "Your bot has been suspended, please check your mailbox for more information."
    )
    INVALID_EVENTS_COUNT = "invalid events count"
    INVALID_VALUE_TYPE = "invalid value type"
    INVALID_EVENT_KEY = "invalid event key"


class DiscordAnalytics:
    def __init__(
        self,
        client: Client,
        api_key: str,
        api_url: str = ApiEndpoints.BASE_URL,
        debug: bool = False,
        chunk_guilds_at_startup: bool = True,
    ):
        self.client = client
        self.api_key = api_key
        self.api_url = api_url
        self.debug = debug
        self.chunk_guilds = chunk_guilds_at_startup
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bot {api_key}",
        }
        self.stats = Stats(
            date=datetime.today().strftime("%Y-%m-%d"),
        )

    def track_events(self):
        if not self.client.is_ready():

            @self.client.event
            async def on_ready():
                await self.init()
        else:
            asyncio.create_task(self.init())

        @self.client.event
        async def on_interaction(interaction: Interaction):
            self.track_interactions(interaction)

        @self.client.event
        async def on_guild_join(_: Guild):
            self.trackGuilds("create")

        @self.client.event
        async def on_guild_remove(_: Guild):
            self.trackGuilds("delete")

    async def api_call_with_retries(
        self, method, endpoint, headers, json, max_retries=5, backoff_factor=0.5
    ) -> Optional[Dict[str, Any]]:
        retries = 0
        while retries < max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method, self.api_url + endpoint, headers=headers, json=json
                    ) as response:
                        if response.status == 200:
                            try:
                                return await response.json()
                            except Exception:
                                return None
                        elif response.status == 401:
                            raise ValueError(ErrorCodes.INVALID_API_TOKEN)
                        elif response.status == 423:
                            raise ValueError(ErrorCodes.SUSPENDED_BOT)
                        elif response.status == 404 and "events" in endpoint:
                            raise ValueError(ErrorCodes.INVALID_EVENT_KEY)
                        else:
                            raise ValueError(ErrorCodes.INVALID_RESPONSE)
            except (aiohttp.ClientError, ValueError) as e:
                retries += 1
                if self.debug:
                    print(
                        f"[DISCORDANALYTICS] Error: {e}. Retrying in {backoff_factor * (2**retries)} seconds..."
                    )
                if retries >= max_retries:
                    raise e
                await asyncio.sleep(backoff_factor * (2**retries))

    async def init(self):
        if not isinstance(self.client, Client):
            raise ValueError(ErrorCodes.INVALID_CLIENT_TYPE)
        if not self.client.is_ready() or not self.client.user:
            raise ValueError(ErrorCodes.CLIENT_NOT_READY)

        endpoint = ApiEndpoints.BOT_URL.replace(":id", str(self.client.user.id))
        headers = self.headers
        json = {
            "avatar": self.client.user._avatar,
            "framework": "discord.py",
            "username": self.client.user.name,
            "version": __version__,
        }

        await self.api_call_with_retries("PATCH", endpoint, headers, json)

        if self.debug:
            print("[DISCORDANALYTICS] Instance successfully initialized")

        if self.debug:
            if "--fast" in sys.argv:
                print(
                    "[DISCORDANALYTICS] Fast mode is enabled. Stats will be sent every 30s."
                )
            else:
                print(
                    "[DISCORDANALYTICS] Fast mode is disabled. Stats will be sent every 5 minutes."
                )

        if not self.chunk_guilds:
            await self.load_members_for_all_guilds()

        self.client.loop.create_task(self.send_stats())

    async def load_members_for_all_guilds(self):
        """Load members for each guild when chunk_guilds_at_startup is False."""
        tasks = [self.load_members_for_guild(guild) for guild in self.client.guilds]
        await asyncio.gather(*tasks)

    async def load_members_for_guild(self, guild: Guild):
        """Load members for a single guild."""
        try:
            await guild.chunk()
            if self.debug:
                print(f"[DISCORDANALYTICS] Chunked members for guild {guild.name}")
        except Exception:
            await self.query_members(guild)

    async def query_members(self, guild: Guild):
        """Query members by prefix if chunking fails."""
        try:
            members = await guild.query_members(query="", limit=1000)
            if self.debug:
                print(
                    f"[DISCORDANALYTICS] Queried members for guild {guild.name}: {len(members)} members found."
                )
        except Exception as e:
            print(
                f"[DISCORDANALYTICS] Error querying members for guild {guild.name}: {e}"
            )

    async def send_stats(self):
        await self.client.wait_until_ready()
        if not self.client.application or not self.client.user:
            return
        while not self.client.is_closed():
            if self.debug:
                print("[DISCORDANALYTICS] Sending stats...")

            guild_count = len(self.client.guilds)
            user_count = len(self.client.users)
            user_install_count = (
                self.client.application.approximate_user_install_count or 0
            )

            endpoint = ApiEndpoints.STATS_URL.replace(":id", str(self.client.user.id))
            headers = self.headers
            json = asdict(self.stats)

            await self.api_call_with_retries("POST", endpoint, headers, json)

            if self.debug:
                print(f"[DISCORDANALYTICS] Stats {self.stats} sent to the API")
            self.stats = Stats(
                date=datetime.today().strftime("%Y-%m-%d"),
                customEvents=self.stats.customEvents,
                guildCount=guild_count,
                userCount=user_count,
                userInstallCount=user_install_count,
                guildMembers=self.calculate_guild_members_repartition()
            )

            await asyncio.sleep(30 if "--fast" in sys.argv else 300)

    def calculate_guild_members_repartition(self) -> GuildMembers:
        repartition = GuildMembers()

        for guild in self.client.guilds:
            count = guild.member_count or 0
            if count <= 100:
                repartition.little += 1
            elif count <= 500:
                repartition.medium += 1
            elif count <= 1500:
                repartition.big += 1
            else:
                repartition.huge += 1

        return repartition

    def track_interactions(self, interaction: Interaction):
        if self.debug:
            print("[DISCORDANALYTICS] Track interactions triggered")

        if not self.client.is_ready():
            raise ValueError(ErrorCodes.CLIENT_NOT_READY)

        if interaction.type == InteractionType.autocomplete:
            return

        locale = next(
            (
                x
                for x in self.stats.interactionsLocales
                if x.locale == interaction.locale.value
            ),
            None,
        )
        if locale is not None:
            locale.number += 1
        else:
            self.stats.interactionsLocales.append(
                LocaleStat(locale=interaction.locale.value, number=1)
            )

        if (
            interaction.type
            in {
                InteractionType.application_command,
                InteractionType.autocomplete,
            }
            and interaction.data
        ):
            cmd_data = cast("ApplicationCommandInteractionData", interaction.data)
            cmd_type = cmd_data.get("type", 1)
            interaction_data = next(
                (
                    x
                    for x in self.stats.interactions
                    if x.name == cmd_data["name"]
                    and x.type == interaction.type.value
                    and x.commandType == cmd_type
                ),
                None,
            )
            if interaction_data:
                interaction_data.number += 1
            else:
                self.stats.interactions.append(
                    InteractionStat(
                        name=cmd_data["name"],
                        number=1,
                        type=interaction.type.value,
                        commandType=cmd_type,
                    )
                )
        elif (
            interaction.type
            in {
                InteractionType.component,
                InteractionType.modal_submit,
            }
            and interaction.data
        ):
            component_data = cast("MessageComponentInteractionData", interaction.data)
            interaction_data = next(
                (
                    x
                    for x in self.stats.interactions
                    if x.name == component_data["custom_id"]
                    and x.type == interaction.type.value
                ),
                None,
            )
            if interaction_data:
                interaction_data.number += 1
            else:
                self.stats.interactions.append(
                    InteractionStat(
                        name=component_data["custom_id"],
                        number=1,
                        type=interaction.type.value,
                    )
                )

        guild_id = str(interaction.guild.id) if interaction.guild else "dm"
        guild_icon = interaction.guild.icon.key if interaction.guild and interaction.guild.icon else None

        guild_data = next(
            (x for x in self.stats.guilds if x.guildId == guild_id),
            None,
        )

        if guild_data:
            guild_data.interactions += 1
            guild_data.icon = guild_icon
        else:
            self.stats.guilds.append(
                GuildStat(
                    guildId=guild_id,
                    icon=guild_icon,
                    interactions=1,
                    members=interaction.guild.member_count if interaction.guild else 0,
                    name=interaction.guild.name if interaction.guild else "DM",
                )
            )

        if interaction.guild is None:
            self.stats.usersType.privateMessage += 1
        else:
            guildLocales: List[LocaleStat] = []
            for guild in self.client.guilds:
                if guild.preferred_locale:
                    guild_locale = next(
                        (
                            x
                            for x in guildLocales
                            if x.locale == guild.preferred_locale.value
                        ),
                        None,
                    )
                    if guild_locale:
                        guild_locale.number += 1
                    else:
                        guildLocales.append(
                            LocaleStat(
                                locale=guild.preferred_locale.value,
                                number=1,
                            )
                        )
            self.stats.guildLocales = guildLocales

            guild_member = cast(Member, interaction.user)
            if (
                guild_member.guild_permissions.administrator
                or guild_member.guild_permissions.manage_guild
            ):
                self.stats.usersType.admin += 1
            elif any(
                perm
                for perm in [
                    guild_member.guild_permissions.manage_messages,
                    guild_member.guild_permissions.kick_members,
                    guild_member.guild_permissions.ban_members,
                    guild_member.guild_permissions.mute_members,
                    guild_member.guild_permissions.deafen_members,
                    guild_member.guild_permissions.move_members,
                    guild_member.guild_permissions.moderate_members,
                ]
            ):
                self.stats.usersType.moderator += 1
            elif (
                guild_member.joined_at
                and (discord.utils.utcnow() - guild_member.joined_at).days <= 7
            ):
                self.stats.usersType.newMember += 1
            else:
                self.stats.usersType.other += 1

    def trackGuilds(self, type: Literal["create", "delete"]):
        if self.debug:
            print(f"[DISCORDANALYTICS] trackGuilds({type}) triggered")

        if type == "create":
            self.stats.addedGuilds += 1
        elif type == "delete":
            self.stats.removedGuilds += 1

    def events(self, event_key: str):
        if self.debug:
            print(f"[DISCORDANALYTICS] Event {event_key} triggered")
        if not self.client.is_ready():
            raise ValueError(ErrorCodes.CLIENT_NOT_READY)
        if event_key not in self.stats.customEvents:
            self.stats.customEvents[event_key] = 0
        return Event(self, event_key)


class Event:
    def __init__(self, analytics: DiscordAnalytics, event_key: str):
        self.analytics = analytics
        self.event_key = event_key
        self.last_action = ""

        asyncio.create_task(self.ensure())

    async def ensure(self):
        if (
            self.analytics.client.user is None
            or not isinstance(self.event_key, str)
            or len(self.event_key) < 1
            or len(self.event_key) > 50
        ):
            raise ValueError(ErrorCodes.INVALID_EVENTS_COUNT)

        if self.event_key not in self.analytics.stats.customEvents:
            if self.analytics.debug:
                print(f"[DISCORDANALYTICS] Fetching value for event {self.event_key}")

        endpoint = ApiEndpoints.EVENT_URL.replace(
            ":id", str(self.analytics.client.user.id)
        ).replace(":event_key", self.event_key)

        data = await self.analytics.api_call_with_retries(
            "GET", endpoint, self.analytics.headers, {}
        )

        if data is not None and self.last_action != "set":
            self.analytics.stats.customEvents[self.event_key] = (
                    self.analytics.stats.customEvents.get(self.event_key, 0)
                    + data.get("currentValue", 0)
            )

        if self.analytics.debug:
            print(f"[DISCORDANALYTICS] Value fetched for event {self.event_key}")

    def increment(self, count: int = 1):
        if self.analytics.debug:
            print(f"[DISCORDANALYTICS] Incrementing event {self.event_key} by {count}")
        if not isinstance(count, int) or count < 0:
            raise ValueError(ErrorCodes.INVALID_VALUE_TYPE)
        self.analytics.stats.customEvents[self.event_key] = (
            self.analytics.stats.customEvents.get(self.event_key, 0) + count
        )
        self.last_action = "increment"

    def decrement(self, count: int = 1):
        if self.analytics.debug:
            print(f"[DISCORDANALYTICS] Decrementing event {self.event_key} by {count}")
        if not isinstance(count, int) or count < 0 or self.get() - count < 0:
            raise ValueError(ErrorCodes.INVALID_VALUE_TYPE)
        self.analytics.stats.customEvents[self.event_key] = (
            self.analytics.stats.customEvents.get(self.event_key, 0) - count
        )
        self.last_action = "decrement"

    def set(self, value: int):
        if self.analytics.debug:
            print(f"[DISCORDANALYTICS] Setting event {self.event_key} to {value}")
        if not isinstance(value, int) or value < 0:
            raise ValueError(ErrorCodes.INVALID_VALUE_TYPE)
        self.analytics.stats.customEvents[self.event_key] = value
        self.last_action = "set"

    def get(self):
        if self.analytics.debug:
            print(f"[DISCORDANALYTICS] Getting event {self.event_key}")
        if (
            not isinstance(self.event_key, str)
            or len(self.event_key) < 1
            or len(self.event_key) > 50
        ):
            raise ValueError(ErrorCodes.INVALID_EVENTS_COUNT)
        return self.analytics.stats.customEvents[self.event_key]
