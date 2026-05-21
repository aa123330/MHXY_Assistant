using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Tasks;

public sealed class TaskRegistry
{
    private readonly Dictionary<string, Func<IAssistantTask>> _factories = new(StringComparer.OrdinalIgnoreCase);

    public TaskRegistry Register<T>() where T : IAssistantTask, new()
    {
        var task = new T();
        _factories[task.Id] = () => new T();
        return this;
    }

    public IReadOnlyList<IAssistantTask> ListTasks()
    {
        return _factories.Values.Select(factory => factory()).ToList();
    }

    public IAssistantTask? Create(string id)
    {
        return _factories.TryGetValue(id, out var factory) ? factory() : null;
    }
}
