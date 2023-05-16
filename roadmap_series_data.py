from disnake.ext.commands import Bot

class RoadmapSeriesData:

    def __init__(self, bot, roadmap_series_data):

        self.bot: Bot = bot
        self.roadmap_series_data: list[dict] = roadmap_series_data

        self.series_count: int = len(self.roadmap_series_data)
        self.show_articles_count: int = 0

        for series in self.roadmap_series_data:
            self.show_articles_count += len(series['projects'])

    def find_series_by_id(self, series_id):

        for series in self.roadmap_series_data:
            if series['id'] == series_id:
                return series
            
    def find_show_article_by_id(self, show_id):

        for series in self.roadmap_series_data:
            for show_article in series['projects']:
                if show_article['id'] == show_id:
                    return show_article

    def find_series_by_show_id(self, show_id):

        for series in self.roadmap_series_data:
            for show_article in series['projects']:
                if show_article['id'] == show_id:
                    return series

    def __getitem__(self, index) -> tuple:

        loop_index = 0
        for series in self.roadmap_series_data:

            for show in series['projects']:
                if loop_index == index:

                    current_series = series
                    current_show = show

                    return (current_series, current_show)

                else:
                    loop_index += 1

        else: 
            raise IndexError('Index out of range')