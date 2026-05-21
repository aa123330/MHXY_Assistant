using System.Drawing;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Vision;

public sealed class ColorDetector : IColorDetector
{
    private static readonly HsvRange BattleRedLow = new(0, 100.0 / 255.0, 50.0 / 255.0, 10, 1, 1);
    private static readonly HsvRange BattleRedHigh = new(170, 100.0 / 255.0, 50.0 / 255.0, 180, 1, 1);

    public bool HasDialog(Bitmap source)
    {
        var region = new RectI(
            (int)(source.Width * 0.12),
            (int)(source.Height * 0.63),
            (int)(source.Width * 0.88),
            (int)(source.Height * 0.93));

        var bright = 0;
        var total = 0;
        foreach (var (_, _, c) in EnumeratePixels(source, region, step: 3))
        {
            if ((c.R + c.G + c.B) / 3 > 180)
                bright++;
            total++;
        }

        return total > 0 && (double)bright / total >= 0.30;
    }

    public bool HasBattleUi(Bitmap source)
    {
        var region = new RectI(
            (int)(source.Width * 0.06),
            (int)(source.Height * 0.67),
            (int)(source.Width * 0.94),
            (int)(source.Height * 0.83));

        return RatioColor(source, BattleRedLow, region, step: 3)
            + RatioColor(source, BattleRedHigh, region, step: 3) >= 0.03;
    }

    public bool HasRedText(Bitmap source, RectI? region = null, double threshold = 0.01)
    {
        var redLow = new HsvRange(0, 150.0 / 255.0, 100.0 / 255.0, 10, 1, 1);
        var redHigh = new HsvRange(170, 150.0 / 255.0, 100.0 / 255.0, 180, 1, 1);
        return RatioColor(source, redLow, region, step: 2) + RatioColor(source, redHigh, region, step: 2) >= threshold;
    }

    public int CountColor(Bitmap source, HsvRange range, RectI? region = null, int step = 1)
    {
        var count = 0;
        foreach (var (_, _, c) in EnumeratePixels(source, region, step))
        {
            if (IsInRange(c, range))
                count++;
        }
        return count;
    }

    public double RatioColor(Bitmap source, HsvRange range, RectI? region = null, int step = 1)
    {
        var total = 0;
        var count = 0;
        foreach (var (_, _, c) in EnumeratePixels(source, region, step))
        {
            total++;
            if (IsInRange(c, range))
                count++;
        }

        return total == 0 ? 0 : (double)count / total;
    }

    public PointI? FindRedTextCenter(Bitmap source, RectI? region = null)
    {
        long sx = 0;
        long sy = 0;
        var count = 0;
        foreach (var (x, y, c) in EnumeratePixels(source, region, step: 2))
        {
            if (c.R > c.G + 40 && c.R > c.B + 40 && c.R > 100)
            {
                sx += x;
                sy += y;
                count++;
            }
        }

        return count < 10 ? null : new PointI((int)(sx / count), (int)(sy / count));
    }

    private static bool IsInRange(Color color, HsvRange range)
    {
        var hsv = ToHsv(color);
        return hsv.H >= range.HMin && hsv.H <= range.HMax
            && hsv.S >= range.SMin && hsv.S <= range.SMax
            && hsv.V >= range.VMin && hsv.V <= range.VMax;
    }

    private static IEnumerable<(int X, int Y, Color Color)> EnumeratePixels(Bitmap source, RectI? region, int step)
    {
        step = Math.Max(1, step);
        var rect = region ?? new RectI(0, 0, source.Width, source.Height);
        var left = Math.Clamp(rect.Left, 0, source.Width);
        var right = Math.Clamp(rect.Right, 0, source.Width);
        var top = Math.Clamp(rect.Top, 0, source.Height);
        var bottom = Math.Clamp(rect.Bottom, 0, source.Height);

        for (var y = top; y < bottom; y += step)
        {
            for (var x = left; x < right; x += step)
                yield return (x, y, source.GetPixel(x, y));
        }
    }

    private static (double H, double S, double V) ToHsv(Color c)
    {
        var r = c.R / 255.0;
        var g = c.G / 255.0;
        var b = c.B / 255.0;
        var max = Math.Max(r, Math.Max(g, b));
        var min = Math.Min(r, Math.Min(g, b));
        var delta = max - min;
        var h = 0.0;

        if (delta > 0)
        {
            if (Math.Abs(max - r) < double.Epsilon)
                h = 60 * (((g - b) / delta) % 6);
            else if (Math.Abs(max - g) < double.Epsilon)
                h = 60 * (((b - r) / delta) + 2);
            else
                h = 60 * (((r - g) / delta) + 4);
        }

        if (h < 0)
            h += 360;

        return (h / 2, max == 0 ? 0 : delta / max, max);
    }
}
