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
    public Models.AppConfig Config { get; init; } = new();
    public required ICaptureService Capture { get; init; }
    public required IInputService Input { get; init; }
    public required ITemplateMatcher Templates { get; init; }
    public required IColorDetector Colors { get; init; }
    public required IMultiColorFeatureDetector ColorFeatures { get; init; }
    public required IOcrService Ocr { get; init; }
    public required IYoloDetector Yolo { get; init; }
    public IGameStateDetector? States { get; init; }
    public IBattleHandler? Battle { get; init; }
    public required Action<string> Log { get; init; }
    public nint GameHwnd { get; set; }
    public bool PreferBackgroundCapture { get; init; } = true;

    public bool EnsureGameWindow(bool activate = true)
    {
        if (GameHwnd == nint.Zero || !Windows.IsWindowValid(GameHwnd) || Windows.IsWindowMinimized(GameHwnd))
            return false;
        return !activate || Windows.ActivateWindow(GameHwnd);
    }

    public System.Drawing.Bitmap CaptureGameClient(bool? preferBackground = null)
    {
        if (GameHwnd == nint.Zero)
            throw new InvalidOperationException("Game window is not bound.");

        if (preferBackground ?? PreferBackgroundCapture)
        {
            var background = Capture.CaptureClientBackground(GameHwnd);
            if (background is not null)
                return background;
        }

        return Capture.CaptureClient(GameHwnd);
    }

    public Models.PointI ClientToScreen(Models.PointI clientPoint)
    {
        if (GameHwnd == nint.Zero)
            throw new InvalidOperationException("Game window is not bound.");
        return Windows.ClientToScreen(GameHwnd, clientPoint);
    }

    public bool ClickClient(Models.PointI clientPoint, string button = "left", int variance = 5)
    {
        if (!EnsureGameWindow())
            return false;

        var screenPoint = ClientToScreen(clientPoint);
        if (!Windows.VerifyClickWindow(GameHwnd, screenPoint))
        {
            Log($"[input] Refusing click outside bound client: {screenPoint.X},{screenPoint.Y}");
            return false;
        }

        return Input.Click(screenPoint, button, variance, bounds: Windows.GetClientRect(GameHwnd));
    }
}
