namespace MhxyAssistant.Core.Models;

public sealed record DetectionResult(
    int ClassId,
    string ClassName,
    double Confidence,
    RectI BBox,
    PointI Center);

public sealed record OcrResult(
    string Text,
    double Confidence,
    RectI BBox);

public sealed record TemplateMatchResult(
    string TemplateName,
    double Score,
    RectI BBox,
    PointI Center);

public enum GameState
{
    Idle,
    Walking,
    Battle,
    Dialog,
    Loading,
    Unknown,
}
