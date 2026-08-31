#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
path = root / 'tests/Jellyfin.Server.Implementations.Tests/Item/BaseItemRepositoryNameInitialTests.cs'
text = path.read_text()
old = '        Assert.Equal([_number, _omegaA, _alphaTonos, _beta, _latin, _psi, _alphaBase, _omegaZ], ids);\n'
new = '        Assert.Equal([_number, _omegaA, _alphaTonos, _beta, _latin, _psi, _omegaZ, _alphaBase], ids);\n'
if old not in text:
    raise SystemExit('Expected legacy SortName ordering assertion not found')
path.write_text(text.replace(old, new, 1))
