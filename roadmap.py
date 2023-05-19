from disnake import CommandInteraction, MessageInteraction, ButtonStyle, Embed, Message, Colour, OptionChoice
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
            self, author, channel, bot, roadmap_api_data,
            roadmap_series_data, roadmap_learning_data, *, timeout = 180
        ):
            super().__init__(clear_on_timeout = False, timeout = timeout)

            self.author = author
            self.bot = bot
            self.channel = channel

            self.roadmap_api_data = roadmap_api_data
            self.roadmap_site_url = 'https://www.showwcase.com/roadmap/{id}/{slug}?tab=roadmap'.format(**self.roadmap_api_data)

            self.roadmap_series_data: RoadmapSeriesData = roadmap_series_data
            self.roadmap_learning_data: RoadmapProgress = roadmap_learning_data

            self.curr_page = 0
            self.last_page = self.roadmap_series_data.show_articles_count - 1
            self.category = 'OVERVIEW'

            self.message: Message = None
            self.embed: Embed = None

            self.add_item(Button(label = 'VIEW ON SHOWWCASE', url = self.roadmap_site_url))
            self.overview_embed: Embed = None

            self.next_unread_show_id: int = self.roadmap_series_data[0][1]['id']
            self.next_unread_page: int = 0

            self.make_overview_embed()
            self.find_next_unread_show()

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

    def find_next_unread_show(self):

        for i in range(0, self.last_page + 1):
            _, curr_show = self.roadmap_series_data[i]

            if curr_show['id'] not in self.roadmap_learning_data.completed_shows:
                self.next_unread_show_id = curr_show['id']
                self.next_unread_page = i
                break

    async def send_roadmap_finished_message(self):

        roadmap_name = self.roadmap_learning_data.roadmap_name
        message = (
            f'**{self.author.name}!** You have finished the **{roadmap_name}** Roadmap!\n'
            f'Congratulations! 🙌🎉🍻 You have learnt a new skill.\n\n'
            f'**What\'s next?**\n'
            f'Go to the Roadmap on Showwcase site and claim your certificate!\n'
            f'To claim your certificate, mark all the shows on the *The Roadmap* section '
            f'as completed and then click on *Claim Certificate Of Completion* and claim your credentials!\n\n'
            f'**DEVELOPER TIP!💡**\n'
            f'Share your achievement on the social media! Go out on your [Twitter](https://twitter.com/home), '
            f'[Linkedin](https://www.linkedin.com/) and even on your own [Showwcase](https://www.showwcase.com/) profile!\n'
            f'Tell the world that you\'re learning and you have made the progress!\n\n'
            f'**It\'s not over yet!**\n'
            f'Start making projects or deep dive into more complex topics about this skill! '
            f'Head over to https://www.showwcase.com/explore and explore Shows and Threads '
            f'related to this skill!'
        )

        embed = embed = Embed(colour = Colour.blurple(), description = message)
        try:
            await self.channel.send(embed = embed)
        except Exception as e:
            try:
                await self.author.send(embed = embed)
            except Exception as e: pass

    async def update_completion_percentage(self) -> None:

        shows_completed = len(self.roadmap_learning_data.completed_shows)
        total_shows = self.roadmap_series_data.show_articles_count

        percent = round((shows_completed / total_shows) * 100, 2)
        self.roadmap_learning_data.completion_percentage = percent

        if percent == 100 and not self.roadmap_learning_data.is_finished:
            self.roadmap_learning_data.is_finished = True
            await self.roadmap_learning_data.update_is_finished()
            await self.send_roadmap_finished_message()

    async def mark_show_as_complete(self, show_id):
        
        self.roadmap_learning_data.add_show(show_id)
        current_series = self.roadmap_series_data.find_series_by_show_id(show_id)

        if all([
            show['id'] in self.roadmap_learning_data.completed_shows \
            for show in current_series['projects']
        ]):
            self.roadmap_learning_data.add_series(current_series['id'])

        await self.update_completion_percentage()
        await self.roadmap_learning_data.save_progress()

    async def mark_show_as_incomplete(self, show_id):

        self.roadmap_learning_data.remove_show(show_id)
        current_series = self.roadmap_series_data.find_series_by_show_id(show_id)

        if not all([
            show['id'] not in self.roadmap_learning_data.completed_shows \
            for show in current_series['projects']
        ]):
            self.roadmap_learning_data.remove_series(current_series['id'])

        await self.update_completion_percentage()
        await self.roadmap_learning_data.save_progress()

    @button(label = 'VIEW LEARNING', custom_id = 'TOGGLE_VIEW', style = ButtonStyle.green)
    async def view_roadmap_learning_button(self, button: Button, interaction: MessageInteraction):

        if self.category == 'OVERVIEW':
            self.category = 'LEARNING'

            next_unread_show = self.roadmap_series_data.find_show_article_by_id(self.next_unread_show_id)
            show_name = shorten(next_unread_show['title'], width = 30, placeholder = '...')

            for button_info in [
                ['REFRESH', 'REFRESH', ButtonStyle.blurple, 0, 'refresh_view'],
                ['LAST', 'PAGE_LEFT', ButtonStyle.gray, 1, 'page_left_button'],
                ['READ THIS', 'VIEW_CURR_SHOW', ButtonStyle.green, 1, 'read_curr_show_button'],
                ['NEXT', 'PAGE_RIGHT', ButtonStyle.gray, 1, 'page_right_button'],
                ['NEXT - ' + show_name, 'JUMP_TO_UNREAD', ButtonStyle.green, 2, 'read_next_unread_show_button'],
                ['JUMP TO PAGE', 'JUMP_TO_PAGE', ButtonStyle.gray, 2, 'navigate_to_page_prompt_button']
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
            self.make_overview_embed()

            button.label = 'VIEW LEARNING'
            button.style = ButtonStyle.green
            self.embed = self.overview_embed

            for child_id in (
                'REFRESH', 'PAGE_LEFT', 'VIEW_CURR_SHOW',
                'PAGE_RIGHT', 'JUMP_TO_UNREAD', 'JUMP_TO_PAGE'
            ):
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

    async def read_next_unread_show_button(self, interaction: MessageInteraction):

        self.curr_page = self.next_unread_page
        self.check_disability()

        await self.update_learning_embed()
        await interaction.response.edit_message(embed = self.embed, view = self)

    async def navigate_to_page_prompt_button(self, interaction: MessageInteraction):

        await interaction.response.send_message(f'Which page would you like to jump to? ({1}/{self.last_page + 1})')
        check = lambda x: x.author.id == self.author.id and x.content.isnumeric() and int(x.content) in range(1, self.last_page + 2)
        try:
            message: Message = await self.bot.wait_for('message', timeout = 60, check = check)
            self.curr_page = int(message.content) - 1

            self.check_disability()
            await self.update_learning_embed()
            await self.message.edit(embed = self.embed, view = self)

            await message.delete()
            await interaction.delete_original_message()

        except Exception as e:
            await interaction.delete_original_message()

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

        current_series, current_show = self.roadmap_series_data[self.curr_page]
        total_shows_in_series = len(current_series['projects'])
        
        series_index = self.roadmap_series_data.roadmap_series_data.index(current_series)
        show_index = current_series['projects'].index(current_show)
        current_show_id = current_show['id']

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

        embed.set_image(url = show_article_data['coverImageUrl'])
        self.embed = embed

        self.get_child_by(id = 'VIEW_CURR_SHOW').label = shorten(show_article_data['title'], width = 30, placeholder = '...')
        if self.curr_page == self.next_unread_page:
            self.get_child_by(id = 'JUMP_TO_UNREAD').disabled = True

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
            interaction.author, interaction.channel, self.bot, roadmap_api_data,
            roadmap_series_data, roadmap_learning_data, timeout = 600
        )
        resp_message = await interaction.send(embed = view.embed, view = view, ephemeral = True)
        await view.resolve_message(interaction, resp_message)

def setup(bot: commands.bot):
    bot.add_cog(Roadmap(bot))