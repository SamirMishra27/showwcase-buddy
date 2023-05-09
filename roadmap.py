from disnake import CommandInteraction, MessageInteraction, ButtonStyle, Embed, Message
from disnake.ui import button, Button
from disnake.ext import commands

from custom_view import CustomView
from utils import SHOWWCASE_LOGO

from datetime import datetime
from string import capwords

class RoadmapsView(CustomView):

    def __init__(self, author, bot, data, *, timeout = 180):
        super().__init__(clear_on_timeout = False, timeout = timeout)

        self.author = author
        self.bot = bot

        self.data: list[dict] = data
        self.curr_page = 0

        self.message: Message = None
        self.embed: Embed = None

    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        if interaction.user.id == self.author.id:
            return True
        else:
            await interaction.response.send_message('This is not for you!', ephemeral = True)

    @button(label = 'LAST', custom_id = 'PAGE_LEFT', style = ButtonStyle.blurple, disabled = True)
    async def page_left_button(self, button: Button, interaction: MessageInteraction):

        self.curr_page -= 1
        self.check_disability()

        await self.update_embed_page()
        await interaction.response.edit_message(embed = self.embed, view = self)

    @button(custom_id = 'PAGE_NO', style = ButtonStyle.gray, disabled = True)
    async def page_no_button(self, button, interaction):
        pass

    @button(label = 'NEXT', custom_id = 'PAGE_RIGHT', style = ButtonStyle.blurple)
    async def page_right_button(self, button: Button, interaction: MessageInteraction):

        self.curr_page += 1
        self.check_disability()

        await self.update_embed_page()
        await interaction.response.edit_message(embed = self.embed, view = self)

    async def update_embed_page(self):

        time_parse_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        page_content = self.data[self.curr_page]
        site_url = f"https://www.showwcase.com/roadmap/{ page_content['id'] }/{ page_content['slug'] }"

        embed = Embed(
            title = page_content['title'],
            colour = int(page_content['color'][1:], base = 16),
            description = page_content['description'],
        )
        embed.set_author(
            name = 'Showwcase Roadmaps - Learn',
            url = 'https://www.showwcase.com/explore',
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_footer(text = 'Learn from Showwcase! 📘 | Roadmap last updated on:')
        embed.timestamp = datetime.strptime(page_content['updatedAt'], time_parse_format)
        embed.set_thumbnail(url = SHOWWCASE_LOGO)

        embed.add_field(
            name = page_content['info']['title'],
            value = page_content['info']['description'],
            inline = False
        )

        embed.add_field(
            name = 'Language 🗣️',
            value = page_content['info']['language'],
            inline = False
        )

        embed.add_field(
            name = 'Difficulty ✒️',
            value = page_content['info']['difficulty'],
            inline = False
        )

        embed.add_field(
            name = capwords(page_content['info']['jobs']['label']) + '💼',
            value = '**' + page_content['info']['jobs']['total'] + '**',
            inline = True
        )

        embed.add_field(
            name = 'Salary Range 💰',
            value = page_content['info']['salary']['range'],
            inline = True
        )
        
        embed.add_field(
            name = 'Skills You Will Learn 📖',
            value = '\n• ' + '\n• '.join(skill for skill in page_content['info']['skills']),
            inline = False
        )
        self.embed = embed
        self.get_child_by(id = 'PAGE_NO').label = f'{self.curr_page + 1} / {len(self.data)}'

        if self.get_child_by(label = 'GO TO ROADMAP'):
            self.get_child_by(label = 'GO TO ROADMAP').url = site_url

        else:
            self.add_item(Button(label = 'GO TO ROADMAP', url = site_url))

    def check_disability(self):
        self.enable_all_children()

        self.get_child_by(id = 'PAGE_NO').disabled = True

        if self.curr_page == 0:
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        if self.curr_page == len(self.data) - 1:
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)

class Roadmap(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_load(self):
        self.bot._Roadmap = self

    @commands.slash_command(name = 'roadmaps')
    async def show_roadmaps(self, ctx: CommandInteraction):
        
        api_response = await self.bot.session.get('https://cache.showwcase.com/roadmaps')
        data = await api_response.json()

        view = RoadmapsView(ctx.author, self.bot, data)
        view.check_disability()
        await view.update_embed_page()

        resp_message = await ctx.send(embed = view.embed, view = view, ephemeral = False)
        await view.resolve_message(ctx, resp_message)

def setup(bot: commands.bot):
    bot.add_cog(Roadmap(bot))