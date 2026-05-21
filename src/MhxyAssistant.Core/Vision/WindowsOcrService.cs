using System.Drawing;
using System.Drawing.Imaging;
using Windows.Globalization;
using Windows.Graphics.Imaging;
using Windows.Media.Ocr;
using Windows.Storage.Streams;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;
using CoreOcrResult = MhxyAssistant.Core.Models.OcrResult;

namespace MhxyAssistant.Core.Vision;

public sealed class WindowsOcrService : IOcrService
{
    private static readonly string[] PreferredLanguages = ["zh-Hans", "zh-CN", "en-US"];

    private readonly OcrEngine _engine;

    private WindowsOcrService(OcrEngine engine)
    {
        _engine = engine;
    }

    public static WindowsOcrService? TryCreate(string? preferredLanguage = null)
    {
        if (!OperatingSystem.IsWindowsVersionAtLeast(10))
            return null;

        foreach (var languageTag in GetLanguageCandidates(preferredLanguage))
        {
            var engine = TryCreateEngine(languageTag);
            if (engine is not null)
                return new WindowsOcrService(engine);
        }

        var profileEngine = OcrEngine.TryCreateFromUserProfileLanguages();
        return profileEngine is null ? null : new WindowsOcrService(profileEngine);
    }

    public IReadOnlyList<CoreOcrResult> Recognize(Bitmap source, RectI? region = null)
    {
        ArgumentNullException.ThrowIfNull(source);

        var cropRegion = ClampRegion(region, source.Width, source.Height);
        if (cropRegion.Width <= 0 || cropRegion.Height <= 0)
            return [];

        try
        {
            using var cropped = Crop(source, cropRegion);
            using var softwareBitmap = ToSoftwareBitmapAsync(cropped).GetAwaiter().GetResult();
            var ocr = _engine.RecognizeAsync(softwareBitmap).AsTask().GetAwaiter().GetResult();

            return ocr.Lines
                .Select(line => ToOcrResult(line, cropRegion.Left, cropRegion.Top))
                .Where(result => result is not null)
                .Select(result => result!)
                .ToArray();
        }
        catch
        {
            return [];
        }
    }

    public CoreOcrResult? FindText(Bitmap source, string text, RectI? region = null)
    {
        if (string.IsNullOrWhiteSpace(text))
            return null;

        return Recognize(source, region)
            .FirstOrDefault(result => result.Text.Contains(text, StringComparison.OrdinalIgnoreCase));
    }

    private static IEnumerable<string> GetLanguageCandidates(string? preferredLanguage)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var languageTag in ExpandLanguage(preferredLanguage).Concat(PreferredLanguages))
        {
            if (seen.Add(languageTag))
                yield return languageTag;
        }
    }

    private static IEnumerable<string> ExpandLanguage(string? language)
    {
        if (string.IsNullOrWhiteSpace(language))
            yield break;

        var normalized = language.Trim();
        yield return normalized;

        if (string.Equals(normalized, "ch", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(normalized, "zh", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(normalized, "cn", StringComparison.OrdinalIgnoreCase))
        {
            yield return "zh-Hans";
            yield return "zh-CN";
        }
    }

    private static OcrEngine? TryCreateEngine(string languageTag)
    {
        try
        {
            return OcrEngine.TryCreateFromLanguage(new Language(languageTag));
        }
        catch
        {
            return null;
        }
    }

    private static RectI ClampRegion(RectI? region, int width, int height)
    {
        if (region is not { } value)
            return new RectI(0, 0, width, height);

        var left = Math.Clamp(value.Left, 0, width);
        var top = Math.Clamp(value.Top, 0, height);
        var right = Math.Clamp(value.Right, left, width);
        var bottom = Math.Clamp(value.Bottom, top, height);
        return new RectI(left, top, right, bottom);
    }

    private static Bitmap Crop(Bitmap source, RectI region)
    {
        var bitmap = new Bitmap(region.Width, region.Height, PixelFormat.Format32bppArgb);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.DrawImage(
            source,
            new Rectangle(0, 0, region.Width, region.Height),
            new Rectangle(region.Left, region.Top, region.Width, region.Height),
            GraphicsUnit.Pixel);
        return bitmap;
    }

    private static async Task<SoftwareBitmap> ToSoftwareBitmapAsync(Bitmap bitmap)
    {
        using var stream = new InMemoryRandomAccessStream();
        await WritePngAsync(bitmap, stream).ConfigureAwait(false);
        stream.Seek(0);

        var decoder = await BitmapDecoder.CreateAsync(stream).AsTask().ConfigureAwait(false);
        return await decoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied)
            .AsTask()
            .ConfigureAwait(false);
    }

    private static async Task WritePngAsync(Bitmap bitmap, IRandomAccessStream stream)
    {
        using var memory = new MemoryStream();
        bitmap.Save(memory, ImageFormat.Png);

        var writer = new DataWriter(stream);
        writer.WriteBytes(memory.ToArray());
        await writer.StoreAsync().AsTask().ConfigureAwait(false);
        await writer.FlushAsync().AsTask().ConfigureAwait(false);
        writer.DetachStream();
    }

    private static CoreOcrResult? ToOcrResult(OcrLine line, int offsetX, int offsetY)
    {
        var words = line.Words;
        if (words.Count == 0)
            return null;

        var left = words.Min(word => word.BoundingRect.X);
        var top = words.Min(word => word.BoundingRect.Y);
        var right = words.Max(word => word.BoundingRect.X + word.BoundingRect.Width);
        var bottom = words.Max(word => word.BoundingRect.Y + word.BoundingRect.Height);

        return new CoreOcrResult(
            line.Text,
            1.0,
            new RectI(
                offsetX + (int)Math.Floor(left),
                offsetY + (int)Math.Floor(top),
                offsetX + (int)Math.Ceiling(right),
                offsetY + (int)Math.Ceiling(bottom)));
    }
}
