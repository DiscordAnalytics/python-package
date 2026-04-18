import os
import re
import discord
from discord import app_commands
from dotenv import load_dotenv
from discordanalytics import DiscordAnalytics

load_dotenv()

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.reactions = True
        intents.messages = True

        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

analytics = DiscordAnalytics(
    client=client,
    api_key=os.getenv("DISCORD_ANALYTICS_API_KEY"),
    debug=True,
    api_url="http://localhost:3001"
)

class TestButtonView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        btn = discord.ui.Button(
            label="Test button",
            style=discord.ButtonStyle.primary,
            custom_id=f"button_{user_id}"
        )
        btn.callback = self.button_callback
        self.add_item(btn)

    async def button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"You clicked the button with ID: {interaction.data['custom_id']}",
            ephemeral=True
        )

class TestSelectView(discord.ui.View):
    @discord.ui.select(
        custom_id="test_select",
        options=[discord.SelectOption(label="Test select", value="test_select")]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.edit_message(
            content=f"You selected: {select.values[0]}",
            view=None
        )

class TestModal(discord.ui.Modal, title="My modal"):
    favorite_color = discord.ui.TextInput(
        label="What's your favorite color?",
        style=discord.TextStyle.short,
        custom_id="favorite_color_input"
    )

    def __init__(self):
        super().__init__(custom_id="my_modal")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Your favorite color is: {self.favorite_color.value}",
            ephemeral=True
        )


@client.event
async def on_ready():
    print(f'Client is ready as {client.user}!')
    await analytics.init()

@client.event
async def on_interaction(interaction: discord.Interaction):
    analytics.track_interactions(interaction)


@client.tree.command(name="test", description="Send a test message")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def test_command(interaction: discord.Interaction, test_option: str = None):
    if test_option == 'button':
        await interaction.response.send_message('Test button', view=TestButtonView(interaction.user.id))
    elif test_option == 'select':
        await interaction.response.send_message('Test select', view=TestSelectView())
    elif test_option == 'modal':
        await interaction.response.send_modal(TestModal())
    else:
        await interaction.response.send_message('This is a test message', ephemeral=True)

@test_command.autocomplete('test_option')
async def test_autocomplete(interaction: discord.Interaction, current: str):
    choices = ['button', 'select', 'modal']
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in choices if choice.startswith(current)
    ]

@client.event
async def on_guild_join(guild):
    analytics.track_guilds('create')

@client.event
async def on_guild_remove(guild):
    analytics.track_guilds('delete')

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.emoji.name == '❤️':
        analytics.events('heart_reaction').increment()

@client.event
async def on_error(event, *args, **kwargs):
    import traceback
    print(f'Client error in {event}:')
    traceback.print_exc()

client.run(os.getenv('DISCORD_TOKEN'))