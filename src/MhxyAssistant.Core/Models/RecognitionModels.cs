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

public sealed record ColorFeaturePoint(
    int OffsetX,
    int OffsetY,
    int Color);

public sealed record ColorFeatureRule(
    string Name,
    int BaseColor,
    IReadOnlyList<ColorFeaturePoint> Points,
    int Similarity,
    RectI SearchRegion);

public sealed record ColorFeatureMatch(
    string Name,
    double Score,
    PointI Point,
    RectI SearchRegion);

public enum GameState
{
    Idle,
    Walking,
    Battle,
    Dialog,
    Loading,
    Unknown,
}
