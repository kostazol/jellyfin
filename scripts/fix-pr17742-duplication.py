from pathlib import Path

root = Path('.')

controllers = [
    'Jellyfin.Api/Controllers/ArtistsController.cs',
    'Jellyfin.Api/Controllers/GenresController.cs',
    'Jellyfin.Api/Controllers/ItemsController.cs',
    'Jellyfin.Api/Controllers/MusicGenresController.cs',
    'Jellyfin.Api/Controllers/StudiosController.cs',
]

old_docs = '''    /// <param name="nameInitials">Optional filter by the pre-transliteration sort-name initial. Allows multiple, comma delimited.</param>\n    /// <param name="excludeNameInitials">Optional filter excluding pre-transliteration sort-name initials. Allows multiple, comma delimited.</param>\n    /// <param name="nameInitialSortOrder">Optional ordered list of pre-transliteration initials used to group SortName/Name ordering. Allows multiple, comma delimited.</param>'''
new_docs = '''    /// <param name="nameInitialQuery">Optional pre-transliteration sort-name initial filtering and ordering.</param>'''

old_signature = '''        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] nameInitials,\n        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] excludeNameInitials,\n        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] nameInitialSortOrder,'''
new_signature = '''        [FromQuery] NameInitialQuery nameInitialQuery,'''

old_assignments = '''            NameInitials = nameInitials,\n            ExcludeNameInitials = excludeNameInitials,\n            NameInitialSortOrder = nameInitialSortOrder,'''
new_assignments = '''            NameInitials = [.. nameInitialQuery.NameInitials],\n            ExcludeNameInitials = [.. nameInitialQuery.ExcludeNameInitials],\n            NameInitialSortOrder = [.. nameInitialQuery.NameInitialSortOrder],'''

for relative in controllers:
    path = root / relative
    text = path.read_text()
    if 'using Jellyfin.Api.Models;' not in text:
        marker = 'using Jellyfin.Api.ModelBinders;\n'
        if marker not in text:
            raise SystemExit(f'ModelBinders using not found in {relative}')
        text = text.replace(marker, marker + 'using Jellyfin.Api.Models;\n', 1)

    if old_docs not in text:
        raise SystemExit(f'Expected docs block not found in {relative}')
    text = text.replace(old_docs, new_docs)

    if old_signature not in text:
        raise SystemExit(f'Expected signature block not found in {relative}')
    text = text.replace(old_signature, new_signature)

    if old_assignments not in text:
        raise SystemExit(f'Expected assignment block not found in {relative}')
    text = text.replace(old_assignments, new_assignments)

    # The legacy Items endpoint forwards the grouped query model to the main endpoint.
    text = text.replace(
        '''            nameInitials,\n            excludeNameInitials,\n            nameInitialSortOrder,''',
        '''            nameInitialQuery,''')

    path.write_text(text)

# Trailers uses the shared ItemsController implementation but does not expose these query options.
trailers = root / 'Jellyfin.Api/Controllers/TrailersController.cs'
text = trailers.read_text()
if 'using Jellyfin.Api.Models;' not in text:
    marker = 'using Jellyfin.Api.ModelBinders;\n'
    if marker not in text:
        raise SystemExit('ModelBinders using not found in TrailersController')
    text = text.replace(marker, marker + 'using Jellyfin.Api.Models;\n', 1)
old = '''                nameStartsWithOrGreater,\n                nameStartsWith,\n                nameLessThan,\n                [],\n                [],\n                [],\n                studioIds,'''
new = '''                nameStartsWithOrGreater,\n                nameStartsWith,\n                nameLessThan,\n                new NameInitialQuery(),\n                studioIds,'''
if old not in text:
    raise SystemExit('Expected forwarding block not found in TrailersController')
trailers.write_text(text.replace(old, new, 1))

model_path = root / 'Jellyfin.Api/Models/NameInitialQuery.cs'
model_path.write_text('''using System.Collections.Generic;\nusing Jellyfin.Api.ModelBinders;\nusing Microsoft.AspNetCore.Mvc;\n\nnamespace Jellyfin.Api.Models;\n\n/// <summary>\n/// Query options for filtering and ordering items by their pre-transliteration sort-name initial.\n/// </summary>\npublic class NameInitialQuery\n{\n    /// <summary>\n    /// Gets or sets the initials to include.\n    /// </summary>\n    [FromQuery(Name = "nameInitials")]\n    [ModelBinder(typeof(CommaDelimitedCollectionModelBinder))]\n    public IReadOnlyList<string> NameInitials { get; set; } = [];\n\n    /// <summary>\n    /// Gets or sets the initials to exclude.\n    /// </summary>\n    [FromQuery(Name = "excludeNameInitials")]\n    [ModelBinder(typeof(CommaDelimitedCollectionModelBinder))]\n    public IReadOnlyList<string> ExcludeNameInitials { get; set; } = [];\n\n    /// <summary>\n    /// Gets or sets the ordered initials used to group SortName or Name ordering.\n    /// </summary>\n    [FromQuery(Name = "nameInitialSortOrder")]\n    [ModelBinder(typeof(CommaDelimitedCollectionModelBinder))]\n    public IReadOnlyList<string> NameInitialSortOrder { get; set; } = [];\n}\n''')
