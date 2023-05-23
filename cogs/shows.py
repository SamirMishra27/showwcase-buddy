from disnake import CommandInteraction, Message, Embed, MessageInteraction, ButtonStyle, Colour
from disnake.ui import button, Button
from disnake.ext import commands

from show_article_view import ShowArticleView
from custom_view import CustomView
from utils import SHOWWCASE_LOGO
from datetime import datetime
from typing import List

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