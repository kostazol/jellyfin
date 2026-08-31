#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

# Bring the migration integration test in line with current test conventions.
path = root / 'tests/Jellyfin.Server.Integration.Tests/Migrations/SortNameInitialMigrationTests.cs'
text = path.read_text()
text = text.replace(
    'namespace Jellyfin.Server.Integration.Tests.Migrations;\n',
    'namespace Jellyfin.Server.Integration.Tests.Database;\n')
text = text.replace(
'''    public async Task MigrationAndBackfill_CreateIndexedColumnAndPopulateExistingItems()\n    {\n        using (var context = CreateDbContext())\n        {\n            context.Database.Migrate();\n''',
'''    public async Task MigrationAndBackfill_CreateIndexedColumnAndPopulateExistingItems()\n    {\n        var cancellationToken = TestContext.Current.CancellationToken;\n        using (var context = CreateDbContext())\n        {\n            await context.Database.MigrateAsync(cancellationToken);\n''')
text = text.replace(
'            context.SaveChanges();\n',
'            await context.SaveChangesAsync(cancellationToken);\n')
text = text.replace(
'''            Assert.Equal(1L, (long)command.ExecuteScalar()!);\n''',
'''            Assert.Equal(1L, (long)(await command.ExecuteScalarAsync(cancellationToken))!);\n''')
text = text.replace(
'        await routine.PerformAsync(CancellationToken.None);\n',
'        await routine.PerformAsync(cancellationToken);\n')
text = text.replace(
'''            var omega = await context.BaseItems.SingleAsync(item => item.Name == "Ωμέγα");\n            var forced = await context.BaseItems.SingleAsync(item => item.ForcedSortName == "Ψυχή");\n''',
'''            var omega = await context.BaseItems.SingleAsync(item => item.Name == "Ωμέγα", cancellationToken);\n            var forced = await context.BaseItems.SingleAsync(item => item.ForcedSortName == "Ψυχή", cancellationToken);\n''')
path.write_text(text)

# A sort-order entry may represent several persisted initials that belong to one visual
# navigation bucket. The public query remains backwards compatible: a plain entry is a
# one-initial group, while aliases are separated by '|', e.g. "Α|Ά,Β,...".
query_path = root / 'Jellyfin.Server.Implementations/Item/BaseItemRepository.QueryBuilding.cs'
text = query_path.read_text()
old_order = '''        var nameInitialSortOrder = NormalizeNameInitials(filter.NameInitialSortOrder);\n        var useNameInitialSortOrder = !hasSearch\n            && nameInitialSortOrder.Length > 0\n            && (orderBy.Length == 0 || orderBy[0].OrderBy is ItemSortBy.SortName or ItemSortBy.Name);\n        if (useNameInitialSortOrder)\n        {\n            var initialRankExpression = BuildNameInitialSortRankExpression(nameInitialSortOrder);\n'''
new_order = '''        var nameInitialSortGroups = NormalizeNameInitialSortGroups(filter.NameInitialSortOrder);\n        var useNameInitialSortOrder = !hasSearch\n            && nameInitialSortGroups.Length > 0\n            && (orderBy.Length == 0 || orderBy[0].OrderBy is ItemSortBy.SortName or ItemSortBy.Name);\n        if (useNameInitialSortOrder)\n        {\n            var initialRankExpression = BuildNameInitialSortRankExpression(nameInitialSortGroups);\n'''
if old_order not in text:
    raise SystemExit('Expected name-initial ordering block not found')
text = text.replace(old_order, new_order, 1)

normalize_anchor = '''    private static string[] NormalizeNameInitials(IEnumerable<string> initials)\n    {\n        var seen = new HashSet<string>(StringComparer.Ordinal);\n        var normalizedInitials = new List<string>();\n        foreach (var value in initials)\n        {\n            if (string.IsNullOrWhiteSpace(value))\n            {\n                continue;\n            }\n\n            var normalized = value.Normalize().ToLowerInvariant();\n            if (seen.Add(normalized))\n            {\n                normalizedInitials.Add(normalized);\n            }\n        }\n\n        return normalizedInitials.ToArray();\n    }\n'''
normalize_groups = normalize_anchor + '''\n    private static string[][] NormalizeNameInitialSortGroups(IEnumerable<string> initialGroups)\n    {\n        var seen = new HashSet<string>(StringComparer.Ordinal);\n        var normalizedGroups = new List<string[]>();\n        foreach (var groupValue in initialGroups)\n        {\n            if (string.IsNullOrWhiteSpace(groupValue))\n            {\n                continue;\n            }\n\n            var group = new List<string>();\n            foreach (var value in groupValue.Split('|', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))\n            {\n                var normalized = value.Normalize().ToLowerInvariant();\n                if (seen.Add(normalized))\n                {\n                    group.Add(normalized);\n                }\n            }\n\n            if (group.Count > 0)\n            {\n                normalizedGroups.Add(group.ToArray());\n            }\n        }\n\n        return normalizedGroups.ToArray();\n    }\n'''
if normalize_anchor not in text:
    raise SystemExit('Expected NormalizeNameInitials implementation not found')
