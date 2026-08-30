from pathlib import Path

# BaseItemMapper: preserve the existing public overload for ABI compatibility,
# but add an explicit configuration overload used by persistence code.
path = Path('Jellyfin.Server.Implementations/Item/BaseItemMapper.cs')
text = path.read_text()
if 'using MediaBrowser.Model.Configuration;' not in text:
    text = text.replace('using MediaBrowser.Model.Entities;\n', 'using MediaBrowser.Model.Configuration;\nusing MediaBrowser.Model.Entities;\n', 1)
old = '''    /// <param name="dto">The DTO.</param>\n    /// <param name="appHost">The application host for path resolution.</param>\n    /// <returns>The database entity.</returns>\n    public static BaseItemEntity Map(BaseItemDto dto, IServerApplicationHost appHost)\n    {\n        var dtoType = dto.GetType();'''
new = '''    /// <param name="dto">The DTO.</param>\n    /// <param name="appHost">The application host for path resolution.</param>\n    /// <returns>The database entity.</returns>\n    public static BaseItemEntity Map(BaseItemDto dto, IServerApplicationHost appHost)\n        => Map(dto, appHost, BaseItemDto.ConfigurationManager.Configuration);\n\n    /// <summary>\n    /// Maps a domain item to its database entity using the supplied sort configuration.\n    /// </summary>\n    /// <param name="dto">The DTO.</param>\n    /// <param name="appHost">The application host for path resolution.</param>\n    /// <param name="configuration">The server configuration used by the sort-name pipeline.</param>\n    /// <returns>The database entity.</returns>\n    public static BaseItemEntity Map(\n        BaseItemDto dto,\n        IServerApplicationHost appHost,\n        ServerConfiguration configuration)\n    {\n        var dtoType = dto.GetType();'''
if old not in text:
    raise SystemExit('BaseItemMapper Map signature block not found')
text = text.replace(old, new, 1)
old = '''        entity.SortNameInitial = BaseItemDto.GetSortNameInitial(\n            !string.IsNullOrEmpty(dto.ForcedSortName) ? dto.ForcedSortName : dto.Name,\n            dto.EnableAlphaNumericSorting,\n            BaseItemDto.ConfigurationManager.Configuration);'''
new = '''        entity.SortNameInitial = BaseItemDto.GetSortNameInitial(\n            !string.IsNullOrEmpty(dto.ForcedSortName) ? dto.ForcedSortName : dto.Name,\n            dto.EnableAlphaNumericSorting,\n            configuration);'''
if old not in text:
    raise SystemExit('BaseItemMapper SortNameInitial block not found')
path.write_text(text.replace(old, new, 1))

# BaseItemRepository already owns the server configuration manager, so use it explicitly.
path = Path('Jellyfin.Server.Implementations/Item/BaseItemRepository.cs')
text = path.read_text()
old = '        return BaseItemMapper.Map(dto, _appHost);'
new = '        return BaseItemMapper.Map(dto, _appHost, _serverConfigurationManager.Configuration);'
if old not in text:
    raise SystemExit('BaseItemRepository Map call not found')
path.write_text(text.replace(old, new, 1))

# ItemPersistenceService: inject the same configuration manager rather than reaching through BaseItem statics.
path = Path('Jellyfin.Server.Implementations/Item/ItemPersistenceService.cs')
text = path.read_text()
if 'using MediaBrowser.Controller.Configuration;' not in text:
    text = text.replace('using MediaBrowser.Controller;\n', 'using MediaBrowser.Controller;\nusing MediaBrowser.Controller.Configuration;\n', 1)
text = text.replace(
    '''    private readonly IDbContextFactory<JellyfinDbContext> _dbProvider;\n    private readonly IServerApplicationHost _appHost;\n    private readonly ILogger<ItemPersistenceService> _logger;''',
    '''    private readonly IDbContextFactory<JellyfinDbContext> _dbProvider;\n    private readonly IServerApplicationHost _appHost;\n    private readonly IServerConfigurationManager _serverConfigurationManager;\n    private readonly ILogger<ItemPersistenceService> _logger;''',
    1)
text = text.replace(
    '''    /// <param name="dbProvider">The database context factory.</param>\n    /// <param name="appHost">The application host.</param>\n    /// <param name="logger">The logger.</param>\n    public ItemPersistenceService(\n        IDbContextFactory<JellyfinDbContext> dbProvider,\n        IServerApplicationHost appHost,\n        ILogger<ItemPersistenceService> logger)\n    {\n        _dbProvider = dbProvider;\n        _appHost = appHost;\n        _logger = logger;\n    }''',
    '''    /// <param name="dbProvider">The database context factory.</param>\n    /// <param name="appHost">The application host.</param>\n    /// <param name="serverConfigurationManager">The server configuration manager.</param>\n    /// <param name="logger">The logger.</param>\n    public ItemPersistenceService(\n        IDbContextFactory<JellyfinDbContext> dbProvider,\n        IServerApplicationHost appHost,\n        IServerConfigurationManager serverConfigurationManager,\n        ILogger<ItemPersistenceService> logger)\n    {\n        _dbProvider = dbProvider;\n        _appHost = appHost;\n        _serverConfigurationManager = serverConfigurationManager;\n        _logger = logger;\n    }''',
    1)
old = '            var entity = BaseItemMapper.Map(item.Item, _appHost);'
new = '            var entity = BaseItemMapper.Map(item.Item, _appHost, _serverConfigurationManager.Configuration);'
if old not in text:
    raise SystemExit('ItemPersistenceService mapper call not found')
path.write_text(text.replace(old, new, 1))

# Mapper test no longer mutates a process-wide static just to supply sort configuration.
path = Path('tests/Jellyfin.Server.Implementations.Tests/Item/BaseItemMapperTests.cs')
text = path.read_text()
text = text.replace('using MediaBrowser.Controller.Configuration;\n', '')
text = text.replace('using MediaBrowser.Controller.Entities;\n', '')
old = '''        var configurationManager = new Mock<IServerConfigurationManager>();\n        configurationManager.SetupGet(manager => manager.Configuration).Returns(new ServerConfiguration());\n        BaseItem.ConfigurationManager = configurationManager.Object;\n\n'''
if old not in text:
    raise SystemExit('BaseItemMapperTests static configuration setup not found')
text = text.replace(old, '', 1)
old = '        var entity = BaseItemMapper.Map(item, Mock.Of<IServerApplicationHost>());'
new = '        var entity = BaseItemMapper.Map(item, Mock.Of<IServerApplicationHost>(), new ServerConfiguration());'
if old not in text:
    raise SystemExit('BaseItemMapperTests mapper call not found')
path.write_text(text.replace(old, new, 1))

# Direct ItemPersistenceService construction in tests gets the same manager it already installs on BaseItem.
path = Path('tests/Jellyfin.Server.Implementations.Tests/Item/ItemPersistenceOwnedRowTests.cs')
text = path.read_text()
old = '''        _service = new ItemPersistenceService(\n            CreateDbContextFactory(),\n            new Mock<IServerApplicationHost>().Object,\n            NullLogger<ItemPersistenceService>.Instance);'''
new = '''        _service = new ItemPersistenceService(\n            CreateDbContextFactory(),\n            new Mock<IServerApplicationHost>().Object,\n            configurationManager.Object,\n            NullLogger<ItemPersistenceService>.Instance);'''
if old not in text:
    raise SystemExit('ItemPersistenceOwnedRowTests constructor call not found')
path.write_text(text.replace(old, new, 1))
