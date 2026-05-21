using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;
using OpenCvSharp;

namespace MhxyAssistant.Core.Vision;

public sealed class TemplateMatcher : ITemplateMatcher
{
    public TemplateMatchResult? MatchBest(Bitmap source, string templatePath, double threshold)
    {
        if (!File.Exists(templatePath))
            return null;

        using var src = BitmapToMat(source);
        using var tpl = Cv2.ImRead(templatePath, ImreadModes.Color);
        using var result = new Mat();
        Cv2.MatchTemplate(src, tpl, result, TemplateMatchModes.CCoeffNormed);
        Cv2.MinMaxLoc(result, out _, out var maxVal, out _, out var maxLoc);

        if (maxVal < threshold)
            return null;

        var rect = new RectI(maxLoc.X, maxLoc.Y, maxLoc.X + tpl.Width, maxLoc.Y + tpl.Height);
        return new TemplateMatchResult(Path.GetFileName(templatePath), maxVal, rect, rect.Center);
    }

    public IReadOnlyList<TemplateMatchResult> MatchAll(Bitmap source, string templatePath, double threshold)
    {
        if (!File.Exists(templatePath))
            return [];

        using var src = BitmapToMat(source);
        using var tpl = Cv2.ImRead(templatePath, ImreadModes.Color);
        if (tpl.Empty() || src.Width < tpl.Width || src.Height < tpl.Height)
            return [];

        using var result = new Mat();
        Cv2.MatchTemplate(src, tpl, result, TemplateMatchModes.CCoeffNormed);

        var matches = new List<TemplateMatchResult>();
        for (var y = 0; y < result.Rows; y++)
        {
            for (var x = 0; x < result.Cols; x++)
            {
                var score = result.At<float>(y, x);
                if (score < threshold)
                    continue;

                var rect = new RectI(x, y, x + tpl.Width, y + tpl.Height);
                matches.Add(new TemplateMatchResult(Path.GetFileName(templatePath), score, rect, rect.Center));
            }
        }

        return SuppressOverlaps(matches, 0.35)
            .OrderByDescending(m => m.Score)
            .ToArray();
    }

    private static IEnumerable<TemplateMatchResult> SuppressOverlaps(
        IEnumerable<TemplateMatchResult> matches,
        double iouThreshold)
    {
        var accepted = new List<TemplateMatchResult>();
        foreach (var match in matches.OrderByDescending(m => m.Score))
        {
            if (accepted.All(existing => IntersectionOverUnion(existing.BBox, match.BBox) < iouThreshold))
                accepted.Add(match);
        }

        return accepted;
    }

    private static double IntersectionOverUnion(RectI a, RectI b)
    {
        var left = Math.Max(a.Left, b.Left);
        var top = Math.Max(a.Top, b.Top);
        var right = Math.Min(a.Right, b.Right);
        var bottom = Math.Min(a.Bottom, b.Bottom);
        var intersection = Math.Max(0, right - left) * Math.Max(0, bottom - top);
        var areaA = Math.Max(0, a.Width) * Math.Max(0, a.Height);
        var areaB = Math.Max(0, b.Width) * Math.Max(0, b.Height);
        var union = areaA + areaB - intersection;
        return union == 0 ? 0 : (double)intersection / union;
    }

    private static Mat BitmapToMat(Bitmap bitmap)
    {
        using var clone = bitmap.Clone(
            new Rectangle(0, 0, bitmap.Width, bitmap.Height),
            PixelFormat.Format24bppRgb);
        var data = clone.LockBits(
            new Rectangle(0, 0, clone.Width, clone.Height),
            ImageLockMode.ReadOnly,
            PixelFormat.Format24bppRgb);
        try
        {
            var mat = new Mat(clone.Height, clone.Width, MatType.CV_8UC3);
            var rowBytes = clone.Width * 3;
            var buffer = new byte[rowBytes];
            for (var y = 0; y < clone.Height; y++)
            {
                Marshal.Copy(data.Scan0 + y * data.Stride, buffer, 0, rowBytes);
                Marshal.Copy(buffer, 0, IntPtr.Add(mat.Data, (int)(y * mat.Step())), rowBytes);
            }
            return mat;
        }
        finally
        {
            clone.UnlockBits(data);
        }
    }
}
