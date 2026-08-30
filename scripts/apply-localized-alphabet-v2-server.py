#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f'anchor not found in {path}: {old[:100]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')


def replace_all(path: str, old: str, new: str) -> int:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if old not in text:
        return 0
    count = text.count(old)
    p.write_text(text.replace(old, new), encoding='utf-8')
    return count

# Global server configuration: one switch for all libraries/clients.
replace_once(
    'MediaBrowser.Model/Configuration/ServerConfiguration.cs',
    '    public string UICulture { get; set; } = "en-US";\n',
    '''    public string UICulture { get; set; } = "en-US";\n\n    /// <summary>\n    /// Gets or sets a value indicating whether localized alphabet navigation is enabled.\n    /// </summary>\n    public bool EnableLocalizedAlphabetNavigation { get; set; }\n\n    /// <summary>\n    /// Gets or sets additional writing-system codes enabled for alphabet navigation.\n    /// </summary>\n    public string[] LocalizedAlphabetAdditionalScripts { get; set; } = Array.Empty<string>();\n''')

# Surface the global navigation setting to authenticated clients through SystemInfo.
replace_once(
    'MediaBrowser.Model/System/SystemInfo.cs',
    '    public IReadOnlyList<CastReceiverApplication> CastReceiverApplications { get; set; }\n',
    '''    public IReadOnlyList<CastReceiverApplication> CastReceiverApplications { get; set; }\n\n    /// <summary>\n    /// Gets or sets a value indicating whether localized alphabet navigation is enabled.\n    /// </summary>\n    public bool EnableLocalizedAlphabetNavigation { get; set; }\n\n    /// <summary>\n    /// Gets or sets the locale used to choose the primary alphabet.\n    /// </summary>\n    public string LocalizedAlphabetLocale { get; set; } = string.Empty;\n\n    /// <summary>\n    /// Gets or sets additional writing-system codes enabled for alphabet navigation.\n    /// </summary>\n    public string[] LocalizedAlphabetAdditionalScripts { get; set; } = Array.Empty<string>();\n''')

replace_once(
    'Emby.Server.Implementations/SystemManager.cs',
    '            CastReceiverApplications = _configurationManager.Configuration.CastReceiverApplications\n',
    '''            CastReceiverApplications = _configurationManager.Configuration.CastReceiverApplications,\n            EnableLocalizedAlphabetNavigation = _configurationManager.Configuration.EnableLocalizedAlphabetNavigation,\n            LocalizedAlphabetLocale = _configurationManager.Configuration.UICulture,\n            LocalizedAlphabetAdditionalScripts = _configurationManager.Configuration.LocalizedAlphabetAdditionalScripts\n''')

# Query-level ordered initials are a sorting primitive, not a filter.
replace_once(
    'MediaBrowser.Controller/Entities/InternalItemsQuery.cs',
    '            NameInitials = [];\n            ExcludeNameInitials = [];\n',
    '            NameInitials = [];\n            ExcludeNameInitials = [];\n            NameInitialSortOrder = [];\n')
replace_once(
    'MediaBrowser.Controller/Entities/InternalItemsQuery.cs',
    '        public string[] ExcludeNameInitials { get; set; }\n',
    '        public string[] ExcludeNameInitials { get; set; }\n\n        public string[] NameInitialSortOrder { get; set; }\n')

replace_once(
    'Jellyfin.Server.Implementations/Item/BaseItemRepository.ByName.cs',
    '            NameInitials = filter.NameInitials,\n            ExcludeNameInitials = filter.ExcludeNameInitials,\n',
    '            NameInitials = filter.NameInitials,\n            ExcludeNameInitials = filter.ExcludeNameInitials,\n            NameInitialSortOrder = filter.NameInitialSortOrder,\n')

query_file = Path('Jellyfin.Server.Implementations/Item/BaseItemRepository.QueryBuilding.cs')
text = query_file.read_text(encoding='utf-8')
old = '''        IOrderedQueryable<BaseItemEntity>? orderedQuery = null;\n\n        if (hasSearch)\n'''
new = '''        IOrderedQueryable<BaseItemEntity>? orderedQuery = null;\n\n        var nameInitialSortOrder = NormalizeNameInitials(filter.NameInitialSortOrder);\n        var useNameInitialSortOrder = !hasSearch\n            && nameInitialSortOrder.Length > 0\n            && (orderBy.Length == 0 || orderBy[0].OrderBy is ItemSortBy.SortName or ItemSortBy.Name);\n        if (useNameInitialSortOrder)\n        {\n            var initialRankExpression = BuildNameInitialSortRankExpression(nameInitialSortOrder);\n            var sortOrder = orderBy.Length > 0 ? orderBy[0].SortOrder : SortOrder.Ascending;\n            orderedQuery = sortOrder == SortOrder.Ascending\n                ? query.OrderBy(initialRankExpression)\n                : query.OrderByDescending(initialRankExpression);\n        }\n\n        if (hasSearch)\n'''
if new not in text:
    if old not in text:
        raise RuntimeError('ApplyOrder anchor not found')
    text = text.replace(old, new, 1)

