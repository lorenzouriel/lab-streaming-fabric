# Clean Architecture

> **Purpose**: Solution structure, naming conventions, dependency rules, and project setup for .NET 8/9
> **MCP Validated:** 2026-04-14

## When to Use

- Starting a new .NET solution or service
- Refactoring a monolith into clear layers
- Establishing team coding standards
- Structuring a multi-project solution with clear dependency boundaries

## Implementation

### Solution Structure

```text
src/
  MyProject.Domain/            # Business logic, no external dependencies
    Entities/                  # Domain entities
    ValueObjects/               # Records / readonly record structs
    Errors/                     # Domain exceptions, Result error types
    Interfaces/                 # Repository/service abstractions (ports)
  MyProject.Application/       # Use cases, orchestration
    Features/                   # Vertical slices (e.g. CreateOrder/)
    Interfaces/                 # Application-level ports
    Behaviors/                  # Cross-cutting (validation, logging pipeline)
  MyProject.Infrastructure/    # External integrations (adapters)
    Persistence/                 # EF Core DbContext, repositories
    Http/                        # Typed HttpClients
    Messaging/                   # Queue/bus implementations
  MyProject.Api/                # ASP.NET Core host, minimal API endpoints or controllers
    Program.cs
    Endpoints/
tests/
  MyProject.Domain.Tests/
  MyProject.Application.Tests/
  MyProject.Api.Tests/          # WebApplicationFactory integration tests
MyProject.sln
Directory.Build.props           # Shared MSBuild settings (Nullable, LangVersion, analyzers)
Directory.Packages.props        # Central Package Management (CPM)
```

### Dependency Rule

```text
Domain  <--  Application  <--  Infrastructure
(pure)       (orchestrates)     (implements)
                  ^
                  |
                 Api  (composition root: wires DI, hosts endpoints)

Domain has zero package references beyond the BCL.
Application depends only on Domain + its own interfaces.
Infrastructure implements Application/Domain interfaces.
Api references all layers only to wire DI in Program.cs.
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Namespace/Project | `PascalCase`, dotted | `MyProject.Application.Orders` |
| Class / record / interface | `PascalCase` | `OrderService`, `IOrderRepository` |
| Interface prefix | `I` + `PascalCase` | `IOrderRepository` |
| Method | `PascalCase` | `CreateOrderAsync()` |
| Async method | Suffix `Async` | `GetByIdAsync()` |
| Private field | `_camelCase` | `_orderRepository` |
| Local variable / parameter | `camelCase` | `orderId` |
| Constant | `PascalCase` | `MaxRetryCount` |
| Boolean | `Is`/`Has`/`Can` prefix | `IsActive`, `HasErrors` |

## Central Package Management + Directory.Build.props

```xml
<!-- Directory.Build.props -->
<Project>
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
  </PropertyGroup>
</Project>
```

```xml
<!-- Directory.Packages.props -->
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="9.0.0" />
    <PackageVersion Include="xunit" Version="2.9.0" />
  </ItemGroup>
</Project>
```

## Interface Segregation (Ports)

```csharp
namespace MyProject.Application.Interfaces;

public interface IOrderRepository
{
    Task<Order?> GetByIdAsync(string id, CancellationToken ct);
    Task AddAsync(Order order, CancellationToken ct);
}

namespace MyProject.Infrastructure.Persistence;

public sealed class EfOrderRepository(AppDbContext db) : IOrderRepository
{
    public Task<Order?> GetByIdAsync(string id, CancellationToken ct) =>
        db.Orders.FirstOrDefaultAsync(o => o.Id == id, ct);

    public Task AddAsync(Order order, CancellationToken ct)
    {
        db.Orders.Add(order);
        return db.SaveChangesAsync(ct);
    }
}
```

## Function/Method Design

```csharp
// GOOD: single responsibility, clear types, guard clause, descriptive name
public IReadOnlyList<string> ExtractActiveUsernames(
    IEnumerable<UserRecord> records,
    int minAge = 18)
{
    ArgumentNullException.ThrowIfNull(records);

    return [.. records
        .Where(r => r.Status == "active" && r.Age >= minAge)
        .Select(r => r.Username)];
}

// BAD: vague name, boxed object params, multiple responsibilities
public List<object> Process(List<object> data, bool flag = true)
{
    var results = new List<object>();
    foreach (var d in data)
    {
        if (flag) { /* ... */ }
        else { results.Add(d); }
    }
    return results;
}
```

## Minimal API Endpoint Organization

```csharp
public static class OrderEndpoints
{
    public static void MapOrderEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/orders").WithTags("Orders");

        group.MapGet("/{id}", async (string id, IOrderRepository repo, CancellationToken ct) =>
        {
            var order = await repo.GetByIdAsync(id, ct);
            return order is not null ? Results.Ok(order) : Results.NotFound();
        });
    }
}

// Program.cs
app.MapOrderEndpoints();
```

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Clean Alternative |
|-------------|---------|-------------------|
| God service (1000+ lines) | Untestable, unclear responsibility | Split into focused, single-purpose services |
| Magic strings/numbers | Unclear intent | Named constants or enums |
| Deep nesting (3+ levels) | Hard to read | Guard clauses, early returns |
| Anemic domain model with logic in services only | Business rules scattered | Push invariants into entities/value objects |
| Direct `DbContext` injection into controllers | Leaks persistence into API layer | Repository/CQRS behind an interface |
| Static `DateTime.Now` calls | Untestable | Inject `TimeProvider` (.NET 8+) |
| `catch (Exception)` and swallow | Hides bugs | Catch specific exceptions, log at boundary |

## See Also

- [Records](../concepts/records.md)
- [Error Handling](error-handling.md)
- [Nullable Reference Types](../concepts/nullable-reference-types.md)
