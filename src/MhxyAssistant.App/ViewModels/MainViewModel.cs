using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using MhxyAssistant.Core.Diagnostics;
using MhxyAssistant.Core.Services;
using MhxyAssistant.Core.Tasks;
using MhxyAssistant.Core.Vision;
using MhxyAssistant.Core.Windows;

namespace MhxyAssistant.App.ViewModels;

public sealed class MainViewModel : INotifyPropertyChanged
{
    private readonly WindowService _windows = new();
    private readonly InputService _input = new();
    private readonly TemplateMatcher _templates = new();
    private readonly ColorDetector _colors = new();
    private readonly NullOcrService _ocr = new();
    private readonly NullYoloDetector _yolo = new();
    private readonly CaptureService _capture;
    private readonly DiagnosticsExporter _diagnostics = new();
    private readonly TaskRegistry _registry;
    private CancellationTokenSource? _taskCts;
    private nint _gameHwnd;
    private string _statusText = "未绑定窗口";
    private string _logText = "";

    public MainViewModel()
    {
        _capture = new CaptureService(_windows);
        _registry = new TaskRegistry()
            .Register<ShimenTask>()
            .Register<ZhuoguiTask>()
            .Register<PlotTask>()
            .Register<PatrolTask>()
            .Register<EscortTask>();

        Tasks = new ObservableCollection<TaskItem>(_registry.ListTasks().Select(t => new TaskItem(t.Id, t.Name, t.Description)));
        BindWindowCommand = new RelayCommand(_ => BindWindow());
        RunTaskCommand = new RelayCommand(p => RunTask(p?.ToString()));
        StopTaskCommand = new RelayCommand(_ => StopTask());
        CaptureCommand = new RelayCommand(_ => CaptureScreenshot());
        YoloPreviewCommand = new RelayCommand(_ => Log("[迁移占位] YOLO 预览入口已保留，运行时将改用 ONNX。"));
        AiSettingsCommand = new RelayCommand(_ => Log("[迁移占位] AI 设置入口已保留。"));
        ExportDiagnosticsCommand = new RelayCommand(_ => ExportDiagnostics());
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<TaskItem> Tasks { get; }
    public ICommand BindWindowCommand { get; }
    public ICommand RunTaskCommand { get; }
    public ICommand StopTaskCommand { get; }
    public ICommand CaptureCommand { get; }
    public ICommand YoloPreviewCommand { get; }
    public ICommand AiSettingsCommand { get; }
    public ICommand ExportDiagnosticsCommand { get; }

    public string StatusText
    {
        get => _statusText;
        private set => SetField(ref _statusText, value);
    }

    public string LogText
    {
        get => _logText;
        private set => SetField(ref _logText, value);
    }

    private void BindWindow()
    {
        _gameHwnd = _windows.FindWindowByRegex("梦幻西游 ONLINE.*");
        if (_gameHwnd == nint.Zero)
            _gameHwnd = _windows.FindWindowByTitle("梦幻西游");

        StatusText = _gameHwnd == nint.Zero ? "未找到梦幻西游窗口" : $"已绑定窗口: 0x{_gameHwnd:X}";
        Log(StatusText);
    }

    private async void RunTask(string? taskId)
    {
        if (string.IsNullOrWhiteSpace(taskId))
            return;

        var task = _registry.Create(taskId);
        if (task is null)
        {
            Log($"未知任务: {taskId}");
            return;
        }

        if (_gameHwnd == nint.Zero)
            BindWindow();

        _taskCts?.Cancel();
        _taskCts = new CancellationTokenSource();
        var context = new TaskContext
        {
            Windows = _windows,
            Capture = _capture,
            Input = _input,
            Templates = _templates,
            Colors = _colors,
            Ocr = _ocr,
            Yolo = _yolo,
            GameHwnd = _gameHwnd,
            Log = Log,
        };

        try
        {
            await task.RunAsync(context, _taskCts.Token);
        }
        catch (OperationCanceledException)
        {
            Log("[任务] 已停止");
        }
        catch (Exception ex)
        {
            Log($"[错误] {ex.Message}");
        }
    }

    private void StopTask()
    {
        _taskCts?.Cancel();
    }

    private void CaptureScreenshot()
    {
        if (_gameHwnd == nint.Zero)
            BindWindow();
        if (_gameHwnd == nint.Zero)
        {
            Log("[截图] 未绑定窗口");
            return;
        }

        try
        {
            var dir = Path.Combine(AppContext.BaseDirectory, "debug", "screenshots");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, $"capture_{DateTime.Now:yyyyMMdd_HHmmss}.png");
            using var image = _capture.CaptureClient(_gameHwnd);
            image.Save(path, ImageFormat.Png);
            Log($"[截图] 已保存: {path}");
        }
        catch (Exception ex)
        {
            Log($"[截图] 失败: {ex.Message}");
        }
    }

    private void ExportDiagnostics()
    {
        if (_gameHwnd == nint.Zero)
            BindWindow();

        try
        {
            var context = CreateContext();
            var outputRoot = Path.Combine(AppContext.BaseDirectory, "debug", "diagnostics");
            var path = _diagnostics.Export(context, outputRoot);
            Log($"[诊断] 已导出: {path}");
        }
        catch (Exception ex)
        {
            Log($"[诊断] 失败: {ex.Message}");
        }
    }

    private TaskContext CreateContext()
    {
        return new TaskContext
        {
            Windows = _windows,
            Capture = _capture,
            Input = _input,
            Templates = _templates,
            Colors = _colors,
            Ocr = _ocr,
            Yolo = _yolo,
            GameHwnd = _gameHwnd,
            Log = Log,
        };
    }

    private void Log(string text)
    {
        LogText += $"[{DateTime.Now:HH:mm:ss}] {text}{Environment.NewLine}";
    }

    private void SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}

public sealed record TaskItem(string Id, string Name, string Description);
