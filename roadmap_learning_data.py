from disnake.ext.commands import Bot
from disnake import Member, User

from typing import Union
from json import loads, dumps
from datetime import datetime

class RoadmapProgress:

    def __init__(
        self,
        bot: Bot,
        user: Union[Member, User],
        roadmap_id: int,
        roadmap_name: str
    ) -> None:

        self.bot = bot

        self.user = user
        self.user_id = user.id

        # DEFINE DATATYPES
        self.roadmap_id: int = roadmap_id
        self.roadmap_name: str = roadmap_name

        self.completed_series: list[int] = []
        self.completed_shows: list[int] = []

        self.completion_percentage: float = 0.0
        self.is_finished: bool = False

        self.started_at: str = str(datetime.now())
        self.last_updated_at: str = self.started_at

    @classmethod
    async def cache_existing_data(
        cls,
        bot: Bot,
        user: Union[Member, User],
        sql_data: list
    ):

        roadmap_id = sql_data[1]
        roadmap_name = sql_data[2]

        roadmap_learning_data = cls(bot, user, roadmap_id, roadmap_name)
        roadmap_learning_data.completed_series = loads(sql_data[3])
        roadmap_learning_data.completed_shows = loads(sql_data[4])

        roadmap_learning_data.completion_percentage = float(sql_data[5])
        roadmap_learning_data.is_finished = True if sql_data[6] == 'TRUE' else False

        time_parse_format = '%Y-%m-%d %H:%M:%S.%f'
        roadmap_learning_data.started_at = datetime.strptime(sql_data[7], time_parse_format)
        roadmap_learning_data.last_updated_at = datetime.strptime(sql_data[8], time_parse_format)

        return roadmap_learning_data
    
    async def create_new(self):

        query = '''
            INSERT INTO roadmaps(user_id, roadmap_id, roadmap_name,
            completed_series, completed_posts, completion_percentage, is_finished,
            started_at, last_updated_at) VALUES (?,?,?,?,?,?,?,?,?)
        '''

        to_enter = (
            self.user_id,
            self.roadmap_id,
            self.roadmap_name,
            dumps(self.completed_series),
            dumps(self.completed_shows),
            self.completion_percentage,
            'TRUE' if self.is_finished else 'FALSE',
            self.started_at,
            self.last_updated_at
        )
        await self.bot.db.execute(query, to_enter)
        await self.bot.db.commit()

    async def save_all(self):

        query = '''
            UPDATE roadmaps
            SET completed_series = (?),
                completed_posts = (?),
                completion_percentage = (?),
                is_finished = (?),
                started_at = (?),
                last_updated_at = (?)
            WHERE user_id == (?)
            AND roadmap_id == (?);
        '''

        to_enter = (
            dumps(self.completed_series), dumps(self.completed_shows),
            self.completion_percentage, 'TRUE' if self.is_finished else 'FALSE',
            self.started_at, self.last_updated_at,
            self.user_id, self.roadmap_id
        )
        await self.bot.db.execute(query, to_enter)
        await self.bot.db.commit()

    async def save_progress(self):

        query = '''
            UPDATE roadmaps
            SET completed_series = (?),
                completed_posts = (?),
                completion_percentage = (?),
                last_updated_at = (?)
            WHERE user_id == (?)
            AND roadmap_id == (?);
        '''

        to_enter = (
            dumps(self.completed_series), dumps(self.completed_shows),
            self.completion_percentage, self.last_updated_at,
            self.user_id, self.roadmap_id
        )
        await self.bot.db.execute(query, to_enter)
        await self.bot.db.commit()

    async def update_is_finished(self):

        await self.bot.db.execute(
            'UPDATE roadmaps SET is_finished = (?) WHERE user_id == (?) AND roadmap_id == (?);',
            ('TRUE' if self.is_finished else 'FALSE', self.user_id, self.roadmap_id)
        )
        await self.bot.db.commit()

    def add_show(self, show_article_id):

        self.completed_shows.append(show_article_id)
        self.last_updated_at = str(datetime.now())

    def add_series(self, series_id):

        self.completed_series.append(series_id)
        self.last_updated_at = str(datetime.now())

    def remove_show(self, show_article_id):

        self.completed_shows.remove(show_article_id)
        self.last_updated_at = str(datetime.now())

    def remove_series(self, series_id):

        self.completed_series.remove(series_id)
        self.last_updated_at = str(datetime.now())