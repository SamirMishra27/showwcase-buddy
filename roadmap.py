from disnake import CommandInteraction, MessageInteraction, ButtonStyle, Embed, Message, Colour
from disnake.ui import button, Button
from disnake.ext import commands

from custom_view import CustomView
from utils import SHOWWCASE_LOGO
from roadmap_learning_data import RoadmapProgress
from roadmap_series_data import RoadmapSeriesData

from datetime import datetime
from string import capwords
from textwrap import shorten
from json import loads
from markdownify import markdownify
from re import sub
from math import floor
from typing import Union
from asyncio import sleep as asyncio_sleep

async def existing_roadmaps_autocomplete(interaction: CommandInteraction, string: str):

    bot = interaction.bot
    query = 'SELECT roadmap_id, roadmap_name FROM roadmaps WHERE user_id = (?)'
    
    results = await bot.db.execute_fetchall(query, (interaction.author.id,))
    if not results:
        return []
    
    return [ OptionChoice(name = row[1], value = row[0]) for row in results ]

class RedirectButton(Button):

    def __init__(self, style, label, custom_id, emoji, row, func_name):
        super().__init__(
            style = style,
            label = label,
            disabled = False,
            custom_id = custom_id,
            emoji = emoji,
            row = row
        )
        self.func_name = func_name

    async def callback(self, interaction: MessageInteraction):
        return await getattr(self.view, self.func_name)(interaction)

class ShowArticleView(CustomView):

    def __init__(
            self, author, bot,
            show_id,
            show_article_data,
            roadmap_learning_data,
            roadmap_learning_view,
            *, timeout = 180
        ):
            super().__init__(clear_on_timeout = False, timeout = timeout)

            self.author = author
            self.bot = bot

            self.show_id = show_id
            self.show_article_data = show_article_data
            self.show_site_url = "https://www.showwcase.com/show/{id}/{slug}".format(**show_article_data)

            self.roadmap_learning_data: RoadmapProgress = roadmap_learning_data
            self.roadmap_learning_view: RoadmapLearningView = roadmap_learning_view

            self.curr_page = 0
            self.show_article_parts = []
            self.parts_per_page = 5

            self.message: Message = None
            self.embed: Embed = None

            self.add_item(Button(label = 'READ ON SHOWWCASE', url = self.show_site_url, row = 1))
            self.make_show_article()

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id == self.author.id and interaction.message.id == self.message.id:
            return True
        else:
            await interaction.response.send_message('This is not for you!', ephemeral = True)

    def make_show_article(self):

        show_article_content = self.show_article_data['content'][0]['lexicalBlock']['html']
        show_article_markdown = markdownify(show_article_content, heading_style = 'ATX_CLOSED')

        show_article_markdown = sub('[#]{1,6}', '**', show_article_markdown)
        self.show_article_parts = show_article_markdown.split('\n\n')

        if len(self.show_article_parts) > 5:

            for button_info in [
                ['LAST', 'PAGE_LEFT', ButtonStyle.blurple, '◀️', 0, 'page_left_button'],
                ['NEXT', 'PAGE_RIGHT', ButtonStyle.blurple, '▶️', 0, 'page_right_button']
            ]:
                self.add_item(RedirectButton(
                    label = button_info[0], custom_id = button_info[1],
                    style = button_info[2], emoji = button_info[3], row = button_info[4],
                    func_name = button_info[5]
                ))
        self.check_disability()

    async def update_show_article_page(self):

        start_index = self.curr_page * self.parts_per_page
        end_index = start_index + self.parts_per_page

        embed = Embed(
            colour = Colour.purple(),
            description = '\n\n'.join(self.show_article_parts[ start_index : end_index ])
        )
        embed.set_author(name = 'Reading - ' + self.show_article_data['title'])
        embed.set_thumbnail(SHOWWCASE_LOGO)
        self.embed = embed

        if self.show_id in self.roadmap_learning_data.completed_shows:
            button = self.get_child_by(id = 'UPDATE_SHOW_STATUS')

            button.label = 'MARK AS INCOMPLETE'
            button.style = ButtonStyle.gray
            button.emoji = '🟥'

    async def page_left_button(self, interaction: MessageInteraction):

        self.curr_page -=  1
        self.check_disability()

        await self.update_show_article_page()
        await interaction.response.edit_message(embed = self.embed, view = self)

    async def page_right_button(self, interaction: MessageInteraction):
        
        self.curr_page += 1
        self.check_disability()

        await self.update_show_article_page()
        await interaction.response.edit_message(embed = self.embed, view = self)

    @button(
        label = 'MARK AS COMPLETE', custom_id = 'UPDATE_SHOW_STATUS',
        style = ButtonStyle.green, emoji = '✅', row = 1
    )
    async def update_show_status_button(self, button: Button, interaction: MessageInteraction):

        if self.show_id in self.roadmap_learning_data.completed_shows:

            await self.roadmap_learning_view.mark_show_as_incomplete(self.show_id)
            button_details = ['MARK AS COMPLETE', ButtonStyle.green, '✅']

        else:
            await self.roadmap_learning_view.mark_show_as_complete(self.show_id)
            button_details = ['MARK AS INCOMPLETE', ButtonStyle.gray, '🟥']

        button.label = button_details[0]
        button.style = button_details[1]
        button.emoji = button_details[2]

        await self.update_show_article_page()
        await interaction.response.edit_message(embed = self.embed, view = self)

    def check_disability(self):

        self.enable_all_children()

        if self.curr_page == 0:
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        max_pages = floor( (len(self.show_article_parts) - 1) / self.parts_per_page )
        if self.curr_page == max_pages:
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)

