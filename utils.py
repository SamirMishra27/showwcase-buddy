from disnake import MessageInteraction
from disnake.ui import Button

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