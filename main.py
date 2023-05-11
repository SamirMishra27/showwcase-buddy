import disnake
from disnake.ext import commands

from aiohttp import ClientSession
from asyncio import sleep
from datetime import datetime
from os import environ

from traceback import print_exception
from json import load
import logging

from disnake.interactions import ApplicationCommandInteraction
logging.basicConfig(level=logging.INFO)

# Setting up variable for jishaku's cog purposes
environ['JISHAKU_NO_UNDERSCORE'] = 'True'
environ['JISHAKU_NO_DM_TRACEBACK'] = 'True'

with open('config.json') as f:
    config = load(f)
    stage = config["STAGE"]

    BOT_TOKEN = config["BOT_TOKEN_" + stage]
    BOT_PREFIX = config["PREFIX_" + stage]

ClientIntents = disnake.Intents(
    guilds = True, members = True, bans = False,
    emojis = True, integrations = False, webhooks = False,
    invites = False, voice_states = False, presences = False,
    messages = True, reactions = True, typing = False,
    emojis_and_stickers = False,
    guild_scheduled_events = False,
    message_content = True
)

class ShowwcaseBuddyClient(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix = BOT_PREFIX,
            case_insensitive = True,
            intents = ClientIntents,
            max_messages = 10,
            owner_id = 278094147901194242,
            strip_after_prefix = True,
            
            allowed_mentions = disnake.AllowedMentions(everyone=False, users=True, roles=True, replied_user=False),
            chunk_guilds_at_startup = True,
            reload = True,
        )

        self.version = '1.0'
        self.debug_channel = 995124307917279252
        self.bot_extensions = ['jishaku', 'hackathon', 'roadmap']

        self.launched_at = None
        self.session = ClientSession()

        self.bot_is_ready = False
        self._disconnected = False

        ext_count = 0
        for extension in self.bot_extensions: 
            try: 
                self.load_extension(extension) 
                print('Loaded', extension)
                ext_count += 1  

            except commands.ExtensionError as e: 
                print(f'Extension {extension} could not be loaded:\n', e)
                print_exception(e, e, e.__traceback__)
                continue
        print(f"Loaded {ext_count} of {len(self.bot_extensions)} Cogs.")

    async def on_ready(self):
        print(
            f'\n\nWe have successfully logged in as {self.user} \n'
            f'USING Disnake, a fork of discord.py \n'
            f'Disnake.py version info: {disnake.version_info} \n'
            f'Disnake.py version: {disnake.__version__} \n'
        )
            
        self.bot_is_ready = True

    async def on_message(self, message: disnake.Message):
        if not self.bot_is_ready and message.author.id != self.owner_id:
            return
        
        if hasattr(message.channel, 'guild') and message.channel.guild.id == 794934796761432094:
            return
        
        if message.content.replace('!', '') == self.user.mention:
            await message.channel.send(f'My default prefix is `{self.prefix}`')

        return await super().on_message(message)

    async def on_application_command(self, interaction: ApplicationCommandInteraction):

        if hasattr(interaction.channel, 'guild') and interaction.channel.guild.id == 794934796761432094:
            return
        
        return await super().on_application_command(interaction)

    @property
    def send_invite_link(self):
        return disnake.utils.oauth_url(
            client_id=super().user.id, 
            permissions=disnake.Permissions(1144388672), 
            scopes=("bot", "applications.commands")
        )
    
    @property
    def prefix(self):
        return BOT_PREFIX
    
    def run(self, *args, **kwargs):
        self.launched_at = datetime.now()
        super().run(*args, **kwargs)

    async def on_disconnect(self):
        self._disconnected = True
        return print(f'The bot has successfully logged out. @ {datetime.now()}')
    
    async def on_resumed(self):
        self._disconnected = False

    # async def get_context(self, message):
    #     return await super().get_context(message, cls=CustomContext)

    async def close(self):
        await self.session.close()
        return await super().close()
    
if __name__ == "__main__":
    ShowwcaseBuddyClient().run(BOT_TOKEN, reconnect=True)