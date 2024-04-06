# Discord Analytics

## Installing the package

```bash
pip install discordanalytics
```

## Usage

> **Note:** To use Discord Analytics, you need to have an API token. Check the docs for more informations : https://docs.discordanalytics.xyz/get-started/bot-registration

```python
import discord
from discordanalytics import DiscordAnalytics

class MyClient(discord.Client):
  async def on_ready(self):
    print(f'Logged on as {self.user}!')

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)

analytics = DiscordAnalytics(client, "YOUR_API_TOKEN")
analytics.track_events()

client.run('TOKEN')
```