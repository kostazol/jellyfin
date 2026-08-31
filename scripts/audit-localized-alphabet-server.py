#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

controllers = [
    'Jellyfin.Api/Controllers/ArtistsController.cs',
    'Jellyfin.Api/Controllers/GenresController.cs',
    'Jellyfin.Api/Controllers/ItemsController.cs',
    'Jellyfin.Api/Controllers/MusicGenresController.cs',
    'Jellyfin.Api/Controllers/StudiosController.cs',
]

old_doc = '    /// <param name="nameInitialQuery">Optional pre-transliteration sort-name initial filtering and ordering.</param>\n'
new_doc = (
    '    /// <param name="nameInitials">Optional filter by pre-transliteration sort-name initials. Allows multiple, comma delimited.</param>\n'
    '    /// <param name="excludeNameInitials">Optional filter excluding pre-transliteration sort-name initials. Allows multiple, comma delimited.</param>\n'
    '    /// <param name="nameInitialSortOrder">Optional ordered list of pre-transliteration initials used to group SortName or Name ordering. Allows multiple, comma delimited.</param>\n'
)
old_param = '        [FromQuery] NameInitialQuery nameInitialQuery,\n'
new_param = (
    '        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] nameInitials,\n'
    '        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] excludeNameInitials,\n'
    '        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] nameInitialSortOrder,\n'
)
old_apply = '        nameInitialQuery.ApplyTo(query);\n'
new_apply = (
    '        RequestHelpers.ApplyNameInitialQuery(query, nameInitials, excludeNameInitials, nameInitialSortOrder);\n'
)

for relative in controllers:
    path = root / relative
    text = path.read_text()
    if old_doc not in text or old_param not in text or old_apply not in text:
        raise SystemExit(f'Expected NameInitialQuery pattern not found in {relative}')
    text = text.replace(old_doc, new_doc)
    text = text.replace(old_param, new_param)
    text = text.replace(old_apply, new_apply)
    path.write_text(text)

# Trailers delegates to ItemsController but intentionally does not expose the new parameters itself.
trailers = root / 'Jellyfin.Api/Controllers/TrailersController.cs'
text = trailers.read_text()
old = '                new NameInitialQuery(),\n'
new = '                [],\n                [],\n                [],\n'
if old not in text:
    raise SystemExit('Expected delegated NameInitialQuery call not found in TrailersController')
trailers.write_text(text.replace(old, new))

# Keep the OpenAPI surface explicit while centralizing the repetitive controller-to-query mapping.
helpers = root / 'Jellyfin.Api/Helpers/RequestHelpers.cs'
text = helpers.read_text()
anchor = '    /// <summary>\n    /// Checks if the user can access a user.\n'
method = '''    /// <summary>\n    /// Applies pre-transliteration name-initial filtering and ordering to an item query.\n    /// </summary>\n    /// <param name="query">The item query.</param>\n    /// <param name="nameInitials">Initials to include.</param>\n    /// <param name="excludeNameInitials">Initials to exclude.</param>\n    /// <param name="nameInitialSortOrder">Initials in navigation order.</param>\n    internal static void ApplyNameInitialQuery(\n        InternalItemsQuery query,\n        IReadOnlyList<string> nameInitials,\n        IReadOnlyList<string> excludeNameInitials,\n        IReadOnlyList<string> nameInitialSortOrder)\n    {\n        query.NameInitials = [.. nameInitials];\n        query.ExcludeNameInitials = [.. excludeNameInitials];\n        query.NameInitialSortOrder = [.. nameInitialSortOrder];\n    }\n\n'''
if 'ApplyNameInitialQuery(' not in text:
    if anchor not in text:
        raise SystemExit('RequestHelpers insertion point not found')
    helpers.write_text(text.replace(anchor, method + anchor, 1))

