using System.Drawing;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Vision;

public sealed class NullOcrService : IOcrService
{
    public IReadOnlyList<OcrResult> Recognize(Bitmap source, RectI? region = null) => [];

    public OcrResult? FindText(Bitmap source, string text, RectI? region = null) => null;
}

public sealed class NullYoloDetector : IYoloDetector
{
    public bool IsAvailable => false;

    public IReadOnlyList<DetectionResult> Detect(Bitmap source) => [];

    public DetectionResult? FindClass(Bitmap source, int classId) => null;

    public DetectionResult? FindClassName(Bitmap source, string className) => null;
}
