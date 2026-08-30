from pathlib import Path

controllers = [
    Path('Jellyfin.Api/Controllers/ArtistsController.cs'),
    Path('Jellyfin.Api/Controllers/GenresController.cs'),
    Path('Jellyfin.Api/Controllers/ItemsController.cs'),
    Path('Jellyfin.Api/Controllers/MusicGenresController.cs'),
    Path('Jellyfin.Api/Controllers/StudiosController.cs'),
]

assignment_block = '''            NameInitials = [.. nameInitialQuery.NameInitials],\n            ExcludeNameInitials = [.. nameInitialQuery.ExcludeNameInitials],\n            NameInitialSortOrder = [.. nameInitialQuery.NameInitialSortOrder],\n'''

for path in controllers:
    text = path.read_text()
    expected = text.count(assignment_block)
    if expected == 0:
        raise SystemExit(f'No name-initial assignment block found in {path}')

    for _ in range(expected):
        assignment_index = text.index(assignment_block)
        query_start = text.rfind('var query = new InternalItemsQuery', 0, assignment_index)
        if query_start < 0:
            raise SystemExit(f'Unable to find InternalItemsQuery initializer in {path}')

        text = text[:assignment_index] + text[assignment_index + len(assignment_block):]
        initializer_end = text.find('\n        };', query_start)
        if initializer_end < 0:
            raise SystemExit(f'Unable to find InternalItemsQuery initializer end in {path}')

        insertion_point = initializer_end + len('\n        };')
        text = text[:insertion_point] + '\n        nameInitialQuery.ApplyTo(query);' + text[insertion_point:]

    path.write_text(text)

model = Path('Jellyfin.Api/Models/NameInitialQuery.cs')
text = model.read_text()
if 'using MediaBrowser.Controller.Entities;' not in text:
    text = text.replace(
        'using Jellyfin.Api.ModelBinders;\n',
        'using Jellyfin.Api.ModelBinders;\nusing MediaBrowser.Controller.Entities;\n',
        1)

marker = '''    public IReadOnlyList<string> NameInitialSortOrder { get; set; } = [];\n}'''
replacement = '''    public IReadOnlyList<string> NameInitialSortOrder { get; set; } = [];\n\n    /// <summary>\n    /// Applies the name-initial query options to an internal items query.\n    /// </summary>\n    /// <param name="query">The internal items query.</param>\n    internal void ApplyTo(InternalItemsQuery query)\n    {\n        query.NameInitials = [.. NameInitials];\n        query.ExcludeNameInitials = [.. ExcludeNameInitials];\n        query.NameInitialSortOrder = [.. NameInitialSortOrder];\n    }\n}'''
if marker not in text:
    raise SystemExit('Unable to find NameInitialQuery class end')
model.write_text(text.replace(marker, replacement, 1))