text = text.replace(normalize_anchor, normalize_groups, 1)

old_rank = '''    private static Expression<Func<BaseItemEntity, int>> BuildNameInitialSortRankExpression(IReadOnlyList<string> initials)\n    {\n        var entity = Expression.Parameter(typeof(BaseItemEntity), "e");\n        var initial = Expression.Property(entity, nameof(BaseItemEntity.SortNameInitial));\n        Expression rank = Expression.Constant(0); // Other / # sorts before the configured alphabets.\n\n        for (var index = initials.Count - 1; index >= 0; index--)\n        {\n            rank = Expression.Condition(\n                Expression.Equal(initial, Expression.Constant(initials[index], typeof(string))),\n                Expression.Constant(index + 1),\n                rank);\n        }\n\n        return Expression.Lambda<Func<BaseItemEntity, int>>(rank, entity);\n    }\n'''
new_rank = '''    private static Expression<Func<BaseItemEntity, int>> BuildNameInitialSortRankExpression(IReadOnlyList<string[]> initialGroups)\n    {\n        var entity = Expression.Parameter(typeof(BaseItemEntity), "e");\n        var initial = Expression.Property(entity, nameof(BaseItemEntity.SortNameInitial));\n        Expression rank = Expression.Constant(0); // Other / # sorts before the configured alphabets.\n\n        for (var index = initialGroups.Count - 1; index >= 0; index--)\n        {\n            Expression? groupMatch = null;\n            foreach (var groupInitial in initialGroups[index])\n            {\n                var initialMatch = Expression.Equal(initial, Expression.Constant(groupInitial, typeof(string)));\n                groupMatch = groupMatch is null ? initialMatch : Expression.OrElse(groupMatch, initialMatch);\n            }\n\n            if (groupMatch is not null)\n            {\n                rank = Expression.Condition(groupMatch, Expression.Constant(index + 1), rank);\n            }\n        }\n\n        return Expression.Lambda<Func<BaseItemEntity, int>>(rank, entity);\n    }\n'''
if old_rank not in text:
    raise SystemExit('Expected name-initial rank expression not found')
query_path.write_text(text.replace(old_rank, new_rank, 1))

# Clarify the generic grouping syntax in the API documentation without introducing
# any script-specific behavior on the server.
for relative in [
    'Jellyfin.Api/Controllers/ArtistsController.cs',
    'Jellyfin.Api/Controllers/GenresController.cs',
    'Jellyfin.Api/Controllers/ItemsController.cs',
    'Jellyfin.Api/Controllers/MusicGenresController.cs',
    'Jellyfin.Api/Controllers/StudiosController.cs',
]:
    controller = root / relative
    text = controller.read_text()
    text = text.replace(
        'Optional ordered list of pre-transliteration initials used to group SortName or Name ordering. Allows multiple, comma delimited.',
        "Optional ordered list of pre-transliteration initial groups used to group SortName or Name ordering. Groups are comma delimited; equivalent initials within one rank may be separated by '|'.")
    controller.write_text(text)

helpers = root / 'Jellyfin.Api/Helpers/RequestHelpers.cs'
text = helpers.read_text().replace(
    '    /// <param name="nameInitialSortOrder">Initials in navigation order.</param>\n',
    '    /// <param name="nameInitialSortOrder">Initial groups in navigation order.</param>\n')
helpers.write_text(text)

