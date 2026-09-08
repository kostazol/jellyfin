using System;
using System.Linq;
using Emby.Server.Implementations.Data;
using Jellyfin.Data.Enums;
using Jellyfin.Database.Implementations.Entities;
using Jellyfin.Database.Implementations.Enums;
using Jellyfin.Server.Implementations.Item;
using MediaBrowser.Controller.Entities;
using Xunit;

namespace Jellyfin.Server.Implementations.Tests.Item;

public sealed class BaseItemRepositoryNameInitialTests : SqliteDbTestFixture
{
    private readonly BaseItemRepository _repository;

    public BaseItemRepositoryNameInitialTests()
    {
        _repository = CreateBaseItemRepository(new ItemTypeLookup());

        using var context = CreateDbContext();
        context.BaseItems.AddRange(
            Item("Άλφα", "alpha", "ά"),
            Item("Αύρα", "aura", "α"),
            Item("Βήτα", "beta", "β"),
            Item("Ωμέγα", "omega", "ω"),
            Item("Ψυχή", "psyche", "ψ"),
            Item("Other", "other", null));
        context.SaveChanges();
    }

    [Theory]
    [InlineData(SortOrder.Ascending, "Other,Άλφα,Αύρα,Βήτα,Ψυχή,Ωμέγα")]
    [InlineData(SortOrder.Descending, "Ωμέγα,Ψυχή,Βήτα,Αύρα,Άλφα,Other")]
    public void GetItems_GroupsAliasesBeforeApplyingSortName(SortOrder direction, string expected)
    {
        var query = CreateQuery(direction);

        Assert.Equal(expected.Split(','), _repository.GetItems(query).Items.Select(item => item.Name));
    }

    [Fact]
    public void GetItems_AppliesPagingAfterInitialOrdering()
    {
        var query = CreateQuery();
        query.StartIndex = 3;
        query.Limit = 2;
        query.EnableTotalRecordCount = true;

        var result = _repository.GetItems(query);

        Assert.Equal(["Βήτα", "Ψυχή"], result.Items.Select(item => item.Name));
        Assert.Equal(6, result.TotalRecordCount);
    }

    [Theory]
    [InlineData(false, "Άλφα,Αύρα")]
    [InlineData(true, "Βήτα,Ωμέγα,Other,Ψυχή")]
    public void GetItems_FiltersNativeInitialsIncludingOther(bool exclude, string expected)
    {
        var query = CreateQuery();
        query.NameInitialSortOrder = [];
        if (exclude)
        {
            query.ExcludeNameInitials = ["Α", "Α\u0301"];
        }
        else
        {
            query.NameInitials = ["Α", "Α\u0301"];
        }

        Assert.Equal(expected.Split(','), _repository.GetItems(query).Items.Select(item => item.Name));
    }

    [Fact]
    public void GetItems_WithoutNativeOrderingPreservesLegacySortName()
    {
        var query = CreateQuery();
        query.NameInitialSortOrder = [];

        Assert.Equal(
            ["Άλφα", "Αύρα", "Βήτα", "Ωμέγα", "Other", "Ψυχή"],
            _repository.GetItems(query).Items.Select(item => item.Name));
    }

    [Theory]
    [InlineData(ItemSortBy.Name)]
    [InlineData(ItemSortBy.SortName)]
    public void GetItems_GroupsAliasesForBothNameSorts(ItemSortBy sortBy)
    {
        var query = CreateQuery();
        query.OrderBy = [(sortBy, SortOrder.Ascending)];

        var names = _repository.GetItems(query).Items.Select(item => item.Name).ToArray();

        Assert.Equal("Other", names[0]);
        Assert.Equal(new[] { "Άλφα", "Αύρα" }.Order(StringComparer.Ordinal), names.Skip(1).Take(2).Order(StringComparer.Ordinal));
        Assert.Equal(["Βήτα", "Ψυχή", "Ωμέγα"], names.Skip(3));
    }

    [Fact]
    public void ApplyOrder_PreservesNonNamePrimarySorting()
    {
        using var context = CreateDbContext();
        var query = CreateQuery();
        query.OrderBy = [(ItemSortBy.DateCreated, SortOrder.Ascending)];
        var withInitials = _repository.ApplyOrder(context.BaseItems, query, context).Select(item => item.Id).ToArray();
        query.NameInitialSortOrder = [];

        Assert.Equal(withInitials, _repository.ApplyOrder(context.BaseItems, query, context).Select(item => item.Id));
    }

    [Fact]
    public void ApplyOrder_PreservesSearchRelevance()
    {
        using var context = CreateDbContext();
        var query = CreateQuery();
        query.SearchTerm = "alpha";
        var withInitials = _repository.ApplyOrder(context.BaseItems, query, context).Select(item => item.Id).ToArray();
        query.NameInitialSortOrder = [];

        Assert.Equal(withInitials, _repository.ApplyOrder(context.BaseItems, query, context).Select(item => item.Id));
    }

    [Fact]
    public void GetItems_KeepsFlatInitialOrderingCompatible()
    {
        var query = CreateQuery();
        query.NameInitialSortOrder = ["Α", "Ά", "Β", "Ψ", "Ω"];

        Assert.Equal(
            ["Other", "Αύρα", "Άλφα", "Βήτα", "Ψυχή", "Ωμέγα"],
            _repository.GetItems(query).Items.Select(item => item.Name));
    }

    [Fact]
    public void GetItems_NormalizesAliasesAndUsesTheirFirstGroup()
    {
        var query = CreateQuery();
        query.NameInitialSortOrder = ["Α|Α\u0301|α", "Β|Α", "Ψ", "Ω", "||"];

        Assert.Equal(
            ["Other", "Άλφα", "Αύρα", "Βήτα", "Ψυχή", "Ωμέγα"],
            _repository.GetItems(query).Items.Select(item => item.Name));
    }

    private static InternalItemsQuery CreateQuery(SortOrder direction = SortOrder.Ascending) => new()
    {
        IncludeItemTypes = [BaseItemKind.Movie],
        OrderBy = [(ItemSortBy.SortName, direction)],
        NameInitialSortOrder = ["Α|Ά", "Β", "Ψ", "Ω|Ώ"]
    };

    private static BaseItemEntity Item(string name, string sortName, string? initial) => new()
    {
        Id = Guid.NewGuid(),
        PresentationUniqueKey = Guid.NewGuid().ToString("N"),
        Type = typeof(MediaBrowser.Controller.Entities.Movies.Movie).FullName!,
        Name = name,
        SortName = sortName,
        SortNameInitial = initial
    };
}
