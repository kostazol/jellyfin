#!/usr/bin/env python3
from pathlib import Path

path = Path('src/apps/modern/features/libraries/components/AlphabetPicker.tsx')
text = path.read_text(encoding='utf-8')

text = text.replace("import Paper from '@mui/material/Paper';\n", '')

old = '''            {!localizedGroups ? (\n                <Paper\n                    elevation={0}\n                    sx={{\n                        borderRadius: 1,\n                        overflow: 'hidden'\n                    }}\n                >\n                    <AlphabetButtons values={LETTER_VALUES} value={value} onChange={handleValue} />\n                </Paper>\n            ) : localizedGroups.map((group, groupIndex) => (\n                <Paper\n                    key={group.id}\n                    elevation={0}\n                    sx={{\n                        borderRadius: 1,\n                        overflow: 'hidden'\n                    }}\n                >\n                    <AlphabetButtons\n                        values={groupIndex === 0 ? ['#', ...group.values] : group.values}\n                        value={value}\n                        onChange={handleValue}\n                    />\n                </Paper>\n            ))}\n'''
new = '''            {!localizedGroups ? (\n                <AlphabetButtons values={LETTER_VALUES} value={value} onChange={handleValue} />\n            ) : localizedGroups.map((group, groupIndex) => (\n                <React.Fragment key={group.id}>\n                    <AlphabetButtons\n                        values={groupIndex === 0 ? ['#', ...group.values] : group.values}\n                        value={value}\n                        onChange={handleValue}\n                    />\n                </React.Fragment>\n            ))}\n'''

if old not in text:
    raise RuntimeError('Expected current-master Paper picker layout was not found')

path.write_text(text.replace(old, new, 1), encoding='utf-8')
