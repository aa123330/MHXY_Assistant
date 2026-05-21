using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Input;
using MhxyAssistant.App.Services;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.App.ViewModels;

public sealed class YoloTrainingViewModel : INotifyPropertyChanged
{
    private readonly UiSettingsStore _store = new();
    private readonly ExternalPythonScriptRunner _runner = new();
    private readonly UiSettings _settings;
    private CancellationTokenSource? _processCts;
    private string _pythonPath;
    private string _datasetPath;
    private string _modelPath;
    private string _scriptPath;
    private string _autoLabelScriptPath;
    private string _autoLabelImagesPath;
    private string _outputPath;
    private int _epochs;
    private int _batch;
    private int _imageSize;
    private string _device;
    private string _runName;
    private double _confidence;
    private bool _isRunning;
    private string _statusText = "Ready";
    private string _logText = "";

    public YoloTrainingViewModel(AppConfig config)
    {
        _settings = _store.Load();
        _pythonPath = string.IsNullOrWhiteSpace(_settings.YoloTraining.PythonPath) ? "python" : _settings.YoloTraining.PythonPath;
        _datasetPath = string.IsNullOrWhiteSpace(_settings.YoloTraining.DatasetPath) ? "tools/ml/data.yaml" : _settings.YoloTraining.DatasetPath;
        _modelPath = string.IsNullOrWhiteSpace(_settings.YoloTraining.ModelPath) ? config.Yolo.ModelPath : _settings.YoloTraining.ModelPath;
        _scriptPath = string.IsNullOrWhiteSpace(_settings.YoloTraining.ScriptPath) ? "tools/ml/train_yolo.py" : _settings.YoloTraining.ScriptPath;
        _autoLabelScriptPath = string.IsNullOrWhiteSpace(_settings.YoloTraining.AutoLabelScriptPath) ? "tools/ml/auto_label.py" : _settings.YoloTraining.AutoLabelScriptPath;
        _autoLabelImagesPath = string.IsNullOrWhiteSpace(_settings.YoloTraining.AutoLabelImagesPath) ? "debug/screenshots" : _settings.YoloTraining.AutoLabelImagesPath;
        _outputPath = string.IsNullOrWhiteSpace(_settings.YoloTraining.OutputPath) ? "tools/ml/runs" : _settings.YoloTraining.OutputPath;
        _epochs = _settings.YoloTraining.Epochs <= 0 ? 100 : _settings.YoloTraining.Epochs;
        _batch = _settings.YoloTraining.Batch <= 0 ? 8 : _settings.YoloTraining.Batch;
        _imageSize = _settings.YoloTraining.ImageSize <= 0 ? 640 : _settings.YoloTraining.ImageSize;
        _device = string.IsNullOrWhiteSpace(_settings.YoloTraining.Device) ? config.Yolo.Device : _settings.YoloTraining.Device;
        _runName = string.IsNullOrWhiteSpace(_settings.YoloTraining.RunName) ? "mhxy_train" : _settings.YoloTraining.RunName;
        _confidence = _settings.YoloTraining.Confidence <= 0 ? config.Yolo.ConfidenceThreshold : _settings.YoloTraining.Confidence;

        SaveCommand = new RelayCommand(_ => Save());
        StartTrainingCommand = new RelayCommand(async _ => await StartTrainingAsync(), _ => !IsRunning);
        AutoLabelCommand = new RelayCommand(async _ => await StartAutoLabelAsync(), _ => !IsRunning);
        StopCommand = new RelayCommand(_ => Stop(), _ => IsRunning);
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ICommand SaveCommand { get; }
    public ICommand StartTrainingCommand { get; }
    public ICommand AutoLabelCommand { get; }
    public ICommand StopCommand { get; }

    public string PythonPath
    {
        get => _pythonPath;
        set => SetField(ref _pythonPath, value);
    }

    public string DatasetPath
    {
        get => _datasetPath;
        set => SetField(ref _datasetPath, value);
    }

    public string ModelPath
    {
        get => _modelPath;
        set => SetField(ref _modelPath, value);
    }

    public string ScriptPath
    {
        get => _scriptPath;
        set => SetField(ref _scriptPath, value);
    }

    public string AutoLabelScriptPath
    {
        get => _autoLabelScriptPath;
        set => SetField(ref _autoLabelScriptPath, value);
    }

    public string AutoLabelImagesPath
    {
        get => _autoLabelImagesPath;
        set => SetField(ref _autoLabelImagesPath, value);
    }

    public string OutputPath
    {
        get => _outputPath;
        set => SetField(ref _outputPath, value);
    }

    public int Epochs
    {
        get => _epochs;
        set => SetField(ref _epochs, value);
    }

    public int Batch
    {
        get => _batch;
        set => SetField(ref _batch, value);
    }

    public int ImageSize
    {
        get => _imageSize;
        set => SetField(ref _imageSize, value);
    }

    public string Device
    {
        get => _device;
        set => SetField(ref _device, value);
    }

    public string RunName
    {
        get => _runName;
        set => SetField(ref _runName, value);
    }

    public double Confidence
    {
        get => _confidence;
        set => SetField(ref _confidence, value);
    }

    public bool IsRunning
    {
        get => _isRunning;
        private set
        {
            if (SetField(ref _isRunning, value))
            {
                (StartTrainingCommand as RelayCommand)?.RaiseCanExecuteChanged();
                (AutoLabelCommand as RelayCommand)?.RaiseCanExecuteChanged();
                (StopCommand as RelayCommand)?.RaiseCanExecuteChanged();
            }
        }
    }

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

    private void Save()
    {
        _settings.YoloTraining.PythonPath = PythonPath;
        _settings.YoloTraining.DatasetPath = DatasetPath;
        _settings.YoloTraining.ModelPath = ModelPath;
        _settings.YoloTraining.ScriptPath = ScriptPath;
        _settings.YoloTraining.AutoLabelScriptPath = AutoLabelScriptPath;
        _settings.YoloTraining.AutoLabelImagesPath = AutoLabelImagesPath;
        _settings.YoloTraining.OutputPath = OutputPath;
        _settings.YoloTraining.Epochs = Epochs;
        _settings.YoloTraining.Batch = Batch;
        _settings.YoloTraining.ImageSize = ImageSize;
        _settings.YoloTraining.Device = Device;
        _settings.YoloTraining.RunName = RunName;
        _settings.YoloTraining.Confidence = Confidence;
        var path = _store.Save(_settings);
        StatusText = $"Saved training settings: {path}";
    }

    private async Task StartTrainingAsync()
    {
        await RunScriptAsync(
            "Training",
            ScriptPath,
            new[]
            {
                "--base", ModelPath,
                "--epochs", Math.Max(1, Epochs).ToString(),
                "--batch", Math.Max(1, Batch).ToString(),
                "--imgsz", Math.Max(32, ImageSize).ToString(),
                "--device", string.IsNullOrWhiteSpace(Device) ? "cpu" : Device,
                "--name", string.IsNullOrWhiteSpace(RunName) ? "mhxy_train" : RunName,
            });
    }

    private async Task StartAutoLabelAsync()
    {
        await RunScriptAsync(
            "Auto-label",
            AutoLabelScriptPath,
            new[]
            {
                "--model", ModelPath,
                "--images", AutoLabelImagesPath,
                "--conf", Math.Clamp(Confidence, 0.01, 1.0).ToString("0.###"),
            });
    }

    private async Task RunScriptAsync(string name, string scriptPath, string[] arguments)
    {
        if (IsRunning)
            return;

        Save();
        LogText = "";
        _processCts = new CancellationTokenSource();
        IsRunning = true;
        StatusText = $"{name} running...";

        try
        {
            var exitCode = await _runner.RunAsync(
                PythonPath,
                scriptPath,
                arguments,
                PathResolver.FindWorkspaceRoot(),
                AppendLog,
                _processCts.Token);
            StatusText = exitCode == 0 ? $"{name} finished." : $"{name} exited with code {exitCode}.";
            AppendLog(StatusText);
        }
        catch (OperationCanceledException)
        {
            StatusText = $"{name} stopped.";
            AppendLog(StatusText);
        }
        catch (Exception ex)
        {
            StatusText = $"{name} failed: {ex.Message}";
            AppendLog(StatusText);
        }
        finally
        {
            IsRunning = false;
            _processCts.Dispose();
            _processCts = null;
        }
    }

    private void Stop()
    {
        _processCts?.Cancel();
    }

    private void AppendLog(string text)
    {
        var line = $"[{DateTime.Now:HH:mm:ss}] {text}{Environment.NewLine}";
        var dispatcher = Application.Current?.Dispatcher;
        if (dispatcher is null || dispatcher.CheckAccess())
            LogText += line;
        else
            dispatcher.Invoke(() => LogText += line);
    }

    private bool SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }
}
