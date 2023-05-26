from disnake import CommandInteraction, Message, Embed, MessageInteraction, ButtonStyle, Colour
from disnake.ui import button, Button
from disnake.ext import commands

from show_article_view import ShowArticleView
from custom_view import CustomView
from utils import SHOWWCASE_LOGO
from datetime import datetime
from typing import List
from math import ceil
from urllib.parse import quote
from traceback import print_exception

class UserShowsHistory(CustomView):

    def __init__(self, author, bot, users_show_history):

        self.author = author
        self.bot = bot

        self.users_show_history: list[dict] = users_show_history
        self.curr_page = 0
        self.history_per_page = 10

        self.message: Message = None
        self.embed: Embed = None

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

        embed = Embed(
            title = f"{self.author.name}'s Showwcase reading history",
            colour = Colour.dark_green(),
            description = ''
        )
        list_of_shows = []

        if len(self.users_show_history) < 10:
            list_of_shows = self.users_show_history

        else:
            start_index = self.curr_page * self.history_per_page
            end_index = start_index + self.history_per_page
            list_of_shows = self.users_show_history[start_index : end_index]

        for show_info in list_of_shows:
            embed.description += (
                '- {post_title} \n'.format(**show_info) +
                '> Read on: <t:{0}:F> (<t:{0}:F>)\n'.format(int( show_info['readed_at_timestamp'] )) +
                '> {reading_time} min read\n\n'.format(**show_info)
            )

        self.get_child_by(id = 'PAGE_NO').label = f'{self.curr_page + 1} / {len(self.users_show_history)}'
        self.embed = embed

    def check_disability(self):
        self.enable_all_children()

        if self.curr_page == 0:
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        if self.curr_page == len(self.users_show_history) - 1:
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)

async def jsonize_sql_data(sql_data: List[tuple], specifications: List[list]) -> List[dict]:

    if len(sql_data[0]) != len(specifications):
        raise ValueError('Specifications should have same number of key names as the length of data tuple')

    json_data: list[dict] = []
    for row in sql_data:
        row_object = {}

        for index, key_name in specifications:
            row_object[key_name] = row[index]
        json_data.append(row_object)

    return json_data

class StandaloneShowArticleView(ShowArticleView):

    def __init__(self, author, bot, show_id, show_article_data, *, timeout = 180):
        super().__init__(author, bot, show_id, show_article_data, timeout = timeout)

    async def check_post_status_initial(self):

        query = 'SELECT * FROM post_history WHERE user_id == (?) AND post_id == (?)'
        sql_data = await self.bot.db.execute_fetchall(query, (self.author.id, self.show_id))

        if sql_data:
            button = self.get_child_by(id = 'UPDATE_SHOW_STATUS')

            button.label = 'MARK AS UNREAD'
            button.style = ButtonStyle.gray
            button.emoji = '🟥'

    @button(
        label = 'MARK AS READ', custom_id = 'UPDATE_SHOW_STATUS',
        style = ButtonStyle.green, emoji = '✅', row = 1
    )
    async def update_show_status_button(self, button: Button, interaction: MessageInteraction):

        button = self.get_child_by(id = 'UPDATE_SHOW_STATUS')
        query = 'SELECT * FROM post_history WHERE user_id == (?) AND post_id == (?)'
        sql_data = await self.bot.db.execute_fetchall(query, (self.author.id, self.show_id))

        if not sql_data:
            query = '''
                INSERT INTO post_history(user_id, post_id, post_title,
                post_slug, readed_at, readed_at_timestamp,
                reading_time) VALUES (?,?,?,?,?,?,?)
            '''
            readed_at_datetime = datetime.now()
            if 'readingStats' in self.show_article_data.keys():
                reading_time = ceil(self.show_article_data['readingStats']['time'] / 1000 / 60)
            else:
                reading_time = 2

            to_enter = (
                self.author.id,
                self.show_id,
                self.show_article_data['title'],
                self.show_article_data['slug'],
                str(readed_at_datetime),
                readed_at_datetime.timestamp(),
                reading_time
            )
            await self.bot.db.execute(query, to_enter)
            await self.bot.db.commit()

            button.label = 'MARK AS UNREAD'
            button.style = ButtonStyle.gray
            button.emoji = '🟥'

        elif sql_data:
            query = 'DELETE FROM post_history WHERE user_id == (?) AND post_id == (?)'
            await self.bot.db.execute(query, (self.author.id, self.show_id))
            await self.bot.db.commit()

            button.label = 'MARK AS READ'
            button.style = ButtonStyle.green
            button.emoji = '✅'

        await self.update_show_article_page()
        await interaction.response.edit_message(embed = self.embed, view = self)

