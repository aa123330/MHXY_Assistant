using System.IO;
using System.Text.Json;

namespace MhxyAssistant.App.ViewModels;

public sealed class UiSettingsStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
    };

    public UiSettings Load()
    {
        var path = GetSettingsPath();
        if (!File.Exists(path))
            return new UiSettings();

        try
        {
            var json = File.ReadAllText(path);
            return JsonSerializer.Deserialize<UiSettings>(json, JsonOptions) ?? new UiSettings();
        }
        catch
        {
            return new UiSettings();
        }
    }

    public string Save(UiSettings settings)
    {
        var path = GetSettingsPath();
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, JsonSerializer.Serialize(settings, JsonOptions));
        return path;
    }

    private static string GetSettingsPath()
    {
        return Path.Combine(AppContext.BaseDirectory, ".appdata", "wpf-ui-settings.json");
    }
}

public sealed class UiSettings
{
    public AiUiSettings Ai { get; set; } = new();
    public YoloTrainingUiSettings YoloTraining { get; set; } = new();
    public CloudUiSettings Cloud { get; set; } = new();
}

public sealed class AiUiSettings
{
    public bool Enabled { get; set; } = true;
    public string Provider { get; set; } = "openai";
    public string BaseUrl { get; set; } = "https://api.openai.com/v1";
    public string Model { get; set; } = "gpt-5.4";
    public string ApiKeyPlaceholder { get; set; } = "${OPENAI_API_KEY}";
}

public sealed class YoloTrainingUiSettings
{
    public string PythonPath { get; set; } = "python";
    public string DatasetPath { get; set; } = "tools/ml/data.yaml";
    public string ModelPath { get; set; } = "yolov8n.pt";
    public string ScriptPath { get; set; } = "tools/ml/train_yolo.py";
    public string AutoLabelScriptPath { get; set; } = "tools/ml/auto_label.py";
    public string AutoLabelImagesPath { get; set; } = "debug/screenshots";
    public string OutputPath { get; set; } = "tools/ml/runs";
    public int Epochs { get; set; } = 100;
    public int Batch { get; set; } = 8;
    public int ImageSize { get; set; } = 640;
    public string Device { get; set; } = "cpu";
    public string RunName { get; set; } = "mhxy_train";
    public double Confidence { get; set; } = 0.5;
}

public sealed class CloudUiSettings
{
    public string ServerUrl { get; set; } = "http://localhost:9527";
    public string UploadPath { get; set; } = "tools/ml/data.yaml";
    public string DownloadDirectory { get; set; } = "downloads";
}

