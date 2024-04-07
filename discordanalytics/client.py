import asyncio
from datetime import datetime
import discord
from discord.enums import InteractionType
import requests
import sys

from .__init__ import __version__

class ApiEndpoints:
  BASE_URL = "https://discordanalytics.xyz/api"
  BOT_URL = f"{BASE_URL}/bots/:id"
  STATS_URL = f"{BASE_URL}/bots/:id/stats"

class ErrorCodes:
  INVALID_CLIENT_TYPE = "Invalid client type, please use a valid client."
  CLIENT_NOT_READY = "Client is not ready, please start the client first."
  INVALID_RESPONSE = "Invalid response from the API, please try again later."
  INVALID_API_TOKEN = "Invalid API token, please get one at " + ApiEndpoints.BASE_URL.split("/api")[0] + " and try again."
  DATA_NOT_SENT = "Data cannot be sent to the API, I will try again in a minute."
  SUSPENDED_BOT = "Your bot has been suspended, please check your mailbox for more information."
  INSTANCE_NOT_INITIALIZED = "It seem that you didn't initialize your instance. Please check the docs for more informations."
  INVALID_EVENTS_COUNT = "invalid events count"

class DiscordAnalytics():
  def __init__(self, client: discord.Client, api_key: str, debug: bool = False):
    self.client = client
    self.api_key = api_key
    self.debug = debug
    self.is_ready = False
    self.headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bot {api_key}"
    }
    self.stats = {
      "date": datetime.today().strftime("%Y-%m-%d"),
      "guilds": 0,
      "users": 0,
      "interactions": [], # {name:str, number:int, type:int}[]
      "locales": [], # {locale:str, number:int}[]
      "guildsLocales": [], # {locale:str, number:int}[]
      "guildMembers": {
        "little": 0,
        "medium": 0,
        "big": 0,
        "huge": 0
      }
    }
  
  def track_events(self):
    if not self.client.is_ready():
      @self.client.event
      async def on_ready():
        self.init()
    else:
      self.init()
    @self.client.event
    async def on_interaction(interaction):
      self.track_interactions(interaction)
  
  def init(self):
    if not isinstance(self.client, discord.Client):
      raise ValueError(ErrorCodes.INVALID_CLIENT_TYPE)
    if not self.client.is_ready():
      raise ValueError(ErrorCodes.CLIENT_NOT_READY)
    
    response = requests.patch(
      ApiEndpoints.BOT_URL.replace(":id", str(self.client.user.id)),
      headers=self.headers,
      json={
        "username": self.client.user.name,
        "avatar": self.client.user._avatar,
        "framework": "discord.py",
        "version": __version__
      }
    )

    if response.status_code == 401:
      raise ValueError(ErrorCodes.INVALID_API_TOKEN)
    if response.status_code == 423:
      raise ValueError(ErrorCodes.SUSPENDED_BOT)
    if response.status_code != 200:
      raise ValueError(ErrorCodes.INVALID_RESPONSE)
    
    if self.debug:
      print("[DISCORDANALYTICS] Instance successfully initialized")
    self.is_ready = True

    if self.debug:
      if "--dev" in sys.argv:
        print("[DISCORDANALYTICS] DevMode is enabled. Stats will be sent every 30s.")
      else:
        print("[DISCORDANALYTICS] DevMode is disabled. Stats will be sent every 5 minutes.")

    self.client.loop.create_task(self.send_stats())

  async def send_stats(self):
    await self.client.wait_until_ready()
    while not self.client.is_closed():
      if self.debug:
        print("[DISCORDANALYTICS] Sending stats...")
      
      guild_count = len(self.client.guilds)
      user_count = len(self.client.users)

      response = requests.post(
        ApiEndpoints.STATS_URL.replace(":id", str(self.client.user.id)),
        headers=self.headers,
        json=self.stats
      )

      if response.status_code == 401:
        raise ValueError(ErrorCodes.INVALID_API_TOKEN)
      if response.status_code == 423:
        raise ValueError(ErrorCodes.SUSPENDED_BOT)
      if response.status_code != 200:
        raise ValueError(ErrorCodes.INVALID_RESPONSE)
      if response.status_code == 200:
        if self.debug:
          print(f"[DISCORDANALYTICS] Stats {self.stats} sent to the API")
        
        self.stats = {
          "date": datetime.today().strftime("%Y-%m-%d"),
          "guilds": guild_count,
          "users": user_count,
          "interactions": [],
          "locales": [],
          "guildsLocales": [],
          "guildMembers": self.calculate_guild_members_repartition()
        }
      
      await asyncio.sleep(10 if "--dev" in sys.argv else 300)

  def calculate_guild_members_repartition(self):
    result = {
      "little": 0,
      "medium": 0,
      "big": 0,
      "huge": 0
    }

    for guild in self.client.guilds:
      if guild.member_count <= 100:
        result["little"] += 1
      elif 100 < guild.member_count <= 500:
        result["medium"] += 1
      elif 500 < guild.member_count <= 1500:
        result["big"] += 1
      else:
        result["huge"] += 1

    return result
  
  def track_interactions(self, interaction):
    if self.debug:
      print("[DISCORDANALYTICS] Track interactions triggered")
    if not self.is_ready:
      raise ValueError(ErrorCodes.INSTANCE_NOT_INITIALIZED)
    
    guilds = []
    for guild in self.client.guilds:
      if guild.preferred_locale is not None:
        found = False
        for g in guilds:
          if g["locale"] == guild.preferred_locale.value:
            g["number"] += 1
            found = True
            break
        if not found:
          guilds.append({
            "locale": guild.preferred_locale.value,
            "number": 1
          })
    self.stats["guildsLocales"] = guilds
    
    found = False
    for data in self.stats["locales"]:
      if data["locale"] == interaction.locale.value:
        data["number"] += 1
        found = True
        break
    if not found:
      self.stats["locales"].append({
        "locale": interaction.locale.value,
        "number": 1
      })

    if interaction.type == InteractionType.application_command or interaction.type == InteractionType.autocomplete:
      found = False
      for data in self.stats["interactions"]:
        if data["name"] == interaction.data["name"] and data["type"] == interaction.type.value:
          data["number"] += 1
          found = True
          break
      if not found:
        self.stats["interactions"].append({
          "name": interaction.data["name"],
          "number": 1,
          "type": interaction.type.value
        })
    elif interaction.type == InteractionType.component or interaction.type == InteractionType.modal_submit:
      found = False
      for data in self.stats["interactions"]:
        if data["name"] == interaction.data["custom_id"] and data["type"] == interaction.type.value:
          data["number"] += 1
          found = True
          break
      if not found:
        self.stats["interactions"].append({
          "name": interaction.data["custom_id"],
          "number": 1,
          "type": interaction.type.value
        })