class ShowsListView(CustomView):

    def __init__(self, author, bot, shows_list, *, timeout = 180):
        super().__init__(clear_on_timeout = False, timeout = timeout)

        self.author = author
        self.bot = bot

        self.shows_list: list[dict] = shows_list
        self.curr_page = 0

        self.message: Message = None
        self.embed: Embed = None

        self.current_show_id: int = None
        self.current_show_data: dict = None

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

    @button(label = 'READ NOW', custom_id = 'READ_SHOW_ARTICLE', style = ButtonStyle.green, emoji = '📖', row = 2)
    async def read_curr_show_button(self, button: Button, interaction: MessageInteraction):

        api_response = await self.bot.session.get(f'https://cache.showwcase.com/projects/{self.current_show_id}')
        show_api_data = await api_response.json()

        try:
            view = StandaloneShowArticleView(
                self.author, self.bot,
                self.current_show_id,
                show_api_data
            )
            await view.check_post_status_initial()
            await view.update_show_article_page()

            resp_message = await interaction.response.send_message(embed = view.embed, view = view, ephemeral = True)
            await view.resolve_message(interaction, resp_message)

        except Exception as e:
            print_exception(e, e, e.__traceback__)

            show_url = "https://www.showwcase.com/show/{id}/{slug}".format(**show_api_data)
            await interaction.response.send_message(
                f'Failed to load the article! \n'
                f'Here is the link to the show => {show_url}',
                ephemeral = True
            )

    async def update_embed_page(self):

        time_parse_format = '%Y-%m-%dT%H:%M:%S.%fZ'
        page_content = self.jobs_list[self.curr_page]

        self.current_show_data = page_content
        self.current_show_id = page_content['id']

        reading_time = page_content['readingStats']['text']
        show_published_date = datetime.strptime(page_content['publishedDate'], time_parse_format)

        embed = Embed(colour = Colour.orange())
        embed.set_author(
            name = 'Showwcase Shows',
            url = 'https://www.showwcase.com/',
            icon_url = self.bot.user.display_avatar_url
        )
        embed.set_thumbnail(url = SHOWWCASE_LOGO)

        embed.add_field(
            name = page_content['title'],
            value = f'{reading_time} ⏱️',
            inline = False
        )
        embed.add_field(
            name = 'Published on 📺',
            value = f'<t:{ show_published_date.timestamp() }:F>',
            inline = False
        )

        embed.set_image(url = page_content['coverImageUrl'])
        self.embed = embed

    def check_disability(self):

        self.enable_all_children()
        if self.category == 'OVERVIEW':
            return

        if self.curr_page == 0:
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        if self.curr_page == len(self.shows_list) - 1:
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)

class Shows(commands.Cog):
    
    def __init__(self, bot: commands.Bot):

        self.bot = bot

    def cog_load(self):
        self.bot._Shows = self

    @commands.slash_command(name = 'shows')
    async def shows_group_command(self, ctx: CommandInteraction):
        pass

    @shows_group_command.sub_command(name = 'trending')
    async def shows_trending(self, ctx: CommandInteraction):
        
        api_response = await self.bot.session.get('https://cache.showwcase.com/projects/trending')
        shows_list = await api_response.json()

        view = ShowsListView(ctx.author, self.bot, shows_list)
        await view.update_embed_page()

        resp_message = await ctx.response.send_message(embed = view.embed, view = view)
        await view.resolve_message(ctx, resp_message)

    @shows_group_command.sub_command(name = 'recommended')
    async def shows_recommended(self, ctx: CommandInteraction):

        api_response = await self.bot.session.get('https://cache.showwcase.com/projects/recommended')
        shows_list = await api_response.json()

        view = ShowsListView(ctx.author, self.bot, shows_list)
        await view.update_embed_page()

        resp_message = await ctx.response.send_message(embed = view.embed, view = view)
        await view.resolve_message(ctx, resp_message)

    @shows_group_command.sub_command(name = 'search')
    async def search_show(
        self,
        ctx: CommandInteraction,
        key_term: str = commands.Param(name = 'key-term')
    ):
        
        base_url = 'https://cache.showwcase.com/projects'
        base_url += f'?search={key_term}&limit=10'

        api_response = await self.bot.session.get(base_url)
        shows_list = await api_response.json()

        view = ShowsListView(ctx.author, self.bot, shows_list)
        await view.update_embed_page()

        resp_message = await ctx.response.send_message(embed = view.embed, view = view)
        await view.resolve_message(ctx, resp_message)

    @shows_group_command.sub_command(name = 'myhistory')
    async def show_article_history(self, ctx: CommandInteraction):

        query = '''
            SELECT JSON_OBJECT() FROM --TableName-- WHERE user_id == (?) ORDER BY timestamp DESC
        '''
        sql_data = await self.bot.db.execute_fetchall(query, (ctx.author.id,))
        
        if not sql_data:
            return await ctx.send('You have not read any Showwcase articles yet!')
        user_show_history = await jsonize_sql_data(sql_data, {})

        view = UserShowsHistory(ctx.author, self.bot, user_show_history)
        await view.update_embed_page()

        resp_message = await ctx.response.send_message(embed = view.embed, view = view)
        await view.resolve_message(ctx, resp_message)