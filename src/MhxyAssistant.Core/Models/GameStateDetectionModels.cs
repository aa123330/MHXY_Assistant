namespace MhxyAssistant.Core.Models;

public sealed record GameStateDetection(
    GameState State,
    double Confidence,
    string Method,
    string Reason,
    IReadOnlyList<GameStateEvidence> Evidence)
{
    public static GameStateDetection Unknown(IReadOnlyList<GameStateEvidence>? evidence = null) =>
        new(GameState.Unknown, 0, "none", "No state rule matched.", evidence ?? []);
}

public sealed record GameStateEvidence(
    GameState State,
    double Confidence,
    string Method,
    string Name,
    string Detail);

public sealed class GameStateDetectorOptions
{
    public IReadOnlyList<GameStateHashRule> HashRules { get; init; } = [];
    public IReadOnlyList<GameStateTemplateRule> TemplateRules { get; init; } = [];
    public IReadOnlyList<GameStateYoloRule> YoloRules { get; init; } = [];
    public double DialogConfidence { get; init; } = 0.82;
    public double BattleConfidence { get; init; } = 0.86;
    public bool UseYoloFallback { get; init; } = true;

    public static GameStateDetectorOptions Default(string? templateRoot = null)
    {
        templateRoot ??= Path.Combine(AppContext.BaseDirectory, "data", "templates");
        return new GameStateDetectorOptions
        {
            TemplateRules =
            [
                new(GameState.Battle, Path.Combine(templateRoot, "scenes", "scene_fight.png"), 0.78, 0.9, "scene_fight"),
                new(GameState.Loading, Path.Combine(templateRoot, "scenes", "login.png"), 0.80, 0.82, "login"),
                new(GameState.Dialog, Path.Combine(templateRoot, "ui", "speak-task.png"), 0.76, 0.84, "speak-task"),
                new(GameState.Idle, Path.Combine(templateRoot, "ui", "taskTracking.png"), 0.76, 0.70, "task-tracking"),
            ],
            YoloRules =
            [
                new(GameState.Battle, "battle", null, 0.60, 0.80),
                new(GameState.Dialog, "dialog", null, 0.60, 0.78),
                new(GameState.Loading, "loading", null, 0.60, 0.72),
            ],
        };
    }
}

public sealed record GameStateHashRule(
    GameState State,
    string Hash,
    int Threshold = 20,
    double Confidence = 0.95,
    string? Name = null);

public sealed record GameStateTemplateRule(
    GameState State,
    string TemplatePath,
    double Threshold = 0.78,
    double Confidence = 0.85,
    string? Name = null);

public sealed record GameStateYoloRule(
    GameState State,
    string? ClassName = null,
    int? ClassId = null,
    double Threshold = 0.60,
    double Confidence = 0.75);
