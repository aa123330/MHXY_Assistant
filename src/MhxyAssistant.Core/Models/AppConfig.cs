namespace MhxyAssistant.Core.Models;

public sealed class AppConfig
{
    public AiConfig Ai { get; init; } = new();
    public GameConfig Game { get; init; } = new();
    public CaptureConfig Capture { get; init; } = new();
    public OcrConfig Ocr { get; init; } = new();
    public YoloConfig Yolo { get; init; } = new();
    public BattleConfig Battle { get; init; } = new();
    public CloudTrainConfig CloudTrain { get; init; } = new();
    public PathfindingConfig Pathfinding { get; init; } = new();
    public SceneDetectionConfig SceneDetection { get; init; } = new();
    public VisionFeatureConfig VisionFeatures { get; init; } = new();
    public TasksConfig Tasks { get; init; } = new();
    public Dictionary<string, RectI> Regions { get; init; } = new();
}

public sealed class AiConfig
{
    public bool Enabled { get; init; } = true;
    public string Provider { get; init; } = "openai";
    public OpenAiConfig OpenAi { get; init; } = new();
    public AnthropicConfig Anthropic { get; init; } = new();
    public OllamaConfig Ollama { get; init; } = new();
    public CustomAiConfig Custom { get; init; } = new();
}

public sealed class OpenAiConfig
{
    public string ApiKey { get; init; } = "${OPENAI_API_KEY}";
    public string BaseUrl { get; init; } = "https://api.openai.com/v1";
    public string Model { get; init; } = "gpt-5.4";
}

public sealed class AnthropicConfig
{
    public string ApiKey { get; init; } = "${ANTHROPIC_API_KEY}";
    public string Model { get; init; } = "claude-sonnet-4-6";
}

public sealed class OllamaConfig
{
    public string BaseUrl { get; init; } = "http://localhost:11434";
    public string Model { get; init; } = "llama3.2-vision";
}

public sealed class CustomAiConfig
{
    public string ApiKey { get; init; } = string.Empty;
    public string Endpoint { get; init; } = string.Empty;
    public string Model { get; init; } = string.Empty;
}

public sealed class GameConfig
{
    public string WindowTitle { get; init; } = "梦幻西游";
    public string WindowTitlePattern { get; init; } = "梦幻西游 ONLINE.*";
    public SizeI WindowSize { get; init; } = new(800, 600);
    public string HotkeyEmergency { get; init; } = "ctrl+shift+f2";
    public string HotkeyToggle { get; init; } = "ctrl+shift+f1";
    public bool AutoMoveWindow { get; init; } = true;
}

public sealed class CaptureConfig
{
    public bool PreferBackground { get; init; }
}

public sealed class OcrConfig
{
    public string Lang { get; init; } = "ch";
    public double ConfidenceThreshold { get; init; } = 0.7;
    public bool UseAngleCls { get; init; } = true;
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
    public int AutoBattleTimeout { get; init; } = 30;
    public double CheckInterval { get; init; } = 0.5;
    public bool FallbackOnFail { get; init; } = true;
    public bool PopupDetection { get; init; } = true;
    public IReadOnlyList<string> PopupTemplates { get; init; } = Array.Empty<string>();
    public int SkillSlot { get; init; } = 1;
    public string TargetStrategy { get; init; } = "auto";
    public bool UseYoloVerify { get; init; } = true;
}

public sealed class CloudTrainConfig
{
    public string ServerUrl { get; init; } = "http://localhost:9527";
}

public sealed class PathfindingConfig
{
    public int ClickVariance { get; init; } = 3;
    public int GridSize { get; init; } = 8;
    public int MoveTimeout { get; init; } = 60;
    public int StuckThreshold { get; init; } = 5;
}

public sealed class SceneDetectionConfig
{
    public bool Enabled { get; init; } = true;
    public double MatchThreshold { get; init; } = 0.7;
    public string TemplateDir { get; init; } = "data/templates/scenes";
}
public sealed class VisionFeatureConfig
{
    public bool Enabled { get; init; } = true;
    public string FeatureLibraryPath { get; init; } = "data/features/page.txt";
}

public sealed class TasksConfig
{
    public ShimenTaskConfig Shimen { get; init; } = new();
    public ZhuoguiTaskConfig Zhuogui { get; init; } = new();
    public EscortTaskConfig Escort { get; init; } = new();
    public PatrolTaskConfig Patrol { get; init; } = new();
}

public sealed class ShimenTaskConfig
{
    public bool AutoRecover { get; init; } = true;
    public string MasterTemplate { get; init; } = "master.png";
    public int MaxRounds { get; init; } = 20;
    public string TaskButtonTemplate { get; init; } = "speak-task.png";
}

public sealed class ZhuoguiTaskConfig
{
    public bool AutoFormation { get; init; } = true;
    public int MaxRounds { get; init; } = 10;
}

public sealed class EscortTaskConfig
{
    public int MaxRounds { get; init; } = 5;
}

public sealed class PatrolTaskConfig
{
    public int MaxCycles { get; init; } = 30;
}
