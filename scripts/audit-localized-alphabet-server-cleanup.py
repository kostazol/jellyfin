#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

# GetItemsByUserIdLegacy delegates to GetItems. The initial DTO-to-explicit-parameter
# rewrite updates its signature, but the delegated call also has to forward all three
# explicit values instead of the removed NameInitialQuery instance.
items_controller = root / 'Jellyfin.Api/Controllers/ItemsController.cs'
text = items_controller.read_text()
old = '''            nameInitialQuery,
            studioIds,
'''
new = '''            nameInitials,
            excludeNameInitials,
            nameInitialSortOrder,
            studioIds,
'''
if old not in text:
    raise SystemExit('Expected legacy delegated nameInitialQuery argument not found in ItemsController')
text = text.replace(old, new, 1)
if 'nameInitialQuery' in text:
    raise SystemExit('Unexpected NameInitialQuery reference remains in ItemsController')
items_controller.write_text(text)
