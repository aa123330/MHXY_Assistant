namespace MhxyAssistant.Core.Services;

public interface IBattleHandler
{
    Task<bool> HandleAsync(TaskContext context, CancellationToken cancellationToken);
}
