using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Tasks;

public abstract class AssistantTaskBase : IAssistantTask
{
    public abstract string Id { get; }
    public abstract string Name { get; }
    public abstract string Description { get; }

    public async Task RunAsync(TaskContext context, CancellationToken cancellationToken)
    {
        context.Log($"[任务] {Name} 开始");
        await ExecuteAsync(context, cancellationToken);
        context.Log($"[任务] {Name} 结束");
    }

    protected abstract Task ExecuteAsync(TaskContext context, CancellationToken cancellationToken);

    protected static async Task DelayAsync(int milliseconds, CancellationToken cancellationToken)
    {
        await Task.Delay(milliseconds, cancellationToken);
    }
}
