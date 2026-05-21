using MhxyAssistant.Core.Models;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace MhxyAssistant.Core.Services;

public sealed class AppConfigLoader
{
    private const string ConfigFileName = "config.yaml";

    private readonly IDeserializer _deserializer = new DeserializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .IgnoreUnmatchedProperties()
        .Build();

    public AppConfig Load(string? configPath = null)
    {
        var resolvedPath = configPath ?? ResolveConfigPath();
        using var reader = File.OpenText(resolvedPath);
        var raw = _deserializer.Deserialize<RawAppConfig>(reader) ?? new RawAppConfig();

        return Map(raw);
    }

    public string ResolveConfigPath()
    {
        foreach (var candidate in EnumerateConfigCandidates())
        {
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        throw new FileNotFoundException(
            $"Could not find {ConfigFileName} in AppContext.BaseDirectory, the current directory, or their parent directories.",
            ConfigFileName);
    }

    private static IEnumerable<string> EnumerateConfigCandidates()
    {
        var roots = new[]
        {
            AppContext.BaseDirectory,
            Directory.GetCurrentDirectory()
        };

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var root in roots)
        {
            var directory = new DirectoryInfo(Path.GetFullPath(root));
            while (directory is not null)
            {
                var candidate = Path.Combine(directory.FullName, ConfigFileName);
                if (seen.Add(candidate))
                {
                    yield return candidate;
                }

                directory = directory.Parent;
            }
        }
    }

    private static AppConfig Map(RawAppConfig raw)
    {
        var defaults = new AppConfig();

        return new AppConfig
        {
            Ai = MapAi(raw.Ai, defaults.Ai),
            Game = MapGame(raw.Game, defaults.Game),
            Capture = MapCapture(raw.Capture, defaults.Capture),
            Ocr = MapOcr(raw.Ocr, defaults.Ocr),
            Yolo = MapYolo(raw.Yolo, defaults.Yolo),
            Battle = MapBattle(raw.Battle, defaults.Battle),
            CloudTrain = MapCloudTrain(raw.CloudTrain, defaults.CloudTrain),
            Pathfinding = MapPathfinding(raw.Pathfinding, defaults.Pathfinding),
            SceneDetection = MapSceneDetection(raw.SceneDetection, defaults.SceneDetection),
            VisionFeatures = MapVisionFeatures(raw.VisionFeatures, defaults.VisionFeatures),
            Tasks = MapTasks(raw.Tasks, defaults.Tasks),
            Regions = MapRegions(raw.Regions)
        };
    }

    private static AiConfig MapAi(RawAiConfig? raw, AiConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new AiConfig
        {
            Enabled = raw.Enabled ?? defaults.Enabled,
            Provider = raw.Provider ?? defaults.Provider,
            OpenAi = new OpenAiConfig
            {
                ApiKey = raw.OpenAi?.ApiKey ?? defaults.OpenAi.ApiKey,
                BaseUrl = raw.OpenAi?.BaseUrl ?? defaults.OpenAi.BaseUrl,
                Model = raw.OpenAi?.Model ?? defaults.OpenAi.Model
            },
            Anthropic = new AnthropicConfig
            {
                ApiKey = raw.Anthropic?.ApiKey ?? defaults.Anthropic.ApiKey,
                Model = raw.Anthropic?.Model ?? defaults.Anthropic.Model
            },
            Ollama = new OllamaConfig
            {
                BaseUrl = raw.Ollama?.BaseUrl ?? defaults.Ollama.BaseUrl,
                Model = raw.Ollama?.Model ?? defaults.Ollama.Model
            },
            Custom = new CustomAiConfig
            {
                ApiKey = raw.Custom?.ApiKey ?? defaults.Custom.ApiKey,
                Endpoint = raw.Custom?.Endpoint ?? defaults.Custom.Endpoint,
                Model = raw.Custom?.Model ?? defaults.Custom.Model
            }
        };
    }

    private static GameConfig MapGame(RawGameConfig? raw, GameConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new GameConfig
        {
            WindowTitle = raw.WindowTitle ?? defaults.WindowTitle,
            WindowTitlePattern = raw.WindowTitlePattern ?? defaults.WindowTitlePattern,
            WindowSize = ToSize(raw.WindowSize, defaults.WindowSize),
            HotkeyEmergency = raw.HotkeyEmergency ?? defaults.HotkeyEmergency,
            HotkeyToggle = raw.HotkeyToggle ?? defaults.HotkeyToggle,
            AutoMoveWindow = raw.AutoMoveWindow ?? defaults.AutoMoveWindow
        };
    }

    private static CaptureConfig MapCapture(RawCaptureConfig? raw, CaptureConfig defaults)
    {
        return new CaptureConfig
        {
            PreferBackground = raw?.PreferBackground ?? defaults.PreferBackground
        };
    }

