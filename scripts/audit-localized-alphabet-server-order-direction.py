#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
query_path = root / 'Jellyfin.Server.Implementations/Item/BaseItemRepository.QueryBuilding.cs'
text = query_path.read_text()
old = '''            var initialRankExpression = BuildNameInitialSortRankExpression(nameInitialSortGroups);\n            var sortOrder = orderBy.Length > 0 ? orderBy[0].SortOrder : SortOrder.Ascending;\n            orderedQuery = sortOrder == SortOrder.Ascending\n                ? query.OrderBy(initialRankExpression)\n                : query.OrderByDescending(initialRankExpression);\n'''
new = '''            var initialRankExpression = BuildNameInitialSortRankExpression(nameInitialSortGroups);\n            orderedQuery = query.OrderBy(initialRankExpression);\n'''
if old not in text:
    raise SystemExit('Expected localized rank ordering block not found')
query_path.write_text(text.replace(old, new, 1))

repo_test = root / 'tests/Jellyfin.Server.Implementations.Tests/Item/BaseItemRepositoryNameInitialTests.cs'
text = repo_test.read_text()
anchor = '''    [Fact]\n    public void NameInitialSortOrder_DuplicateAliasesKeepFirstGroupRank()\n'''
test = '''    [Fact]\n    public void NameInitialSortOrder_KeepsBucketOrderWhenSortNameIsDescending()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitials = ["Α", "Ά", "Β"],\n            NameInitialSortOrder = ["Α|Ά", "Β"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Descending)]\n        });\n\n        Assert.Equal([_alphaBase, _alphaTonos, _beta], ids);\n    }\n\n'''
if anchor not in text:
    raise SystemExit('Repository test insertion point not found')
repo_test.write_text(text.replace(anchor, test + anchor, 1))
