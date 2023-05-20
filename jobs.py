from disnake import CommandInteraction, OptionChoice, Message, Embed, MessageInteraction, ButtonStyle, Colour
from disnake.ui import button, Button
from disnake.ext import commands

from custom_view import CustomView
from string import capwords
from utils import SHOWWCASE_LOGO, shorten_text_as_it_is
from datetime import datetime

job_type_choices = []
job_role_choices = []
for string in ('full-time', 'part-time', 'contract', 'freelance', 'internship'):

    readable_string = capwords(string.replace('-', ' '))
    job_type_choices.append(OptionChoice(name = readable_string, value = string))

class JobsView(CustomView):

    def __init__(self, author, bot, jobs_list, *, timeout = 180):
        super().__init__(clear_on_timeout = False, timeout = timeout)

        self.author = author
        self.bot = bot

        self.jobs_list: list[dict] = jobs_list
        self.curr_page = 0

        self.message: Message = None
        self.embed: Embed = None

    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        if interaction.user.id == self.author.id and interaction.message.id == self.message.id:
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

    @button(label = 'READ MORE', custom_id = 'ABOUT', style = ButtonStyle.green, row = 2)
    async def show_job_desc_button(self, button: Button, interaction: MessageInteraction):

        page_content = self.jobs_list[self.curr_page]
        job_description = page_content['description']
        job_info_url = f"https://www.showwcase.com/job/{ page_content['id'] }-{ page_content['slug'] }"

        embed = Embed(
            title = page_content['title'],
            colour = Colour.brand_green(),
            description = shorten_text_as_it_is(job_description, 4080)
        )
        embed.set_author(
            name = 'Jobs On Showwcase',
            url = 'https://www.showwcase.com/jobs',
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_thumbnail(url = SHOWWCASE_LOGO)
        embed.set_footer(text = 'Find Jobs on Showwcase!')

        go_to_job_button = Button(label = 'APPLY NOW!', url = job_info_url)
        await interaction.response.send_message(embed = embed, ephemeral = True, components = [go_to_job_button])

    async def update_embed_page(self):

        time_parse_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        page_content = self.jobs_list[self.curr_page]

        job_description_part = shorten_text_as_it_is(page_content['description'], 1080)
        job_info_site_url = f"https://www.showwcase.com/job/{ page_content['id'] }-{ page_content['slug'] }"

        job_published_date = page_content['publishedDate']
        if not isinstance(job_published_date, int):
            job_published_date = datetime.strptime(job_published_date, time_parse_format)
        else:
            datetime.fromtimestamp(job_published_date / 1000)
        job_info_updated_at = datetime.strptime(page_content['updatedAt'], time_parse_format)

        embed = Embed(
            title = page_content['title'],
            colour = Colour.brand_green(),
            description = job_description_part
        )
        embed.set_author(
            name = 'Jobs On Showwcase',
            url = 'https://www.showwcase.com/jobs',
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_thumbnail(url = SHOWWCASE_LOGO)
        embed.set_footer(text = 'Find Jobs on Showwcase! Info last updated on:')
        embed.timestamp = job_info_updated_at

        embed.add_field(
            name = 'Job Type 💼',
            value = page_content['type'].upper(),
        )
        embed.add_field(
            name = 'Arrangement 🗄️',
            value = page_content['arrangement'].upper(),
        )
        embed.add_field(
            name = 'Location 🌏',
            value = page_content['location'],
        )
        embed.add_field(
            name = 'Required Experience 👨‍🎓',
            value = page_content['experience'],
        )
        embed.add_field(
            name = 'Published At 📅',
            value = f'<t:{job_published_date.timestamp().__int__()}:F>',
        )
        embed.add_field(
            name = 'Tech Stack 💻',
            value = ', '.join(stack['name'] for stack in page_content['stacks'])
        )
        self.embed = embed
        self.get_child_by(id = 'PAGE_NO').label = f'{self.curr_page + 1} / {len(self.jobs_list)}'

        if self.get_child_by(label = 'APPLY NOW!'):
            self.get_child_by(label = 'APPLY NOW!').url = job_info_site_url

        else:
            self.add_item(Button(label = 'APPLY NOW!', url = job_info_site_url))

    def check_disability(self):
        self.enable_all_children()

        self.get_child_by(id = 'PAGE_NO').disabled = True

        if self.curr_page == 0:
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        if self.curr_page == len(self.jobs_list) - 1:
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)

class Jobs(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

    async def cog_load(self):
        self.bot._Jobs = self

        api_response = await self.bot.session.get('https://cache.showwcase.com/jobs/roles')
        job_roles: list[dict] = await api_response.json()

        for role in job_roles:
            job_role_choices.append(OptionChoice(name = role['name'], value = role['id']))

    @commands.slash_command(name = 'jobs')
    async def jobs_group_command(self, ctx: CommandInteraction):
        pass

    @jobs_group_command.sub_command(name = 'search')
    async def search_jobs(
        self,
        ctx: CommandInteraction,
        job_type: str = commands.Param(default = 'NONE', name = 'type-of-job', choices = job_type_choices),
        job_role: str = commands.Param(default = 'NONE', name = 'type-of-role', choices = job_role_choices)
    ):

        base_url = 'https://cache.showwcase.com/jobs'
        if job_type != 'NONE':
            base_url += f'?type={job_type}'

        api_response = await self.bot.session.get(base_url)
        jobs_list = await api_response.json()

        view = JobsView(ctx.author, self.bot, jobs_list)
        await view.update_embed_page()

        resp_message = await ctx.response.send_message(embed = view.embed, view = view)
        await view.resolve_message(ctx, resp_message)

    @jobs_group_command.sub_command(name = 'recommended')
    async def recommended_jobs(self, ctx: CommandInteraction):

        api_response = await self.bot.session.get('https://cache.showwcase.com/jobs/recommended')
        jobs_list = await api_response.json()

        view = JobsView(ctx.author, self.bot, jobs_list)
        await view.update_embed_page()

        resp_message = await ctx.response.send_message(embed = view.embed, view = view)
        await view.resolve_message(ctx, resp_message)

def setup(bot: commands.Bot):
    bot.add_cog(Jobs(bot))