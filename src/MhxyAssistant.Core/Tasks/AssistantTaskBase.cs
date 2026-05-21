using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Tasks;

public abstract class AssistantTaskBase : IAssistantTask
{
    public abstract string Id { get; }
    public abstract string Name { get; }
    public abstract string Description { get; }

    public async Task RunAsync(TaskContext context, CancellationToken cancellationToken)
    {
        context.Log($"[task] {Name} started");
        await ExecuteAsync(context, cancellationToken).ConfigureAwait(false);
        context.Log($"[task] {Name} finished");
    }

    protected abstract Task ExecuteAsync(TaskContext context, CancellationToken cancellationToken);

    protected static async Task DelayAsync(int milliseconds, CancellationToken cancellationToken)
    {
        await Task.Delay(milliseconds, cancellationToken).ConfigureAwait(false);
    }
}
