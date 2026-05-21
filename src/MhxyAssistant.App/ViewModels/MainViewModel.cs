using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using MhxyAssistant.App.Windows;
using MhxyAssistant.Core.Diagnostics;
using MhxyAssistant.Core.Models;
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
    private readonly IMultiColorFeatureDetector _colorFeatures;
    private readonly IOcrService _ocr;
    private readonly IYoloDetector _yolo;
    private readonly ImageHasher _hasher = new();
    private readonly IGameStateDetector _states;
    private readonly BasicBattleHandler _battle = new();
    private readonly CaptureService _capture;
    private readonly DiagnosticsExporter _diagnostics = new();
    private readonly TaskRegistry _registry;
    private readonly AppConfig _config;
    private CancellationTokenSource? _taskCts;
    private nint _gameHwnd;
    private string _statusText = "Window not bound";
    private string _logText = "";

    public MainViewModel()
    {
        var loadedConfig = LoadConfig();
        _config = loadedConfig.Config;
        _ocr = CreateOcrService(_config);
        _yolo = CreateYoloDetector(_config, loadedConfig.BaseDirectory);
        _colorFeatures = CreateColorFeatureDetector(_config, loadedConfig.BaseDirectory);
        _states = new StateDetector(
            _colors,
            _hasher,
            _templates,
            _yolo,
            CreateStateDetectorOptions(_config, loadedConfig.BaseDirectory));
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
        YoloPreviewCommand = new RelayCommand(_ => OpenYoloTrainingWindow());
        YoloTrainingCommand = new RelayCommand(_ => OpenYoloTrainingWindow());
        AiSettingsCommand = new RelayCommand(_ => OpenAiSettingsWindow());
        CloudCommand = new RelayCommand(_ => OpenCloudWindow());
        ExportDiagnosticsCommand = new RelayCommand(_ => ExportDiagnostics());
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<TaskItem> Tasks { get; }
    public ICommand BindWindowCommand { get; }
    public ICommand RunTaskCommand { get; }
    public ICommand StopTaskCommand { get; }
    public ICommand CaptureCommand { get; }
    public ICommand YoloPreviewCommand { get; }
    public ICommand YoloTrainingCommand { get; }
    public ICommand AiSettingsCommand { get; }
    public ICommand CloudCommand { get; }
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
        _gameHwnd = FindConfiguredWindow();
        if (_gameHwnd == nint.Zero)
            _gameHwnd = _windows.FindWindowByRegex("梦幻西游 ONLINE.*");
        if (_gameHwnd == nint.Zero)
            _gameHwnd = _windows.FindWindowByTitle("梦幻西游");

        StatusText = _gameHwnd == nint.Zero ? "Game window not found" : $"Bound window: 0x{_gameHwnd:X}";
        Log(StatusText);
    }

    private async void RunTask(string? taskId)
    {
        if (string.IsNullOrWhiteSpace(taskId))
            return;

        var task = _registry.Create(taskId);
        if (task is null)
        {
            Log($"Unknown task: {taskId}");
            return;
        }

        if (_gameHwnd == nint.Zero)
            BindWindow();
        if (_gameHwnd == nint.Zero || !_windows.IsWindowValid(_gameHwnd) || _windows.IsWindowMinimized(_gameHwnd))
        {
            Log("[task] Game window is not bound or not available. Task will not start.");
            return;
        }

        _taskCts?.Cancel();
        _taskCts = new CancellationTokenSource();

        try
        {
            await task.RunAsync(CreateContext(), _taskCts.Token);
        }
        catch (OperationCanceledException)
        {
            Log("[task] Stopped");
        }
        catch (Exception ex)
        {
            Log($"[error] {ex.Message}");
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
            Log("[capture] Game window is not bound.");
            return;
        }

        try
        {
            var dir = Path.Combine(AppContext.BaseDirectory, "debug", "screenshots");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, $"capture_{DateTime.Now:yyyyMMdd_HHmmss}.png");
            using var image = _capture.CaptureClientBackground(_gameHwnd) ?? _capture.CaptureClient(_gameHwnd);
            image.Save(path, ImageFormat.Png);
            Log($"[capture] Saved: {path}");
        }
        catch (Exception ex)
        {
            Log($"[capture] Failed: {ex.Message}");
        }
    }

    private void ExportDiagnostics()
    {
        if (_gameHwnd == nint.Zero)
            BindWindow();

        try
        {
            var outputRoot = Path.Combine(AppContext.BaseDirectory, "debug", "diagnostics");
            var path = _diagnostics.Export(CreateContext(), outputRoot);
            Log($"[diagnostics] Exported: {path}");
        }
        catch (Exception ex)
        {
            Log($"[diagnostics] Failed: {ex.Message}");
        }
    }

    private void OpenAiSettingsWindow()
    {
        ShowDialog(new AiSettingsWindow(_config));
        Log("[ui] AI settings window opened.");
    }

    private void OpenYoloTrainingWindow()
    {
        ShowDialog(new YoloTrainingWindow(_config));
        Log("[ui] YOLO training window opened.");
    }

    private void OpenCloudWindow()
    {
        ShowDialog(new CloudWindow(_config));
        Log("[ui] Cloud window opened.");
    }

    private static void ShowDialog(System.Windows.Window window)
    {
        window.Owner = System.Windows.Application.Current.MainWindow;
        window.ShowDialog();
    }

    private TaskContext CreateContext()
    {
        return new TaskContext
        {
            Windows = _windows,
            Config = _config,
            Capture = _capture,
            Input = _input,
            Templates = _templates,
            Colors = _colors,
            ColorFeatures = _colorFeatures,
            Ocr = _ocr,
            Yolo = _yolo,
            States = _states,
            Battle = _battle,
            GameHwnd = _gameHwnd,
            PreferBackgroundCapture = _config.Capture.PreferBackground,
            Log = Log,
        };
    }

    private nint FindConfiguredWindow()
    {
        if (!string.IsNullOrWhiteSpace(_config.Game.WindowTitlePattern))
        {
            try
            {
                var byPattern = _windows.FindWindowByRegex(_config.Game.WindowTitlePattern);
                if (byPattern != nint.Zero)
                    return byPattern;
            }
            catch (ArgumentException ex)
            {
                Log($"[config] Invalid window regex: {ex.Message}");
            }
        }

        return string.IsNullOrWhiteSpace(_config.Game.WindowTitle)
            ? nint.Zero
            : _windows.FindWindowByTitle(_config.Game.WindowTitle);
    }

    private static LoadedConfig LoadConfig()
    {
        var loader = new AppConfigLoader();
        try
        {
            var configPath = loader.ResolveConfigPath();
            return new LoadedConfig(
                loader.Load(configPath),
                Path.GetDirectoryName(configPath) ?? AppContext.BaseDirectory);
        }
        catch
        {
            return new LoadedConfig(new AppConfig(), AppContext.BaseDirectory);
        }
    }

    private static IOcrService CreateOcrService(AppConfig config)
    {
        return WindowsOcrService.TryCreate(config.Ocr.Lang) is { } ocr ? ocr : new NullOcrService();
    }

    private static IMultiColorFeatureDetector CreateColorFeatureDetector(AppConfig config, string configBaseDirectory)
    {
        if (!config.VisionFeatures.Enabled || string.IsNullOrWhiteSpace(config.VisionFeatures.FeatureLibraryPath))
            return MultiColorFeatureDetector.Empty;

        var featurePath = ResolvePath(config.VisionFeatures.FeatureLibraryPath, configBaseDirectory);
        return MultiColorFeatureDetector.LoadFromFile(featurePath);
    }
    private static IYoloDetector CreateYoloDetector(AppConfig config, string configBaseDirectory)
    {
        if (!config.Yolo.Enabled || string.IsNullOrWhiteSpace(config.Yolo.ModelPath))
            return new NullYoloDetector();

        var modelPath = ResolvePath(config.Yolo.ModelPath, configBaseDirectory);
        if (!string.Equals(Path.GetExtension(modelPath), ".onnx", StringComparison.OrdinalIgnoreCase))
            return new NullYoloDetector();

        var classNames = config.Yolo.Classes
            .OrderBy(kv => kv.Key)
            .Select(kv => kv.Value)
            .ToArray();

        return new YoloOnnxDetector(
            modelPath,
            classNames,
            confidenceThreshold: (float)config.Yolo.ConfidenceThreshold);
    }

    private static GameStateDetectorOptions CreateStateDetectorOptions(AppConfig config, string configBaseDirectory)
    {
        var templateRoot = ResolveTemplateRoot(config.SceneDetection.TemplateDir, configBaseDirectory);
        var options = GameStateDetectorOptions.Default(templateRoot);
        return new GameStateDetectorOptions
        {
            HashRules = options.HashRules,
            TemplateRules = config.SceneDetection.Enabled
                ? options.TemplateRules.Select(rule => rule with
                {
                    Threshold = config.SceneDetection.MatchThreshold
                }).ToArray()
                : [],
            YoloRules = options.YoloRules,
            DialogConfidence = options.DialogConfidence,
            BattleConfidence = options.BattleConfidence,
            UseYoloFallback = config.Yolo.Enabled
        };
    }

    private static string ResolveTemplateRoot(string templateDir, string configBaseDirectory)
    {
        var resolved = ResolvePath(templateDir, configBaseDirectory);
        return string.Equals(Path.GetFileName(resolved), "scenes", StringComparison.OrdinalIgnoreCase)
            ? Path.GetDirectoryName(resolved) ?? resolved
            : resolved;
    }

    private static string ResolvePath(string path, string configBaseDirectory)
    {
        if (Path.IsPathRooted(path))
            return Path.GetFullPath(path);

        var configCandidate = Path.GetFullPath(Path.Combine(configBaseDirectory, path));
        if (File.Exists(configCandidate) || Directory.Exists(configCandidate))
            return configCandidate;

        var baseCandidate = Path.Combine(AppContext.BaseDirectory, path);
        if (File.Exists(baseCandidate) || Directory.Exists(baseCandidate))
            return Path.GetFullPath(baseCandidate);

        return configCandidate;
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

public sealed record LoadedConfig(AppConfig Config, string BaseDirectory);
