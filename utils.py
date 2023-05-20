SHOWWCASE_LOGO = 'https://media.discordapp.net/attachments/1104488425924612136/1104514328553590834/showwcase_1649326857208.png?width=487&height=487'

def shorten_text_as_it_is(string: str, max_chars: int):

    if len(string) > max_chars:
        return string[:max_chars] + '...'
    
    else:
        return string