# A nullable column is already NULL for the seeded placeholder; the generated UpdateData is redundant.
migration = root / 'src/Jellyfin.Database/Jellyfin.Database.Providers.Sqlite/Migrations/20260829125247_AddSortNameInitial.cs'
text = migration.read_text()
redundant = '''            migrationBuilder.UpdateData(\n                table: "BaseItems",\n                keyColumn: "Id",\n                keyValue: new Guid("00000000-0000-0000-0000-000000000001"),\n                column: "SortNameInitial",\n                value: null);\n\n'''
if redundant not in text:
    raise SystemExit('Expected redundant migration UpdateData block not found')
migration.write_text(text.replace(redundant, '', 1))

# Expand Unicode coverage around the exact persisted-initial semantics.
tests = root / 'tests/Jellyfin.Controller.Tests/Entities/BaseItemTests.cs'
text = tests.read_text()
old_tests = '''    [Theory]\n    [InlineData("Ωμέγα", "ω")]\n    [InlineData("Ψυχή", "ψ")]\n    [InlineData("The Ωμέγα", "ω")]\n    [InlineData("+ F1", "f")]\n    [InlineData("1917", "1")]\n    [InlineData("🎬 Ωμέγα", "ω")]\n    public void GetSortNameInitial_PreservesNativeScript(string value, string expected)\n    {\n        var config = new ServerConfiguration\n        {\n            SortRemoveWords = ["the", "a", "an"],\n            SortRemoveCharacters = [",", "&", "-", "{", "}", "'"],\n            SortReplaceCharacters = [".", "+", "%"]\n        };\n\n        Assert.Equal(expected, BaseItem.GetSortNameInitial(value, true, config));\n    }\n\n    [Fact]\n    public void GetSortNameInitial_WithoutAlphaNumericSorting_PreservesNativeScript()\n    {\n        Assert.Equal("ω", BaseItem.GetSortNameInitial("  Ωμέγα", false, new ServerConfiguration()));\n    }\n\n'''
new_tests = '''    [Theory]\n    [InlineData("Альфа", "а")]\n    [InlineData("альфа", "а")]\n    [InlineData("Ёлка", "ё")]\n    [InlineData("Йод", "й")]\n    [InlineData("Історія", "і")]\n    [InlineData("Їжак", "ї")]\n    [InlineData("Європа", "є")]\n    [InlineData("Ґанок", "ґ")]\n    [InlineData("Ўсход", "ў")]\n    [InlineData("Ъгъл", "ъ")]\n    [InlineData("Щастие", "щ")]\n    [InlineData("Ωμέγα", "ω")]\n    [InlineData("Ψυχή", "ψ")]\n    [InlineData("Άλφα", "ά")]\n    [InlineData("Α\\u0301λφα", "ά")]\n    [InlineData("éclair", "é")]\n    [InlineData("e\\u0301clair", "é")]\n    [InlineData("The Ωμέγα", "ω")]\n    [InlineData("+ F1", "f")]\n    [InlineData("1917", "1")]\n    [InlineData("🎬 Ωμέγα", "ω")]\n    [InlineData("\\U00010400test", "\\U00010428")]\n    [InlineData("🎬", null)]\n    [InlineData("---", null)]\n    [InlineData("", null)]\n    [InlineData(null, null)]\n    public void GetSortNameInitial_PreservesNormalizedNativeInitial(string? value, string? expected)\n    {\n        var config = new ServerConfiguration\n        {\n            SortRemoveWords = ["the", "a", "an"],\n            SortRemoveCharacters = [",", "&", "-", "{", "}", "'"],\n            SortReplaceCharacters = [".", "+", "%"]\n        };\n\n        Assert.Equal(expected, BaseItem.GetSortNameInitial(value, true, config));\n    }\n\n    [Fact]\n    public void GetSortNameInitial_WithoutAlphaNumericSorting_PreservesNativeScript()\n    {\n        Assert.Equal("ω", BaseItem.GetSortNameInitial("  Ωμέγα", false, new ServerConfiguration()));\n    }\n\n'''
if old_tests not in text:
    raise SystemExit('Expected existing SortNameInitial tests not found')