class RoadmapLearningView(CustomView):

    def __init__(
            self, author, bot, roadmap_api_data,
            roadmap_series_data, roadmap_learning_data, *, timeout = 180
        ):
            super().__init__(clear_on_timeout = False, timeout = timeout)

            self.author = author
            self.bot = bot

            self.roadmap_api_data = roadmap_api_data
            self.roadmap_site_url = 'https://www.showwcase.com/roadmap/{id}/{slug}?tab=roadmap'.format(**self.roadmap_api_data)

            self.roadmap_series_data: RoadmapSeriesData = roadmap_series_data
            self.roadmap_learning_data: RoadmapProgress = roadmap_learning_data

            self.curr_page = 0
            self.last_page = -1
            self.category = 'OVERVIEW'

            self.message: Message = None
            self.embed: Embed = None

            self.add_item(Button(label = 'VIEW ON SHOWWCASE', url = self.roadmap_site_url))
            for series in self.roadmap_series_data:
                self.last_page += len(series['projects'])

            self.overview_embed: Embed = None
            self.make_overview_embed()

    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        if interaction.user.id == self.author.id and interaction.message.id == self.message.id:
            return True
        else:
            await interaction.response.send_message('This is not for you!', ephemeral = True)

    def make_overview_embed(self):

        embed = Embed(
            colour = Colour.purple(),
            description = self.roadmap_api_data['info']['description']
        )
        embed.set_author(
            name = 'LEARN - ' + self.roadmap_api_data['title'],
            url = self.roadmap_site_url
        )
        embed.set_thumbnail(url = SHOWWCASE_LOGO)
        embed.set_footer(text = 'Keep Learning! 🙌')

        embed.add_field(
            name = 'You have completed',
            value = '{0} %'.format(self.roadmap_learning_data.completion_percentage),
            inline = False
        )

        embed.add_field(
            name = 'Topics Completed',
            value = f'{ len(self.roadmap_learning_data.completed_series) } / { self.roadmap_series_data.series_count }',
            inline = False
        )

        embed.add_field(
            name = 'Articles Completed',
            value = f'{ len(self.roadmap_learning_data.completed_shows) } / { self.roadmap_series_data.show_articles_count }',
            inline = False
        )
        self.overview_embed = embed
        self.embed = embed

    async def mark_show_as_complete(self, show_id):
        ...
    
    async def mark_show_as_incomplete(self, show_id):
        ...

    @button(label = 'VIEW LEARNING', custom_id = 'TOGGLE_VIEW', style = ButtonStyle.green)
    async def view_roadmap_learning_button(self, button: Button, interaction: MessageInteraction):

        if self.category == 'OVERVIEW':
            self.category = 'LEARNING'

            for button_info in [
                ['REFRESH', 'REFRESH', ButtonStyle.gray, 0, 'refresh_view'],
                ['LAST', 'PAGE_LEFT', ButtonStyle.gray, 1, 'page_left_button'],
                ['READ THIS', 'VIEW_CURR_SHOW', ButtonStyle.green, 1, 'read_curr_show_button'],
                ['NEXT', 'PAGE_RIGHT', ButtonStyle.gray, 1, 'page_right_button']
            ]:
                self.add_item(RedirectButton(
                    label = button_info[0], custom_id = button_info[1],
                    style = button_info[2], emoji = None, row = button_info[3],
                    func_name = button_info[4]
                ))

            button.label = 'GO BACK'
            button.style = ButtonStyle.blurple

            await self.update_learning_embed()
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        else: # self.category == 'LEARNING'
            self.category = 'OVERVIEW'

            button.label = 'VIEW LEARNING'
            button.style = ButtonStyle.green
            self.embed = self.overview_embed

            for child_id in ('REFRESH', 'PAGE_LEFT', 'VIEW_CURR_SHOW', 'PAGE_RIGHT'):
                self.remove_item(self.get_child_by(id = child_id))

        await interaction.response.edit_message(embed = self.embed, view = self)

    async def refresh_view(self, interaction: MessageInteraction):

        await self.update_learning_embed()
        await interaction.response.edit_message(embed = self.embed, view = self)

    async def page_left_button(self, interaction: MessageInteraction):

        self.curr_page -=  1
        self.check_disability()

        await self.update_learning_embed()
        await interaction.response.edit_message(embed = self.embed, view = self)

    async def page_right_button(self, interaction: MessageInteraction):
        
        self.curr_page += 1
        self.check_disability()

        await self.update_learning_embed()
        await interaction.response.edit_message(embed = self.embed, view = self)

    async def read_curr_show_button(self, interaction: MessageInteraction):

        view = ShowArticleView(
            self.author, self.bot,
            self.current_show_id,
            self.current_show_api_data,
            self.roadmap_learning_data, self
        )
        await view.update_show_article_page()

        resp_message = await interaction.response.send_message(embed = view.embed, view = view, ephemeral = True)
        await view.resolve_message(interaction, resp_message)

    async def update_learning_embed(self):

        loop_index = 0
        for series in self.roadmap_series_data:

            found = False
            for show in series['projects']:
                if loop_index == self.curr_page:

                    current_series = series
                    total_shows_in_series = len(series['projects'])

                    series_index = self.roadmap_series_data.index(series)
                    show_index = series['projects'].index(show)
                    current_show_id = show['id']

                    found = True
                    break

                else:
                    loop_index += 1
                    continue
            
            if found: break
            else: continue

        else: 
            return

        api_response = await self.bot.session.get(f'https://cache.showwcase.com/projects/{current_show_id}')
        show_article_data = await api_response.json()
        
        self.current_show_id = current_show_id
        self.current_show_api_data = show_article_data

        series_view_progress_bar = '――'.join([ ('▶' if i == show_index else '▷') for i in range(total_shows_in_series) ])
        embed_description = (
            f"#{ series_index + 1 } - **{ current_series['title'] }**\n"
            f"{ series_view_progress_bar }\n"
        )
        reading_time = show_article_data['readingStats']['text']
        reading_status = 'Marked as completed ✅' if current_show_id in self.roadmap_learning_data.completed_shows else ''

        embed = Embed(
            colour = Colour.purple(),
            description = embed_description
        )
        embed.set_author(
            name = 'LEARN - ' + self.roadmap_api_data['title'],
            url = self.roadmap_site_url
        )
        embed.set_thumbnail(url = SHOWWCASE_LOGO)

        embed.add_field(
            name = show_article_data['title'],
            value = f'{reading_time} ⏱️ \n{reading_status}',
            inline = False
        )

        embed.set_image(url = show_article_data['coverImage'])
        self.embed = embed

        self.get_child_by(id = 'VIEW_CURR_SHOW').label = shorten(show_article_data['title'], width = 30, placeholder = '...')

    def check_disability(self):

        self.enable_all_children()
        if self.category == 'OVERVIEW':
            return

        if self.curr_page == 0:
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        if self.curr_page == self.last_page:
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)

