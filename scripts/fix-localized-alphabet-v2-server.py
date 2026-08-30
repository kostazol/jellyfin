#!/usr/bin/env python3
from pathlib import Path

p = Path('Jellyfin.Server.Implementations/Item/BaseItemMapper.cs')
text = p.read_text(encoding='utf-8')
old = '''            BaseItemDto.ConfigurationManager.Configuration);'''
new = '''            BaseItemDto.ConfigurationManager?.Configuration ?? new MediaBrowser.Model.Configuration.ServerConfiguration());'''
if new not in text:
    if old not in text:
        raise RuntimeError('BaseItemMapper configuration anchor not found')
    text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
