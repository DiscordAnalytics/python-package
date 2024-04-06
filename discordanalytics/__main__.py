import discord

class ApiEndpoints():
  BASE_URL = "https://discordanalytics.xyz/api"
  BOT_URL = f"{BASE_URL}/bots/:id"
  STATS_URL = f"{BASE_URL}/bots/:id/stats"

class ErrorCodes():
  INVALID_CLIENT_TYPE = 'Invalid client type, please use a valid client.'
  CLIENT_NOT_READY = 'Client is not ready, please start the client first.'
  INVALID_RESPONSE = 'Invalid response from the API, please try again later.'
  INVALID_API_TOKEN = 'Invalid API token, please get one at ' + ApiEndpoints.BASE_URL.split('/api')[0] + ' and try again.'
  DATA_NOT_SENT = "Data cannot be sent to the API, I will try again in a minute."
  SUSPENDED_BOT = "Your bot has been suspended, please check your mailbox for more information."
  INSTANCE_NOT_INITIALIZED = "It seem that you didn't initialize your instance. Please check the docs for more informations."
  INVALID_EVENTS_COUNT = "invalid events count"

class DiscordAnalytics():
  def __init__(self, client: discord.Client, api_key: str, debug: bool = False):
    self.client = client
    self.api_key = api_key