namespace MhxyAssistant.Core.Models;

public sealed class AppConfig
{
    public GameConfig Game { get; init; } = new();
    public CaptureConfig Capture { get; init; } = new();
    public OcrConfig Ocr { get; init; } = new();
    public YoloConfig Yolo { get; init; } = new();
    public BattleConfig Battle { get; init; } = new();
    public Dictionary<string, RectI> Regions { get; init; } = new();
}

public sealed class GameConfig
{
    public string WindowTitle { get; init; } = "梦幻西游";
    public string WindowTitlePattern { get; init; } = "梦幻西游 ONLINE.*";
    public SizeI WindowSize { get; init; } = new(800, 600);
    public string HotkeyEmergency { get; init; } = "ctrl+shift+f2";
    public string HotkeyToggle { get; init; } = "ctrl+shift+f1";
}

public sealed class CaptureConfig
{
    public bool PreferBackground { get; init; }
}

public sealed class OcrConfig
{
    public string Lang { get; init; } = "ch";
    public double ConfidenceThreshold { get; init; } = 0.7;
}

public sealed class YoloConfig
{
    public bool Enabled { get; init; }
    public string ModelPath { get; init; } = "models/yolo/best.onnx";
    public double ConfidenceThreshold { get; init; } = 0.5;
    public string Device { get; init; } = "cpu";
    public Dictionary<int, string> Classes { get; init; } = new();
}

public sealed class BattleConfig
{
    public string DefaultAction { get; init; } = "attack";
    public int MaxWrongClicks { get; init; } = 5;
    public bool SmartTargeting { get; init; } = true;
}
