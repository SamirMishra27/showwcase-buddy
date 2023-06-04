from disnake import CommandInteraction, MessageInteraction, ButtonStyle, Button, Embed, Message, Colour
from disnake.ui import button
from disnake.ext import commands

from custom_view import CustomView
from utils import SHOWWCASE_LOGO

from datetime import datetime

class HackathonsView(CustomView):
    
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

        embed = Embed(colour = Colour.orange())
        embed.set_author(
            name = 'Showwcase Hackathons',
            url = 'https://www.showwcase.com/hackathon/hackfest',
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_footer(text = 'Don\'t forget to participate!')
        embed.set_thumbnail(url = SHOWWCASE_LOGO)

        embed.title = page_content['name']
        embed.description = page_content['description']
        embed.add_field(
            name = 'Total Participants',
            value = page_content['totalParticipants'],
            inline = False
        )

        if 'about' in page_content:
            embed.add_field(
                name = 'About',
                value = page_content['about'],
                inline = False
            )

        if 'reward' in page_content:
            embed.add_field(
                name = 'Prize',
                value = page_content['reward'],
                inline = False
            )

        start_date = datetime.strptime(page_content['startDate'], time_parse_format)
        end_date = datetime.strptime(page_content['endDate'], time_parse_format)

        embed.add_field(
            name = 'Starts On',
            value = '<t:{0}:F> (<t:{0}:R>)'.format(int(start_date.timestamp())),
            inline = False 
        )
        
        embed.add_field(
            name = 'Ends On',
            value = '<t:{0}:F> (<t:{0}:R>)'.format(int(end_date.timestamp())),
            inline = False 
        )
        self.embed = embed

        self.get_child_by(id = 'PAGE_NO').label = f'{self.curr_page + 1} / {len(self.data)}'

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

class Hackathon(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_load(self):
        self.bot._Hackathon = self

    @commands.slash_command(name = 'hackathons')
    async def show_hackathons(self, ctx: CommandInteraction):
        '''
        See the list of upcoming and ongoing hack-a-thons overview 
        right from this command!
        '''
        
        api_response = await self.bot.session.get('https://cache.showwcase.com/hackathons')
        data = await api_response.json()

        if not len(data):
            return await ctx.send('Uh-oh! There are no upcoming and ongoing Hack-a-thons right now! Check back later.', ephemeral = True)
        
        view = HackathonsView(ctx.author, self.bot, data)
        view.check_disability()
        await view.update_embed_page()

        resp_message = await ctx.send(embed = view.embed, view = view, ephemeral = False)
        await view.resolve_message(ctx, resp_message)

def setup(bot: commands.Bot):
    bot.add_cog(Hackathon(bot))