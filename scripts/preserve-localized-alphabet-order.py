#!/usr/bin/env python3
from pathlib import Path

path = Path('Jellyfin.Server.Implementations/Item/BaseItemRepository.QueryBuilding.cs')
text = path.read_text(encoding='utf-8')
old = '''    private static string[] NormalizeNameInitials(IEnumerable<string> initials)\n    {\n        return initials\n            .Where(static value => !string.IsNullOrWhiteSpace(value))\n            .Select(static value => value.Normalize().ToLowerInvariant())\n            .Distinct(StringComparer.Ordinal)\n            .ToArray();\n    }\n'''
new = '''    private static string[] NormalizeNameInitials(IEnumerable<string> initials)\n    {\n        var seen = new HashSet<string>(StringComparer.Ordinal);\n        var normalizedInitials = new List<string>();\n        foreach (var value in initials)\n        {\n            if (string.IsNullOrWhiteSpace(value))\n            {\n                continue;\n            }\n\n            var normalized = value.Normalize().ToLowerInvariant();\n            if (seen.Add(normalized))\n            {\n                normalizedInitials.Add(normalized);\n            }\n        }\n\n        return normalizedInitials.ToArray();\n    }\n'''
if new not in text:
    if old not in text:
        raise RuntimeError('NormalizeNameInitials anchor not found')
    text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
