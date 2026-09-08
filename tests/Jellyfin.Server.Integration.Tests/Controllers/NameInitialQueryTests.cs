using System;
using System.Linq;
using System.Net.Http.Json;
using System.Threading.Tasks;
using Jellyfin.Database.Implementations;
using Jellyfin.Database.Implementations.Entities;
using Jellyfin.Extensions.Json;
using MediaBrowser.Controller.Configuration;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Entities.Movies;
using MediaBrowser.Model.Dto;
using MediaBrowser.Model.Querying;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace Jellyfin.Server.Integration.Tests.Controllers;

public sealed class NameInitialQueryTests : IClassFixture<JellyfinApplicationFactory>
{
    private readonly JellyfinApplicationFactory _factory;

    public NameInitialQueryTests(JellyfinApplicationFactory factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task GetItems_BindsNativeInitialOptionsBeforePaging()
    {
        using var client = _factory.CreateClient();
        client.DefaultRequestHeaders.AddAuthHeader(await AuthHelper.CompleteStartupAsync(client));
        var configuration = _factory.Services.GetRequiredService<IServerConfigurationManager>().Configuration;
        Assert.False(configuration.EnableLocalizedAlphabetNavigation);
        var names = new[] { (Name: "Ωμέγα", SortName: "omega"), (Name: "Ψυχή", SortName: "psyche"), (Name: "Άλφα", SortName: "alpha"), (Name: "Αύρα", SortName: "aura"), (Name: "I\u0307stanbul", SortName: "istanbul") };
        var items = names.Select(name => new BaseItemEntity
        {
            Id = Guid.NewGuid(),
            PresentationUniqueKey = Guid.NewGuid().ToString("N"),
            Type = typeof(Movie).ToString(),
            Name = name.Name,
            SortName = name.SortName,
            SortNameInitial = BaseItem.GetSortNameInitial(name.Name, true, configuration)
        }).ToArray();
        using (var context = _factory.Services.GetRequiredService<IDbContextFactory<JellyfinDbContext>>().CreateDbContext())
        {
            context.BaseItems.AddRange(items);
            await context.SaveChangesAsync(TestContext.Current.CancellationToken);
        }

        var ids = string.Join(',', items.Select(item => item.Id));
        var initialOrder = Uri.EscapeDataString("Α|Ά,Ψ,Ω");
        var alphaInitials = Uri.EscapeDataString("Α,Α\u0301");
        var dottedInitial = Uri.EscapeDataString("I\u0307");
        var requests = new[]
        {
            (Options: $"nameInitialSortOrder={initialOrder}&startIndex=2&limit=2", Expected: "Αύρα,Ψυχή", Total: 5),
            (Options: $"sortBy=SortName&sortOrder=Descending&nameInitialSortOrder={initialOrder}", Expected: "Ωμέγα,Ψυχή,Αύρα,Άλφα,I\u0307stanbul", Total: 5),
            (Options: $"nameInitials={alphaInitials}&nameInitialSortOrder={initialOrder}", Expected: "Άλφα,Αύρα", Total: 2),
            (Options: $"excludeNameInitials={alphaInitials}&nameInitialSortOrder={initialOrder}", Expected: "I\u0307stanbul,Ψυχή,Ωμέγα", Total: 3),
            (Options: $"nameInitials={dottedInitial}", Expected: "I\u0307stanbul", Total: 1),
            (Options: "sortBy=SortName", Expected: "Άλφα,Αύρα,I\u0307stanbul,Ωμέγα,Ψυχή", Total: 5)
        };

        foreach (var request in requests)
        {
            using var response = await client.GetAsync($"Items?ids={ids}&includeItemTypes=Movie&enableImages=false&{request.Options}", TestContext.Current.CancellationToken);
            response.EnsureSuccessStatusCode();
            var result = await response.Content.ReadFromJsonAsync<QueryResult<BaseItemDto>>(JsonDefaults.Options, TestContext.Current.CancellationToken);
            Assert.NotNull(result);
            Assert.Equal(request.Expected.Split(','), result.Items.Select(item => item.Name));
            Assert.Equal(request.Total, result.TotalRecordCount);
        }
    }
}
