using System.Drawing;
using System.Globalization;
using System.Text.RegularExpressions;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Vision;

public sealed class MultiColorFeatureDetector : IMultiColorFeatureDetector
{
    private static readonly Regex FullRulePattern = new(
        @"^\s*(?<name>[\w\u4e00-\u9fa5.\-]+)\s*=\s*\{\s*(?<body>.*)\}\s*;?\s*$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private static readonly Regex BodyPattern = new(
        @"^\s*(?<base>0x[0-9a-fA-F]+|\d+)\s*,\s*""(?<offsets>[^""}]*)""\s*,\s*(?<similarity>\d+)\s*,\s*(?<x1>-?\d+)\s*,\s*(?<y1>-?\d+)\s*,\s*(?<x2>-?\d+)\s*,\s*(?<y2>-?\d+)\s*$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private readonly Dictionary<string, ColorFeatureRule> _rules = new(StringComparer.OrdinalIgnoreCase);

    public MultiColorFeatureDetector()
    {
    }

    public MultiColorFeatureDetector(IEnumerable<ColorFeatureRule> rules)
    {
        foreach (var rule in rules)
            _rules[rule.Name] = rule;
    }

    public static MultiColorFeatureDetector Empty { get; } = new();

    public static MultiColorFeatureDetector LoadFromFile(string path)
    {
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            return Empty;

        var detector = new MultiColorFeatureDetector();
        foreach (var line in File.ReadLines(path))
        {
            if (detector.TryParseLine(line, out var rule))
                detector._rules[rule.Name] = rule;
        }

        return detector;
    }

    public bool TryParseRule(string name, string definition, out ColorFeatureRule rule)
    {
        rule = null!;
        var match = BodyPattern.Match(definition.Trim().Trim('{', '}', ';'));
        if (!match.Success)
            return false;

        rule = BuildRule(name, match);
        return true;
    }

    public ColorFeatureMatch? Match(Bitmap source, ColorFeatureRule rule)
    {
        var threshold = SimilarityToColorDistance(rule.Similarity);
        var region = ClampRegion(rule.SearchRegion, source.Width, source.Height, rule.Points);
        if (region.Width <= 0 || region.Height <= 0)
            return null;

        var baseColor = FromRgbInt(rule.BaseColor);
        for (var y = region.Top; y < region.Bottom; y++)
        {
            for (var x = region.Left; x < region.Right; x++)
            {
                if (ColorDistance(source.GetPixel(x, y), baseColor) > threshold)
                    continue;

                var score = ScorePoints(source, x, y, rule, threshold);
                if (score >= 0)
                    return new ColorFeatureMatch(rule.Name, score, new PointI(x, y), rule.SearchRegion);
            }
        }

        return null;
    }

    public ColorFeatureMatch? Find(Bitmap source, string featureName)
    {
        return _rules.TryGetValue(featureName, out var rule) ? Match(source, rule) : null;
    }

    public IReadOnlyDictionary<string, ColorFeatureRule> Rules => _rules;

    private bool TryParseLine(string line, out ColorFeatureRule rule)
    {
        rule = null!;
        var trimmed = line.Trim();
        if (trimmed.Length == 0 || trimmed.StartsWith('#') || trimmed.StartsWith("//"))
            return false;

        var full = FullRulePattern.Match(trimmed);
        if (!full.Success)
            return false;

        return TryParseRule(full.Groups["name"].Value, full.Groups["body"].Value, out rule);
    }

    private static ColorFeatureRule BuildRule(string name, Match match)
    {
        var region = new RectI(
            ParseInt(match.Groups["x1"].Value),
            ParseInt(match.Groups["y1"].Value),
            ParseInt(match.Groups["x2"].Value) + 1,
            ParseInt(match.Groups["y2"].Value) + 1);

        return new ColorFeatureRule(
            name,
            ParseColor(match.Groups["base"].Value),
            ParsePoints(match.Groups["offsets"].Value),
            Math.Clamp(ParseInt(match.Groups["similarity"].Value), 1, 100),
            region);
    }

    private static IReadOnlyList<ColorFeaturePoint> ParsePoints(string offsets)
    {
        if (string.IsNullOrWhiteSpace(offsets))
            return Array.Empty<ColorFeaturePoint>();

        return offsets.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(part => part.Split('|', StringSplitOptions.TrimEntries))
            .Where(parts => parts.Length == 3)
            .Select(parts => new ColorFeaturePoint(ParseInt(parts[0]), ParseInt(parts[1]), ParseColor(parts[2])))
            .ToArray();
    }

    private static RectI ClampRegion(RectI region, int width, int height, IReadOnlyList<ColorFeaturePoint> points)
    {
        var minDx = points.Count == 0 ? 0 : Math.Min(0, points.Min(p => p.OffsetX));
        var maxDx = points.Count == 0 ? 0 : Math.Max(0, points.Max(p => p.OffsetX));
        var minDy = points.Count == 0 ? 0 : Math.Min(0, points.Min(p => p.OffsetY));
        var maxDy = points.Count == 0 ? 0 : Math.Max(0, points.Max(p => p.OffsetY));

        return new RectI(
            Math.Clamp(region.Left - minDx, 0, width),
            Math.Clamp(region.Top - minDy, 0, height),
            Math.Clamp(region.Right - maxDx, 0, width),
            Math.Clamp(region.Bottom - maxDy, 0, height));
    }

    private static double ScorePoints(Bitmap source, int x, int y, ColorFeatureRule rule, int threshold)
    {
        if (rule.Points.Count == 0)
            return 1.0;

        var total = 0.0;
        foreach (var point in rule.Points)
        {
            var nx = x + point.OffsetX;
            var ny = y + point.OffsetY;
            if (nx < 0 || ny < 0 || nx >= source.Width || ny >= source.Height)
                return -1;

            var distance = ColorDistance(source.GetPixel(nx, ny), FromRgbInt(point.Color));
            if (distance > threshold)
                return -1;

            total += 1.0 - distance / 765.0;
        }

        return total / rule.Points.Count;
    }

    private static int SimilarityToColorDistance(int similarity)
    {
        return (int)Math.Round((100 - Math.Clamp(similarity, 1, 100)) / 100.0 * 765);
    }

    private static int ColorDistance(Color left, Color right)
    {
        return Math.Abs(left.R - right.R) + Math.Abs(left.G - right.G) + Math.Abs(left.B - right.B);
    }

    private static Color FromRgbInt(int value)
    {
        return Color.FromArgb((value >> 16) & 0xff, (value >> 8) & 0xff, value & 0xff);
    }

    private static int ParseColor(string value)
    {
        return value.StartsWith("0x", StringComparison.OrdinalIgnoreCase)
            ? int.Parse(value[2..], NumberStyles.HexNumber, CultureInfo.InvariantCulture)
            : int.Parse(value, CultureInfo.InvariantCulture);
    }

    private static int ParseInt(string value)
    {
        return int.Parse(value, CultureInfo.InvariantCulture);
    }
}