    private static OcrConfig MapOcr(RawOcrConfig? raw, OcrConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new OcrConfig
        {
            Lang = raw.Lang ?? defaults.Lang,
            ConfidenceThreshold = raw.ConfidenceThreshold ?? defaults.ConfidenceThreshold,
            UseAngleCls = raw.UseAngleCls ?? defaults.UseAngleCls
        };
    }

    private static YoloConfig MapYolo(RawYoloConfig? raw, YoloConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new YoloConfig
        {
            Enabled = raw.Enabled ?? defaults.Enabled,
            ModelPath = raw.ModelPath ?? defaults.ModelPath,
            ConfidenceThreshold = raw.ConfidenceThreshold ?? raw.ConfThreshold ?? defaults.ConfidenceThreshold,
            Device = raw.Device ?? defaults.Device,
            Classes = raw.Classes ?? defaults.Classes
        };
    }

    private static BattleConfig MapBattle(RawBattleConfig? raw, BattleConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new BattleConfig
        {
            DefaultAction = raw.DefaultAction ?? defaults.DefaultAction,
            MaxWrongClicks = raw.MaxWrongClicks ?? defaults.MaxWrongClicks,
            SmartTargeting = raw.SmartTargeting ?? defaults.SmartTargeting,
            AutoBattleTimeout = raw.AutoBattleTimeout ?? defaults.AutoBattleTimeout,
            CheckInterval = raw.CheckInterval ?? defaults.CheckInterval,
            FallbackOnFail = raw.FallbackOnFail ?? defaults.FallbackOnFail,
            PopupDetection = raw.PopupDetection ?? defaults.PopupDetection,
            PopupTemplates = raw.PopupTemplates ?? defaults.PopupTemplates,
            SkillSlot = raw.SkillSlot ?? defaults.SkillSlot,
            TargetStrategy = raw.TargetStrategy ?? defaults.TargetStrategy,
            UseYoloVerify = raw.UseYoloVerify ?? defaults.UseYoloVerify
        };
    }

    private static CloudTrainConfig MapCloudTrain(RawCloudTrainConfig? raw, CloudTrainConfig defaults)
    {
        return new CloudTrainConfig
        {
            ServerUrl = raw?.ServerUrl ?? defaults.ServerUrl
        };
    }

    private static PathfindingConfig MapPathfinding(RawPathfindingConfig? raw, PathfindingConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new PathfindingConfig
        {
            ClickVariance = raw.ClickVariance ?? defaults.ClickVariance,
            GridSize = raw.GridSize ?? defaults.GridSize,
            MoveTimeout = raw.MoveTimeout ?? defaults.MoveTimeout,
            StuckThreshold = raw.StuckThreshold ?? defaults.StuckThreshold
        };
    }

    private static SceneDetectionConfig MapSceneDetection(RawSceneDetectionConfig? raw, SceneDetectionConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new SceneDetectionConfig
        {
            Enabled = raw.Enabled ?? defaults.Enabled,
            MatchThreshold = raw.MatchThreshold ?? defaults.MatchThreshold,
            TemplateDir = raw.TemplateDir ?? defaults.TemplateDir
        };
    }

    private static VisionFeatureConfig MapVisionFeatures(RawVisionFeatureConfig? raw, VisionFeatureConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new VisionFeatureConfig
        {
            Enabled = raw.Enabled ?? defaults.Enabled,
            FeatureLibraryPath = raw.FeatureLibraryPath ?? defaults.FeatureLibraryPath
        };
    }
    private static TasksConfig MapTasks(RawTasksConfig? raw, TasksConfig defaults)
    {
        if (raw is null)
        {
            return defaults;
        }

        return new TasksConfig
        {
            Shimen = new ShimenTaskConfig
            {
                AutoRecover = raw.Shimen?.AutoRecover ?? defaults.Shimen.AutoRecover,
                MasterTemplate = raw.Shimen?.MasterTemplate ?? defaults.Shimen.MasterTemplate,
                MaxRounds = raw.Shimen?.MaxRounds ?? defaults.Shimen.MaxRounds,
                TaskButtonTemplate = raw.Shimen?.TaskButtonTemplate ?? defaults.Shimen.TaskButtonTemplate
            },
            Zhuogui = new ZhuoguiTaskConfig
            {
                AutoFormation = raw.Zhuogui?.AutoFormation ?? defaults.Zhuogui.AutoFormation,
                MaxRounds = raw.Zhuogui?.MaxRounds ?? defaults.Zhuogui.MaxRounds
            }
        };
    }

    private static Dictionary<string, RectI> MapRegions(Dictionary<string, int[]>? rawRegions)
    {
        var regions = new Dictionary<string, RectI>(StringComparer.OrdinalIgnoreCase);
        if (rawRegions is null)
        {
            return regions;
        }

        foreach (var (name, coordinates) in rawRegions)
        {
            if (coordinates.Length >= 4)
            {
                regions[name] = new RectI(coordinates[0], coordinates[1], coordinates[2], coordinates[3]);
            }
        }

        return regions;
    }

