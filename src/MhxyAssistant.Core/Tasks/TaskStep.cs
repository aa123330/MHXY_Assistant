using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Tasks;

public enum StepTransition
{
    Next,
    Repeat,
    RestartFromFirst,
    CompleteTask,
    FailTask,
}

public sealed record StepResult(
    bool Success,
    StepTransition Transition = StepTransition.Next,
    string? Message = null)
{
    public static StepResult Continue(string? message = null) => new(false, StepTransition.Repeat, message);
    public static StepResult Next(string? message = null) => new(true, StepTransition.Next, message);
    public static StepResult Restart(string? message = null) => new(true, StepTransition.RestartFromFirst, message);
    public static StepResult Complete(string? message = null) => new(true, StepTransition.CompleteTask, message);
    public static StepResult Fail(string? message = null) => new(false, StepTransition.FailTask, message);
}

public sealed class TaskStep(
    string name,
    Func<TaskContext, CancellationToken, Task<StepResult>> action,
    TimeSpan? timeout = null,
    int retries = 3,
    Func<TaskContext, CancellationToken, Task<bool>>? verify = null,
    TimeSpan? backoff = null)
{
    public string Name { get; } = name;
    public Func<TaskContext, CancellationToken, Task<StepResult>> Action { get; } = action;
    public Func<TaskContext, CancellationToken, Task<bool>>? Verify { get; } = verify;
    public TimeSpan Timeout { get; } = timeout ?? TimeSpan.FromSeconds(30);
    public int Retries { get; } = Math.Max(1, retries);
    public TimeSpan Backoff { get; } = backoff ?? TimeSpan.FromMilliseconds(500);
    public string? LastError { get; private set; }
    public int AttemptCount { get; private set; }

    public async Task<StepResult> ExecuteAsync(TaskContext context, CancellationToken cancellationToken)
    {
        LastError = null;
        AttemptCount = 0;

        for (var attempt = 0; attempt < Retries; attempt++)
        {
            AttemptCount = attempt + 1;
            var deadline = DateTimeOffset.UtcNow + Timeout;

            while (DateTimeOffset.UtcNow < deadline)
            {
                cancellationToken.ThrowIfCancellationRequested();
                try
                {
                    var result = await Action(context, cancellationToken).ConfigureAwait(false);
                    if (result.Transition == StepTransition.FailTask)
                        return result;

                    if (result.Success)
                    {
                        if (Verify is null || await Verify(context, cancellationToken).ConfigureAwait(false))
                            return result;
                    }

                    if (!string.IsNullOrWhiteSpace(result.Message))
                        LastError = result.Message;
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    LastError = ex.Message;
                    break;
                }

                await Task.Delay(Backoff * AttemptCount, cancellationToken).ConfigureAwait(false);
            }
        }

        return StepResult.Fail(LastError ?? "Step timeout or retry limit reached.");
    }
}

public abstract class StepTaskBase : AssistantTaskBase
{
    private const int MaxConsecutiveErrors = 5;

    protected abstract IReadOnlyList<TaskStep> BuildSteps(TaskContext context);

    protected override async Task ExecuteAsync(TaskContext context, CancellationToken cancellationToken)
    {
        var errorCount = 0;
        var stepIndex = 0;
        var steps = BuildSteps(context);

        while (stepIndex < steps.Count)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var step = steps[stepIndex];
            context.Log($"[Step] {step.Name}");

            if (await HandleAnomaliesAsync(context, cancellationToken).ConfigureAwait(false))
                await Task.Delay(300, cancellationToken).ConfigureAwait(false);

            var result = await step.ExecuteAsync(context, cancellationToken).ConfigureAwait(false);
            if (!result.Success && result.Transition != StepTransition.FailTask)
            {
                errorCount++;
                context.Log($"[Step failed] {step.Name} ({step.AttemptCount}/{step.Retries}) {result.Message ?? step.LastError}");
                if (errorCount >= MaxConsecutiveErrors)
                    throw new InvalidOperationException($"Task stopped after {errorCount} consecutive step failures.");
                continue;
            }

            if (!string.IsNullOrWhiteSpace(result.Message))
                context.Log(result.Message);

            switch (result.Transition)
            {
                case StepTransition.Next:
                    errorCount = 0;
                    stepIndex++;
                    break;
                case StepTransition.Repeat:
                    errorCount = 0;
                    break;
                case StepTransition.RestartFromFirst:
                    errorCount = 0;
                    steps = BuildSteps(context);
                    stepIndex = 0;
                    break;
                case StepTransition.CompleteTask:
                    return;
                case StepTransition.FailTask:
                    throw new InvalidOperationException(result.Message ?? $"Step failed: {step.Name}");
                default:
                    throw new ArgumentOutOfRangeException(nameof(result.Transition));
            }
        }
    }

    protected virtual Task<bool> HandleAnomaliesAsync(TaskContext context, CancellationToken cancellationToken)
    {
        return Task.FromResult(false);
    }
}
