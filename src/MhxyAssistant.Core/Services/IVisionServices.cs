using System.Drawing;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.Core.Services;

public interface ITemplateMatcher
{
    TemplateMatchResult? MatchBest(Bitmap source, string templatePath, double threshold);
    IReadOnlyList<TemplateMatchResult> MatchAll(Bitmap source, string templatePath, double threshold);
}

public interface IColorDetector
{
    bool HasDialog(Bitmap source);
    bool HasBattleUi(Bitmap source);
    int CountColor(Bitmap source, HsvRange range, RectI? region = null, int step = 1);
    double RatioColor(Bitmap source, HsvRange range, RectI? region = null, int step = 1);
    bool HasRedText(Bitmap source, RectI? region = null, double threshold = 0.01);
    PointI? FindRedTextCenter(Bitmap source, RectI? region = null);
}

public readonly record struct HsvRange(double HMin, double SMin, double VMin, double HMax, double SMax, double VMax);

public interface IImageHasher
{
    string Compute(Bitmap source);
    int Hamming(string left, string right);
    bool Matches(Bitmap source, string hash, int threshold = 20);
    bool Compare(Bitmap left, Bitmap right, int threshold = 15);
}

public interface IScreenChangeDetector
{
    bool HasChanged(Bitmap previous, Bitmap current, double threshold = 0.03);
}

public interface IOcrService
{
    IReadOnlyList<OcrResult> Recognize(Bitmap source, RectI? region = null);
    OcrResult? FindText(Bitmap source, string text, RectI? region = null);
}

public interface IYoloDetector
{
    bool IsAvailable { get; }
    IReadOnlyList<DetectionResult> Detect(Bitmap source);
    DetectionResult? FindClass(Bitmap source, int classId);
    DetectionResult? FindClassName(Bitmap source, string className);
}
