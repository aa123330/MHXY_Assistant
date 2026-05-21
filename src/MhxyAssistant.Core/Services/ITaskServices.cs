namespace MhxyAssistant.Core.Services;

public enum TaskRunState
{
    Idle,
    Running,
    Paused,
    Completed,
    Failed,
    Cancelled,
}

public interface IAssistantTask
{
    string Id { get; }
    string Name { get; }
    string Description { get; }
    Task RunAsync(TaskContext context, CancellationToken cancellationToken);
}

public sealed class TaskContext
{
    public required IWindowService Windows { get; init; }
    public required ICaptureService Capture { get; init; }
    public required IInputService Input { get; init; }
    public required ITemplateMatcher Templates { get; init; }
    public required IColorDetector Colors { get; init; }
    public required IOcrService Ocr { get; init; }
    public required IYoloDetector Yolo { get; init; }
    public required Action<string> Log { get; init; }
    public nint GameHwnd { get; set; }
}
