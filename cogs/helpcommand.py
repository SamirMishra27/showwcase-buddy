from disnake import CommandInteraction, Embed, Colour
from disnake.ext import commands
from urllib.parse import quote

class CustomHelpCommand(commands.DefaultHelpCommand):

    def prepare_help_context(self):

        bot: commands.Bot = self.context.bot
        list_of_app_commands: list[str] = []

        for slash_command in bot.global_slash_commands:
            sub_commands = list(option for option in slash_command.options if option.type.value == 1)

            if not sub_commands:
                list_of_app_commands.append(f'</{slash_command.name}:{slash_command.id}>')

            else:
                for sub_command in sub_commands:
                    list_of_app_commands.append(f'</{slash_command.name} {sub_command.name}:{slash_command.id}>')

        list_of_app_commands_string = '- ' + '\n- '.join(command for command in list_of_app_commands)
        help_description = (
            f'A discord bot to make browsing [Showwcase](https://www.showwcase.com/) nice, easier and convenient for Developers! <:coding:1111660183987437628>\n'
            f'### My Commands\n'
            f'{list_of_app_commands_string}'
        )

        twitter_tweet = 'http://twitter.com/intent/tweet?text=' + quote(f'Hey! @SamirMishra27 I need help with your bot.')
        resources = (
            f'[Support]({twitter_tweet}) '
            f'| [Github](https://github.com/SamirMishra27) '
            f'| [Support My Work!](https://paypal.me/SamirMishra27) '
            f'| [Showwcase](https://www.showwcase.com/explore) '
        )

        embed = Embed(colour = Colour.dark_teal(), description = help_description)
        embed.set_author(
            name = 'Showwcase Buddy Help!',
            icon_url = bot.user.display_avatar.url
        )
        embed.set_thumbnail(url = bot.user.display_avatar.url)

        embed.add_field(name = 'Useful', value = resources)
        embed.set_footer(text = 'Thank you for using this bot! 💖')
        return embed

    async def send_bot_help(self, mapping):

        embed, view = self.prepare_help_context(mapping)
        view.embed = embed
        view.message = await self.context.send(embed = embed, view = view)

class Help(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self._original_help_command = bot.help_command
        self.bot = bot
        bot.help_command = CustomHelpCommand()

    def cog_unload(self) -> None:
        self.bot.help_command = self._original_help_command

    @commands.slash_command(name = 'help')
    async def help(self, ctx: CommandInteraction):
        """
        Shows help and commands of this Bot!
        """

        help_command = self.bot.help_command
        help_command.context = ctx

        embed = help_command.prepare_help_context()
        await ctx.send(embed = embed)

def setup(bot: commands.Bot):
    bot.add_cog(Help(bot))