helper_anchor = '''    private IQueryable<BaseItemEntity> ApplySeriesDatePlayedOrder(\n'''
helper = '''    private static Expression<Func<BaseItemEntity, int>> BuildNameInitialSortRankExpression(IReadOnlyList<string> initials)\n    {\n        var entity = Expression.Parameter(typeof(BaseItemEntity), "e");\n        var initial = Expression.Property(entity, nameof(BaseItemEntity.SortNameInitial));\n        Expression rank = Expression.Constant(0); // Other / # sorts before the configured alphabets.\n\n        for (var index = initials.Count - 1; index >= 0; index--)\n        {\n            rank = Expression.Condition(\n                Expression.Equal(initial, Expression.Constant(initials[index], typeof(string))),\n                Expression.Constant(index + 1),\n                rank);\n        }\n\n        return Expression.Lambda<Func<BaseItemEntity, int>>(rank, entity);\n    }\n\n'''
if helper not in text:
    if helper_anchor not in text:
        raise RuntimeError('rank helper anchor not found')
    text = text.replace(helper_anchor, helper + helper_anchor, 1)
query_file.write_text(text, encoding='utf-8')

# Add the API parameter consistently to every BaseItem-backed alphabet endpoint.
controller_paths = [
    'Jellyfin.Api/Controllers/ArtistsController.cs',
    'Jellyfin.Api/Controllers/GenresController.cs',
    'Jellyfin.Api/Controllers/ItemsController.cs',
    'Jellyfin.Api/Controllers/MusicGenresController.cs',
    'Jellyfin.Api/Controllers/StudiosController.cs',
]
for path in controller_paths:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    doc_old = '    /// <param name="excludeNameInitials">Optional filter excluding pre-transliteration sort-name initials. Allows multiple, comma delimited.</param>\n'
    doc_new = doc_old + '    /// <param name="nameInitialSortOrder">Optional ordered list of pre-transliteration initials used to group SortName/Name ordering. Allows multiple, comma delimited.</param>\n'
    if 'name="nameInitialSortOrder"' not in text:
        text = text.replace(doc_old, doc_new)

    sig_old = '        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] nameInitials,\n        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] excludeNameInitials,\n'
    sig_new = sig_old + '        [FromQuery, ModelBinder(typeof(CommaDelimitedCollectionModelBinder))] string[] nameInitialSortOrder,\n'
    if 'string[] nameInitialSortOrder' not in text:
        text = text.replace(sig_old, sig_new)

    assign_old = '            NameInitials = nameInitials,\n            ExcludeNameInitials = excludeNameInitials,\n'
    assign_new = assign_old + '            NameInitialSortOrder = nameInitialSortOrder,\n'
    if 'NameInitialSortOrder = nameInitialSortOrder' not in text:
        text = text.replace(assign_old, assign_new)

    p.write_text(text, encoding='utf-8')

# Positional forwarding in ItemsController legacy endpoint.
p = Path('Jellyfin.Api/Controllers/ItemsController.cs')
text = p.read_text(encoding='utf-8')
legacy_old = '''            nameInitials,\n            excludeNameInitials,\n            studioIds,\n'''
legacy_new = '''            nameInitials,\n            excludeNameInitials,\n            nameInitialSortOrder,\n            studioIds,\n'''
if legacy_new not in text:
    if legacy_old not in text:
        raise RuntimeError('ItemsController legacy forwarding anchor not found')
    text = text.replace(legacy_old, legacy_new, 1)
p.write_text(text, encoding='utf-8')

# Trailers invokes ItemsController positionally and does not expose the localized primitive.
p = Path('Jellyfin.Api/Controllers/TrailersController.cs')
text = p.read_text(encoding='utf-8')
trailers_old = '''                [],\n                [],\n                studioIds,\n'''
trailers_new = '''                [],\n                [],\n                [],\n                studioIds,\n'''
if trailers_new not in text:
    if trailers_old not in text:
        raise RuntimeError('TrailersController forwarding anchor not found')
    text = text.replace(trailers_old, trailers_new, 1)
p.write_text(text, encoding='utf-8')
