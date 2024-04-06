from datetime import datetime
import discord
import requests
import sys
import threading
import time

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
      "interactions": [],
      "locales": [],
      "guildsLocales": [],
      "guildMembers": {
        "little": 0,
        "medium": 0,
        "big": 0,
        "huge": 0
      }
    }

  def set_interval(self, func, interval, *args, **kwargs):
    def wrapper():
      while True:
        func(*args, **kwargs)
        time.sleep(interval)
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join()
    return thread
  
  def start(self):
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

    self.set_interval(self.send_stats, 30 if "--dev" in sys.argv else 300)

  def send_stats(self):
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