class SeriesView(CustomView):

    def __init__(self, author, bot, roadmap_data, series_data, *, timeout = 180):
        super().__init__(clear_on_timeout = False, timeout = timeout)

        self.author = author
        self.bot = bot

        self.roadmap_data: list[dict] = roadmap_data
        self.series_data: list[dict] = series_data
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
        # TODO: add safety net in case image url still broken

    async def update_embed_page(self):

        series_content = self.series_data[self.curr_page]
        series_site_url = f"https://www.showwcase.com/series/{ series_content['id'] }/{ series_content['slug'] }"

        series_no = self.curr_page + 1
        series_cover_image = series_content['coverImageKey']
        base_url ='https://project-assets.showwcase.com/'

        if base_url not in series_cover_image: # Some cover image urls are broken :/
            series_cover_image = base_url + series_cover_image

        embed = Embed(
            title = f'#{series_no} - ' + series_content['title'],
            colour = int(self.roadmap_data['color'][1:], base = 16),
            description = ''
        )
        embed.set_author(
            name = self.roadmap_data['title'] + ' - Curriculum',
            url = series_site_url,
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_footer(text = 'Learn from Showwcase! 📘')
        embed.set_thumbnail(url = SHOWWCASE_LOGO)

        for show_data in series_content['projects']:

            show_site_url = f"https://www.showwcase.com/show/{ show_data['id'] }/{ show_data['slug'] }"
            show_title = show_data['title']
            reading_time = show_data['readingStats']['text']

            embed.description += (
                f"**[{ show_title }]({ show_site_url })**\n"
                f"{reading_time} ⏱️\n\n"
            )
            embed.set_image(url = series_cover_image)

        self.embed = embed
        self.get_child_by(id = 'PAGE_NO').label = f'{self.curr_page + 1} / {len(self.series_data)}'

        if self.get_child_by(label = 'GO TO ROADMAP'):
            self.get_child_by(label = 'GO TO ROADMAP').url = series_site_url

        else:
            self.add_item(Button(label = 'GO TO ROADMAP', url = series_site_url))

    def check_disability(self):
        self.enable_all_children()

        self.get_child_by(id = 'PAGE_NO').disabled = True

        if self.curr_page == 0:
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        if self.curr_page == len(self.series_data) - 1:
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)

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
        if interaction.user.id == self.author.id and interaction.message.id == self.message.id:
            return True
        else:
            await interaction.response.send_message('This is not for you!', ephemeral = True)

    async def update_learning_button(self, roadmap_id):

        query = 'SELECT * FROM roadmaps WHERE user_id = (?) AND roadmap_id = (?)'
        results = await self.bot.db.execute_fetchall(query, (self.author.id, roadmap_id))

        if not results:
            self.remove_item(self.get_child_by(id = 'CONTINUE_LEARNING'))

            self.add_item(RedirectButton(
                ButtonStyle.green, 'START LEARNING!',
                'START_LEARNING', None, 2, 'start_roadmap_for_user'
            ))

        else:
            self.remove_item(self.get_child_by(id = 'START_LEARNING'))

            self.add_item(RedirectButton(
                ButtonStyle.blurple, 'CONTINUE LEARNING!',
                'CONTINUE_LEARNING', None, 2, 'continue_roadmap_for_user'
            ))

    async def start_roadmap_for_user(self, interaction: MessageInteraction):

        roadmap_api_data = self.data[self.curr_page]
        roadmap_id = roadmap_api_data['id']
        roadmap_name = roadmap_api_data['title']

        roadmap_learning_data = RoadmapProgress(self.bot, self.author, roadmap_id, roadmap_name)
        await roadmap_learning_data.create_new()

        await interaction.response.defer()
        await asyncio_sleep(3)

        message = (
            f'Congratulations {self.author.name}! You have successfully enrolled in '
            f'**{roadmap_name}!** 🎉\n'
            f'Head over to the learning view above ^ and start learning now!\n'
            f'I wish you good luck!'
        )

        await self.continue_roadmap_for_user(interaction)
        await interaction.followup.send(message, ephemeral = True)

    async def continue_roadmap_for_user(self, interaction: MessageInteraction):

        roadmap_api_data = self.data[self.curr_page]
        roadmap_id = roadmap_api_data['id']
        user_id = self.author.id

        cog: Roadmap = interaction.bot.get_cog('Roadmap')
        await cog.send_learn_roadmap_view(interaction, user_id, roadmap_id, roadmap_api_data)

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
    async def show_about_button(self, button: Button, interaction: MessageInteraction):

        page_content = self.data[self.curr_page]
        about_content = page_content['about']
        site_url = f"https://www.showwcase.com/roadmap/{ page_content['id'] }/{ page_content['slug'] }"

        embed = Embed(
            title = page_content['title'],
            colour = int(page_content['color'][1:], base = 16)
        )
        embed.set_author(
            name = 'Showwcase Roadmaps - Learn',
            url = 'https://www.showwcase.com/explore',
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_footer(text = 'Learn from Showwcase! 📘')
        embed.set_thumbnail(url = SHOWWCASE_LOGO)

        if len(about_content) > 4080: # Embed desc limit 4096
            embed.description = about_content[:4080] + '...'

        else:
            embed.description = about_content

        go_to_roadmap_button = Button(label = 'GO TO ROADMAP', url = site_url)
        await interaction.response.send_message(embed = embed, ephemeral = True, components = [go_to_roadmap_button])

    @button(label = 'SEE CURRICULUM', custom_id = 'VIEW_SERIES', style = ButtonStyle.green, row = 2)
    async def show_roadmap_series_button(self, button: Button, interaction: MessageInteraction):

        page_content = self.data[self.curr_page]
        roadmap_id = page_content['id']

        api_response = await self.bot.session.get(f'https://cache.showwcase.com/roadmaps/{roadmap_id}/series')
        data = await api_response.json()

        view = SeriesView(self.author, self.bot, page_content, data)
        view.check_disability()
        await view.update_embed_page()

        resp_message = await interaction.response.send_message(embed = view.embed, view = view, ephemeral = True)
        await view.resolve_message(interaction, resp_message)

    async def update_embed_page(self):

        time_parse_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        page_content = self.data[self.curr_page]

        roadmap_site_url = f"https://www.showwcase.com/roadmap/{ page_content['id'] }/{ page_content['slug'] }"
        roadmap_id = page_content['id']
        await self.update_learning_button(roadmap_id)

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
            name = capwords(page_content['info']['jobs']['label']) + ' 💼',
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
            self.get_child_by(label = 'GO TO ROADMAP').url = roadmap_site_url

        else:
            self.add_item(Button(label = 'GO TO ROADMAP', url = roadmap_site_url))

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

    @commands.slash_command(name = 'roadmapslearn')
    async def learn_roadmap(
        self,
        interaction: CommandInteraction,
        roadmap_id: int = commands.Param(
            name = 'roadmap-name',
            autocomplete = existing_roadmaps_autocomplete
        )
    ):        
        await self.send_learn_roadmap_view(interaction, interaction.author.id, roadmap_id, None)

    async def send_learn_roadmap_view(
        self,
        interaction: Union[CommandInteraction, MessageInteraction],
        user_id,
        roadmap_id,
        roadmap_api_data = None
    ):
        if not roadmap_api_data:
            api_response = await self.bot.session.get(f'https://cache.showwcase.com/roadmaps/{roadmap_id}')
            roadmap_api_data = await api_response.json()

        api_response = await self.bot.session.get(f'https://cache.showwcase.com/roadmaps/{roadmap_id}/series')
        roadmap_series_data = RoadmapSeriesData(self.bot, await api_response.json())

        query = 'SELECT * FROM roadmaps WHERE user_id = (?) AND roadmap_id = (?)'
        sql_data = await self.bot.db.execute_fetchall(query, (user_id, roadmap_id))

        sql_data = sql_data[0]
        roadmap_learning_data: RoadmapProgress = await RoadmapProgress.cache_existing_data(self.bot, interaction.author, sql_data)

        view = RoadmapLearningView(
            interaction.author, self.bot, roadmap_api_data,
            roadmap_series_data, roadmap_learning_data, timeout = 600
        )
        resp_message = await interaction.response.send_message(embed = view.embed, view = view, ephemeral = True)
        await view.resolve_message(interaction, resp_message)

def setup(bot: commands.bot):
    bot.add_cog(Roadmap(bot))