# Replace the generated repository test with one that follows the current fixture/import
# conventions and explicitly verifies that aliases in the same visual bucket share one rank.
repo_test = root / 'tests/Jellyfin.Server.Implementations.Tests/Item/BaseItemRepositoryNameInitialTests.cs'
repo_test.write_text(r'''using System;\nusing System.Linq;\nusing Emby.Server.Implementations.Data;\nusing Jellyfin.Data.Enums;\nusing Jellyfin.Database.Implementations;\nusing Jellyfin.Database.Implementations.Entities;\nusing Jellyfin.Database.Implementations.Enums;\nusing Jellyfin.Server.Implementations.Item;\nusing MediaBrowser.Controller.Entities;\nusing Xunit;\n\nnamespace Jellyfin.Server.Implementations.Tests.Item;\n\npublic sealed class BaseItemRepositoryNameInitialTests : SqliteDbTestFixture\n{\n    private const string MovieType = "MediaBrowser.Controller.Entities.Movies.Movie";\n\n    private readonly BaseItemRepository _repository;\n    private readonly Guid _latin = Guid.NewGuid();\n    private readonly Guid _number = Guid.NewGuid();\n    private readonly Guid _psi = Guid.NewGuid();\n    private readonly Guid _omegaA = Guid.NewGuid();\n    private readonly Guid _omegaZ = Guid.NewGuid();\n    private readonly Guid _alphaBase = Guid.NewGuid();\n    private readonly Guid _alphaTonos = Guid.NewGuid();\n    private readonly Guid _beta = Guid.NewGuid();\n\n    public BaseItemRepositoryNameInitialTests()\n    {\n        using (var context = CreateDbContext())\n        {\n            Add(context, _latin, "Omega", "omega", "o");\n            Add(context, _number, "1917", "0000001917", "1");\n            Add(context, _psi, "Ψυχή", "psyche", "ψ");\n            Add(context, _omegaA, "Ω alpha", "alpha", "ω");\n            Add(context, _omegaZ, "Ω zulu", "zulu", "ω");\n            Add(context, _alphaBase, "Α zulu", "zulu-alpha", "α");\n            Add(context, _alphaTonos, "Ά alpha", "alpha-alpha", "ά");\n            Add(context, _beta, "Β beta", "beta-beta", "β");\n            context.SaveChanges();\n        }\n\n        _repository = CreateBaseItemRepository(new ItemTypeLookup());\n    }\n\n    [Fact]\n    public void NameInitials_MatchesCaseInsensitivelyAfterNormalization()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitials = ["Ω"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_omegaA, _omegaZ], ids);\n    }\n\n    [Fact]\n    public void ExcludeNameInitials_KeepsItemsOutsideEnabledAlphabet()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            ExcludeNameInitials = ["Ψ", "Ω", "Α", "Ά", "Β"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_number, _latin], ids);\n    }\n\n    [Fact]\n    public void NameInitialSortOrder_GroupsBeforeExistingSortNameOrdering()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitialSortOrder = ["Ψ", "Ω"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_number, _alphaTonos, _beta, _latin, _alphaBase, _psi, _omegaA, _omegaZ], ids);\n    }\n\n    [Fact]\n    public void NameInitialSortOrder_EquivalentInitialsShareOneRank()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitials = ["Α", "Ά", "Β"],\n            NameInitialSortOrder = ["Α|Ά", "Β"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_alphaTonos, _alphaBase, _beta], ids);\n    }\n\n    [Fact]\n    public void NameInitialSortOrder_DuplicateAliasesKeepFirstGroupRank()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitials = ["Α", "Ά", "Β"],\n            NameInitialSortOrder = ["Α|Ά", "Ά|Β"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_alphaTonos, _alphaBase, _beta], ids);\n    }\n\n    [Fact]\n    public void NameInitialSortOrder_IsAppliedBeforePagination()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitialSortOrder = ["Ψ", "Ω"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)],\n            StartIndex = 5,\n            Limit = 2\n        });\n\n        Assert.Equal([_psi, _omegaA], ids);\n    }\n\n    [Fact]\n    public void EmptyNameInitialOptions_KeepLegacySortNameOrdering()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_number, _omegaA, _alphaTonos, _beta, _latin, _psi, _alphaBase, _omegaZ], ids);\n    }\n\n    private Guid[] Query(InternalItemsQuery query)\n        => _repository.GetItemList(query).Select(item => item.Id).ToArray();\n\n    private static void Add(JellyfinDbContext context, Guid id, string name, string sortName, string initial)\n        => context.BaseItems.Add(new BaseItemEntity\n        {\n            Id = id,\n            Type = MovieType,\n            Name = name,\n            SortName = sortName,\n            SortNameInitial = initial,\n            PresentationUniqueKey = id.ToString("N")\n        });\n}\n'''.replace('\\n', '\n'))
