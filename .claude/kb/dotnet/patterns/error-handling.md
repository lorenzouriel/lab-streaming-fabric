# Error Handling

> **Purpose**: Exception hierarchy, custom exceptions, the Result pattern, and global error handling in ASP.NET Core
> **MCP Validated:** 2026-04-14

## When to Use

- Defining domain-specific exception hierarchies
- Building resilient services with typed failure handling
- Wrapping third-party/SDK exceptions at adapter boundaries
- Returning structured error responses from an API

## Implementation

### Custom Exception Hierarchy

```csharp
public abstract class AppException(string message, string code) : Exception(message)
{
    public string Code { get; } = code;
}

public sealed class ValidationException(string message, string fieldName)
    : AppException(message, "VALIDATION_ERROR")
{
    public string FieldName { get; } = fieldName;
}

public sealed class NotFoundException(string resource, string identifier)
    : AppException($"{resource} not found: {identifier}", "NOT_FOUND")
{
    public string Resource { get; } = resource;
    public string Identifier { get; } = identifier;
}

public sealed class ExternalServiceException(string service, int? statusCode = null)
    : AppException($"Service {service} failed (status={statusCode})", "EXTERNAL_ERROR")
{
    public string Service { get; } = service;
    public int? StatusCode { get; } = statusCode;
}
```

### Exception Handling Best Practices

```csharp
private readonly ILogger<OrderProcessor> _logger;

public async Task<Order> ProcessAsync(OrderRequest request, CancellationToken ct)
{
    try
    {
        var validated = Validate(request);
        return await EnrichAsync(validated, ct);
    }
    catch (ValidationException e)
    {
        _logger.LogWarning(e, "Validation failed for field {Field}", e.FieldName);
        throw;
    }
    catch (ExternalServiceException e)
    {
        _logger.LogError(e, "Service {Service} unavailable", e.Service);
        throw;
    }
    catch (Exception e) when (e is not AppException)
    {
        _logger.LogError(e, "Unexpected error processing order");
        throw new AppException($"Processing failed: {e.Message}", "INTERNAL") { };
    }
}
```

## Result Pattern (No Exceptions for Expected Failures)

```csharp
public readonly struct Result<T>
{
    public bool IsSuccess { get; }
    public T? Value { get; }
    public string? Error { get; }

    private Result(bool ok, T? value, string? error) => (IsSuccess, Value, Error) = (ok, value, error);

    public static Result<T> Success(T value) => new(true, value, null);
    public static Result<T> Failure(string error) => new(false, default, error);
}

public Result<int> ParseAmount(string raw) =>
    int.TryParse(raw, out var value)
        ? Result<int>.Success(value)
        : Result<int>.Failure($"Cannot parse '{raw}' as int");

// Usage with pattern matching
var result = ParseAmount("42");
var message = result switch
{
    { IsSuccess: true } r => $"Parsed: {r.Value}",
    _ => $"Error: {result.Error}",
};
```

## Global Exception Handling (ASP.NET Core, `IExceptionHandler`)

```csharp
public sealed class AppExceptionHandler(ILogger<AppExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, Exception exception, CancellationToken ct)
    {
        var (status, code) = exception switch
        {
            NotFoundException => (StatusCodes.Status404NotFound, "NOT_FOUND"),
            ValidationException => (StatusCodes.Status400BadRequest, "VALIDATION_ERROR"),
            _ => (StatusCodes.Status500InternalServerError, "INTERNAL"),
        };

        logger.LogError(exception, "Request failed with {Code}", code);

        httpContext.Response.StatusCode = status;
        await httpContext.Response.WriteAsJsonAsync(
            new { code, message = exception.Message }, cancellationToken: ct);
        return true;
    }
}

// Program.cs
builder.Services.AddExceptionHandler<AppExceptionHandler>();
builder.Services.AddProblemDetails();
// ...
app.UseExceptionHandler();
```

## Retry with Polly

```csharp
services.AddHttpClient<OrdersClient>()
    .AddResilienceHandler("orders-retry", builder =>
    {
        builder.AddRetry(new HttpRetryStrategyOptions
        {
            MaxRetryAttempts = 3,
            BackoffType = DelayBackoffType.Exponential,
            Delay = TimeSpan.FromSeconds(1),
        });
    });
```

## Common Mistakes

### Wrong

```csharp
try
{
    var result = Compute();
}
catch (Exception) // swallows everything, including OperationCanceledException
{
}
```

### Correct

```csharp
try
{
    var result = Compute();
}
catch (Exception e) when (e is InvalidOperationException or FormatException)
{
    _logger.LogWarning(e, "Computation failed, using default");
    result = DefaultValue;
}
```

## Exception Quick Reference

| Principle | Practice |
|-----------|----------|
| Catch specific | `catch (SpecificException e)`, or `when` filters — never bare `catch (Exception)` |
| Preserve stack trace | `throw;` not `throw e;` when rethrowing |
| Log at boundaries | Log once where you handle, not at every raise site |
| Fail fast | `ArgumentNullException.ThrowIfNull`, validate inputs early |
| Custom hierarchy | One base `AppException`, specific typed subclasses |
| Expected failures | Prefer `Result<T>` / `TryX` over exceptions for control flow |

## See Also

- [Nullable Reference Types](../concepts/nullable-reference-types.md)
- [Clean Architecture](clean-architecture.md)
- [Async/Await](../concepts/async-await.md)
