from disnake import MessageInteraction
from disnake.ui import Button

from typing import List
from markdownify import markdownify

SHOWWCASE_LOGO = 'https://media.discordapp.net/attachments/1104488425924612136/1104514328553590834/showwcase_1649326857208.png?width=487&height=487'

def shorten_text_as_it_is(string: str, max_chars: int):

    if len(string) > max_chars:
        return string[:max_chars] + '...'
    
    else:
        return string

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
    
def convert_block_to_markdown(content: List[dict]) -> str:

    markdown_content = ''
    for article_block in content:

        if 'textBlock' in article_block.keys():
            style = article_block['textBlock']['style']

            if style == 2: # Header size 2
                markdown_content += '# ' + markdownify(article_block['textBlock']['value']) + '\n\n'

            elif style == 3: # Header size 3
                markdown_content += '## ' + markdownify(article_block['textBlock']['value']) + '\n\n'

            elif style == 4: # Header size 4
                markdown_content += '### ' + markdownify(article_block['textBlock']['value']) + '\n\n'

            elif style == 5 or style == 6: # Dot & Numbered bullet, respectively
                markdown_content += '- ' + markdownify(article_block['textBlock']['value']) + '\n\n'

            elif style == 7: # Quote block
                markdown_content += '> ' + markdownify(article_block['textBlock']['value']) + '\n\n'

            else: # Plain text
                markdown_content += markdownify(article_block['textBlock']['value']) + '\n\n'

        elif 'codeBlock' in article_block.keys():

            code_language = article_block['codeBlock'].get('language', '').lower()
            code_block = article_block['codeBlock'].get('code', '# No code found')

            markdown_content += f'```{code_language}\n{code_block}\n```\n'

        else:
            continue

    return markdown_content