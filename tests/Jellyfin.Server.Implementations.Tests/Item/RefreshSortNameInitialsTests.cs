using System;
using System.Linq;
using System.Threading.Tasks;
using Jellyfin.Database.Implementations.Entities;
using Jellyfin.Server.Migrations.Routines;
using Jellyfin.Server.ServerSetupApp;
using MediaBrowser.Controller.Configuration;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Entities.Movies;
using MediaBrowser.Model.Configuration;
using Moq;
using Xunit;

namespace Jellyfin.Server.Implementations.Tests.Item;

public sealed class RefreshSortNameInitialsTests : SqliteDbTestFixture
{
    [Fact]
    public async Task PerformAsync_RefreshesFullAndPartialBatchesWhenNavigationDisabled()
    {
        var personId = Guid.NewGuid();
        var forcedId = Guid.NewGuid();
        using (var context = CreateDbContext())
        {
            context.BaseItems.AddRange(Enumerable.Range(0, 10001).Select(index => new BaseItemEntity
            {
                Id = Guid.NewGuid(),
                Type = typeof(Movie).ToString(),
                Name = "I\u0307stanbul",
                SortName = "legacy sort name"
            }));
            context.BaseItems.Add(new BaseItemEntity { Id = personId, Type = typeof(Person).ToString(), Name = "The Ωμέγα", SortName = "legacy person sort name" });
            context.BaseItems.Add(new BaseItemEntity { Id = forcedId, Type = typeof(Movie).ToString(), Name = "Ωμέγα", ForcedSortName = "The Ψυχή", SortName = "legacy forced sort name" });
            await context.SaveChangesAsync(TestContext.Current.CancellationToken);
        }

        var configurationManager = new Mock<IServerConfigurationManager>();
        configurationManager.SetupGet(manager => manager.Configuration).Returns(new ServerConfiguration { EnableLocalizedAlphabetNavigation = false, SortRemoveWords = ["the"] });
        var migration = new RefreshSortNameInitials(Mock.Of<IStartupLogger<RefreshSortNameInitials>>(), CreateDbContextFactory(), configurationManager.Object);

        await migration.PerformAsync(TestContext.Current.CancellationToken);
        await migration.PerformAsync(TestContext.Current.CancellationToken);

        using var verification = CreateDbContext();
        Assert.Equal(10004, verification.BaseItems.Count());
        Assert.Equal(10001, verification.BaseItems.Count(item => item.SortNameInitial == "İ" && item.SortName == "legacy sort name"));
        Assert.Equal("t", verification.BaseItems.Single(item => item.Id.Equals(personId)).SortNameInitial);
        Assert.Equal("ψ", verification.BaseItems.Single(item => item.Id.Equals(forcedId)).SortNameInitial);
        Assert.Equal("legacy person sort name", verification.BaseItems.Single(item => item.Id.Equals(personId)).SortName);
        Assert.Equal("legacy forced sort name", verification.BaseItems.Single(item => item.Id.Equals(forcedId)).SortName);
    }
}