tests.write_text(text.replace(old_tests, new_tests, 1))

repo_test = root / 'tests/Jellyfin.Server.Implementations.Tests/Item/BaseItemRepositoryNameInitialTests.cs'
repo_test.write_text(r'''using System;\nusing System.Linq;\nusing Jellyfin.Data.Enums;\nusing Jellyfin.Database.Implementations;\nusing Jellyfin.Database.Implementations.Entities;\nusing Jellyfin.Database.Implementations.Enums;\nusing Jellyfin.Server.Implementations.Item;\nusing MediaBrowser.Controller.Entities;\nusing Xunit;\n\nnamespace Jellyfin.Server.Implementations.Tests.Item;\n\npublic sealed class BaseItemRepositoryNameInitialTests : SqliteDbTestFixture\n{\n    private const string MovieType = "MediaBrowser.Controller.Entities.Movies.Movie";\n\n    private readonly BaseItemRepository _repository;\n    private readonly Guid _latin = Guid.NewGuid();\n    private readonly Guid _number = Guid.NewGuid();\n    private readonly Guid _psi = Guid.NewGuid();\n    private readonly Guid _omegaA = Guid.NewGuid();\n    private readonly Guid _omegaZ = Guid.NewGuid();\n\n    public BaseItemRepositoryNameInitialTests()\n    {\n        using (var context = CreateDbContext())\n        {\n            Add(context, _latin, "Omega", "omega", "o");\n            Add(context, _number, "1917", "0000001917", "1");\n            Add(context, _psi, "Ψυχή", "psyche", "ψ");\n            Add(context, _omegaA, "Ω alpha", "alpha", "ω");\n            Add(context, _omegaZ, "Ω zulu", "zulu", "ω");\n            context.SaveChanges();\n        }\n\n        _repository = CreateBaseItemRepository(new ItemTypeLookup());\n    }\n\n    [Fact]\n    public void NameInitials_MatchesCaseInsensitivelyAfterNormalization()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitials = ["Ω"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_omegaA, _omegaZ], ids);\n    }\n\n    [Fact]\n    public void ExcludeNameInitials_KeepsNullOrOtherInitialsOutOfEnabledAlphabet()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            ExcludeNameInitials = ["Ψ", "Ω"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_number, _latin], ids);\n    }\n\n    [Fact]\n    public void NameInitialSortOrder_GroupsBeforeExistingSortNameOrdering()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitialSortOrder = ["Ψ", "Ω"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_number, _latin, _psi, _omegaA, _omegaZ], ids);\n    }\n\n    [Fact]\n    public void NameInitialSortOrder_IsAppliedBeforePagination()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            NameInitialSortOrder = ["Ψ", "Ω"],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)],\n            StartIndex = 2,\n            Limit = 2\n        });\n\n        Assert.Equal([_psi, _omegaA], ids);\n    }\n\n    [Fact]\n    public void EmptyNameInitialOptions_KeepLegacySortNameOrdering()\n    {\n        var ids = Query(new InternalItemsQuery\n        {\n            IncludeItemTypes = [BaseItemKind.Movie],\n            OrderBy = [(ItemSortBy.SortName, SortOrder.Ascending)]\n        });\n\n        Assert.Equal([_number, _omegaA, _latin, _psi, _omegaZ], ids);\n    }\n\n    private Guid[] Query(InternalItemsQuery query)\n        => _repository.GetItemList(query).Select(item => item.Id).ToArray();\n\n    private static void Add(JellyfinDbContext context, Guid id, string name, string sortName, string initial)\n        => context.BaseItems.Add(new BaseItemEntity\n        {\n            Id = id,\n            Type = MovieType,\n            Name = name,\n            SortName = sortName,\n            SortNameInitial = initial,\n            PresentationUniqueKey = id.ToString("N")\n        });\n}\n'''.replace('\\n', '\n'))