    private static SizeI ToSize(int[]? values, SizeI fallback)
    {
        return values is { Length: >= 2 }
            ? new SizeI(values[0], values[1])
            : fallback;
    }

    private sealed class RawAppConfig
    {
        public RawAiConfig? Ai { get; set; }
        public RawGameConfig? Game { get; set; }
        public RawCaptureConfig? Capture { get; set; }
        public RawOcrConfig? Ocr { get; set; }
        public RawYoloConfig? Yolo { get; set; }
        public RawBattleConfig? Battle { get; set; }
        public RawCloudTrainConfig? CloudTrain { get; set; }
        public RawPathfindingConfig? Pathfinding { get; set; }
        public RawSceneDetectionConfig? SceneDetection { get; set; }
        public RawVisionFeatureConfig? VisionFeatures { get; set; }
        public RawTasksConfig? Tasks { get; set; }
        public Dictionary<string, int[]>? Regions { get; set; }
    }

    private sealed class RawAiConfig
    {
        public bool? Enabled { get; set; }
        public string? Provider { get; set; }

        [YamlMember(Alias = "openai")]
        public RawOpenAiConfig? OpenAi { get; set; }

        public RawAnthropicConfig? Anthropic { get; set; }
        public RawOllamaConfig? Ollama { get; set; }
        public RawCustomAiConfig? Custom { get; set; }
    }

    private sealed class RawOpenAiConfig
    {
        public string? ApiKey { get; set; }
        public string? BaseUrl { get; set; }
        public string? Model { get; set; }
    }

    private sealed class RawAnthropicConfig
    {
        public string? ApiKey { get; set; }
        public string? Model { get; set; }
    }

    private sealed class RawOllamaConfig
    {
        public string? BaseUrl { get; set; }
        public string? Model { get; set; }
    }

    private sealed class RawCustomAiConfig
    {
        public string? ApiKey { get; set; }
        public string? Endpoint { get; set; }
        public string? Model { get; set; }
    }

    private sealed class RawGameConfig
    {
        public string? WindowTitle { get; set; }
        public string? WindowTitlePattern { get; set; }
        public int[]? WindowSize { get; set; }
        public string? HotkeyEmergency { get; set; }
        public string? HotkeyToggle { get; set; }
        public bool? AutoMoveWindow { get; set; }
    }

    private sealed class RawCaptureConfig
    {
        public bool? PreferBackground { get; set; }
    }

    private sealed class RawOcrConfig
    {
        public string? Lang { get; set; }
        public double? ConfidenceThreshold { get; set; }
        public bool? UseAngleCls { get; set; }
    }

    private sealed class RawYoloConfig
    {
        public bool? Enabled { get; set; }
        public string? ModelPath { get; set; }
        public double? ConfidenceThreshold { get; set; }

        [YamlMember(Alias = "conf_threshold")]
        public double? ConfThreshold { get; set; }

        public string? Device { get; set; }
        public Dictionary<int, string>? Classes { get; set; }
    }

    private sealed class RawBattleConfig
    {
        public string? DefaultAction { get; set; }
        public int? MaxWrongClicks { get; set; }
        public bool? SmartTargeting { get; set; }
        public int? AutoBattleTimeout { get; set; }
        public double? CheckInterval { get; set; }
        public bool? FallbackOnFail { get; set; }
        public bool? PopupDetection { get; set; }
        public List<string>? PopupTemplates { get; set; }
        public int? SkillSlot { get; set; }
        public string? TargetStrategy { get; set; }
        public bool? UseYoloVerify { get; set; }
    }

    private sealed class RawCloudTrainConfig
    {
        public string? ServerUrl { get; set; }
    }

    private sealed class RawPathfindingConfig
    {
        public int? ClickVariance { get; set; }
        public int? GridSize { get; set; }
        public int? MoveTimeout { get; set; }
        public int? StuckThreshold { get; set; }
    }

    private sealed class RawSceneDetectionConfig
    {
        public bool? Enabled { get; set; }
        public double? MatchThreshold { get; set; }
        public string? TemplateDir { get; set; }
    }

    private sealed class RawVisionFeatureConfig
    {
        public bool? Enabled { get; set; }
        public string? FeatureLibraryPath { get; set; }
    }
    private sealed class RawTasksConfig
    {
        public RawShimenTaskConfig? Shimen { get; set; }
        public RawZhuoguiTaskConfig? Zhuogui { get; set; }
    }

    private sealed class RawShimenTaskConfig
    {
        public bool? AutoRecover { get; set; }
        public string? MasterTemplate { get; set; }
        public int? MaxRounds { get; set; }
        public string? TaskButtonTemplate { get; set; }
    }

    private sealed class RawZhuoguiTaskConfig
    {
        public bool? AutoFormation { get; set; }
        public int? MaxRounds { get; set; }
    }
}
