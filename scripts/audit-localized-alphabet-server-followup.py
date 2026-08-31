#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
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
