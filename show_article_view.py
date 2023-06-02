from disnake import Message, Embed, ButtonStyle, MessageInteraction, Colour
from disnake.ui import Button

from utils import SHOWWCASE_LOGO, RedirectButton, convert_block_to_markdown
from custom_view import CustomView
from markdownify import markdownify
from re import sub
from math import floor

class ShowArticleView(CustomView):

    def __init__(
        self,
        author,
        bot,
        show_id,
        show_article_data,
        *, timeout = 180
    ):
        super().__init__(clear_on_timeout = False, timeout = timeout)

        self.author = author
        self.bot = bot

        self.show_id = show_id
        self.show_article_data = show_article_data
        self.show_site_url = "https://www.showwcase.com/show/{id}/{slug}".format(**show_article_data)

        self.curr_page = 0
        self.show_article_parts = []
        self.parts_per_page = 5

        self.message: Message = None
        self.embed: Embed = None

        self.add_item(Button(label = 'READ ON SHOWWCASE', url = self.show_site_url, row = 1))
        self.make_show_article()

    async def interaction_check(self, interaction) -> bool:
        if interaction.user.id == self.author.id:
            return True
        else:
            await interaction.response.send_message('This is not for you!', ephemeral = True)

    def make_show_article(self):

        article_structure = self.show_article_data['structure'].lower()
        show_article_content = None

        if article_structure == 'lexical':
            show_article_content = self.show_article_data['content'][0]['lexicalBlock']['html']

        elif article_structure == 'markdown':
            show_article_content = self.show_article_data['markdown']

        elif article_structure == 'block':
            show_article_content = convert_block_to_markdown(self.show_article_data['content'])

        show_article_markdown = markdownify(show_article_content, heading_style = 'ATX')
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

    def check_disability(self):

        self.enable_all_children()

        if self.curr_page == 0 and self.get_child_by(id = 'PAGE_LEFT'):
            self.get_child_by(id = 'PAGE_LEFT').disabled = True

        max_pages = floor( (len(self.show_article_parts) - 1) / self.parts_per_page )
        if self.curr_page == max_pages and self.get_child_by(id = 'PAGE_RIGHT'):
            self.get_child_by(id = 'PAGE_RIGHT').disabled = True

    async def teardown(self):
        self.disable_all_children()
        await self.message.edit(embed = self.embed, view = self)