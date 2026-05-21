using System.Drawing;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Vision;

public sealed class StateDetector : IGameStateDetector
{
    private readonly IColorDetector _colors;
    private readonly IImageHasher _hasher;
    private readonly ITemplateMatcher _templates;
    private readonly IYoloDetector _yolo;
    private readonly GameStateDetectorOptions _options;

    public StateDetector(
        IColorDetector colors,
        IImageHasher hasher,
        ITemplateMatcher templates,
        IYoloDetector yolo,
        GameStateDetectorOptions? options = null)
    {
        _colors = colors;
        _hasher = hasher;
        _templates = templates;
        _yolo = yolo;
        _options = options ?? GameStateDetectorOptions.Default();
    }

    public GameStateDetection Detect(Bitmap source)
    {
        ArgumentNullException.ThrowIfNull(source);

        var evidence = new List<GameStateEvidence>();

        var hashMatch = DetectByHash(source, evidence);
        if (hashMatch is not null)
            return hashMatch;

        var dialogMatch = DetectDialog(source, evidence);
        if (dialogMatch is not null)
            return dialogMatch;

        var battleMatch = DetectBattle(source, evidence);
        if (battleMatch is not null)
            return battleMatch;

        var templateMatch = DetectByTemplate(source, evidence);
        if (templateMatch is not null)
            return templateMatch;

        var yoloMatch = DetectByYolo(source, evidence);
        if (yoloMatch is not null)
            return yoloMatch;

        return GameStateDetection.Unknown(evidence);
    }

    private GameStateDetection? DetectByHash(Bitmap source, List<GameStateEvidence> evidence)
    {
        if (_options.HashRules.Count == 0)
            return null;

        var currentHash = _hasher.Compute(source);
        var matches = new List<(GameStateHashRule Rule, int Distance)>();
        foreach (var rule in _options.HashRules)
        {
            var distance = _hasher.Hamming(currentHash, rule.Hash);
            if (distance > rule.Threshold)
                continue;

            matches.Add((rule, distance));
            evidence.Add(new GameStateEvidence(
                rule.State,
                rule.Confidence,
                "hash",
                rule.Name ?? rule.Hash,
                $"distance={distance}, threshold={rule.Threshold}"));
        }

        var best = matches
            .OrderByDescending(m => m.Rule.Confidence)
            .ThenBy(m => m.Distance)
            .FirstOrDefault();

        return best.Rule is null
            ? null
            : BuildDetection(best.Rule.State, best.Rule.Confidence, "hash", "Screen hash matched.", evidence);
    }

    private GameStateDetection? DetectDialog(Bitmap source, List<GameStateEvidence> evidence)
    {
        if (!_colors.HasDialog(source))
            return null;

        evidence.Add(new GameStateEvidence(
            GameState.Dialog,
            _options.DialogConfidence,
            "color-dialog",
            "dialog-panel",
            "Bright lower-panel dialog heuristic matched."));

        return BuildDetection(GameState.Dialog, _options.DialogConfidence, "color-dialog", "Dialog UI color heuristic matched.", evidence);
    }

    private GameStateDetection? DetectBattle(Bitmap source, List<GameStateEvidence> evidence)
    {
        if (!_colors.HasBattleUi(source))
            return null;

        evidence.Add(new GameStateEvidence(
            GameState.Battle,
            _options.BattleConfidence,
            "color-battle",
            "battle-ui",
            "Battle UI color heuristic matched."));

        return BuildDetection(GameState.Battle, _options.BattleConfidence, "color-battle", "Battle UI color heuristic matched.", evidence);
    }

    private GameStateDetection? DetectByTemplate(Bitmap source, List<GameStateEvidence> evidence)
    {
        TemplateMatchResult? bestMatch = null;
        GameStateTemplateRule? bestRule = null;
        var bestConfidence = 0.0;

        foreach (var rule in _options.TemplateRules)
        {
            var match = _templates.MatchBest(source, rule.TemplatePath, rule.Threshold);
            if (match is null)
                continue;

            var confidence = Math.Clamp(match.Score * rule.Confidence, 0, 1);
            evidence.Add(new GameStateEvidence(
                rule.State,
                confidence,
                "template",
                rule.Name ?? match.TemplateName,
                $"score={match.Score:0.000}, threshold={rule.Threshold:0.000}"));

            if (confidence <= bestConfidence)
                continue;

            bestMatch = match;
            bestRule = rule;
            bestConfidence = confidence;
        }

        return bestRule is null || bestMatch is null
            ? null
            : BuildDetection(bestRule.State, bestConfidence, "template", $"Template '{bestRule.Name ?? bestMatch.TemplateName}' matched.", evidence);
    }

    private GameStateDetection? DetectByYolo(Bitmap source, List<GameStateEvidence> evidence)
    {
        if (!_options.UseYoloFallback || !_yolo.IsAvailable || _options.YoloRules.Count == 0)
            return null;

        var detections = _yolo.Detect(source);
        DetectionResult? bestDetection = null;
        GameStateYoloRule? bestRule = null;
        var bestConfidence = 0.0;

        foreach (var rule in _options.YoloRules)
        {
            var match = detections
                .Where(d => MatchesYoloRule(d, rule))
                .OrderByDescending(d => d.Confidence)
                .FirstOrDefault();

            if (match is null)
                continue;

            var confidence = Math.Clamp(match.Confidence * rule.Confidence, 0, 1);
            evidence.Add(new GameStateEvidence(
                rule.State,
                confidence,
                "yolo",
                rule.ClassName ?? rule.ClassId?.ToString() ?? match.ClassName,
                $"confidence={match.Confidence:0.000}, threshold={rule.Threshold:0.000}"));

            if (confidence <= bestConfidence)
                continue;

            bestDetection = match;
            bestRule = rule;
            bestConfidence = confidence;
        }

        return bestRule is null || bestDetection is null
            ? null
            : BuildDetection(bestRule.State, bestConfidence, "yolo", $"YOLO class '{bestDetection.ClassName}' matched.", evidence);
    }

    private static bool MatchesYoloRule(DetectionResult detection, GameStateYoloRule rule)
    {
        if (detection.Confidence < rule.Threshold)
            return false;

        if (rule.ClassId is not null && detection.ClassId == rule.ClassId.Value)
            return true;

        return rule.ClassName is not null
            && string.Equals(detection.ClassName, rule.ClassName, StringComparison.OrdinalIgnoreCase);
    }

    private static GameStateDetection BuildDetection(
        GameState state,
        double confidence,
        string method,
        string reason,
        IReadOnlyList<GameStateEvidence> evidence)
    {
        return new GameStateDetection(
            state,
            Math.Clamp(confidence, 0, 1),
            method,
            reason,
            evidence.ToArray());
    }
}
