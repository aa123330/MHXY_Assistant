using System.Drawing.Imaging;
using System.IO.Compression;
using System.Text.Json;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Diagnostics;

public sealed class DiagnosticsExporter
{
    public string Export(TaskContext context, string outputRoot)
    {
        Directory.CreateDirectory(outputRoot);
        var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        var zipPath = Path.Combine(outputRoot, $"diagnostics_{timestamp}.zip");

        using var archive = ZipFile.Open(zipPath, ZipArchiveMode.Create);
        WriteJson(archive, "window.json", new
        {
            hwnd = $"0x{context.GameHwnd:X}",
            valid = context.GameHwnd != nint.Zero && context.Windows.IsWindowValid(context.GameHwnd),
            minimized = context.GameHwnd != nint.Zero && context.Windows.IsWindowMinimized(context.GameHwnd),
            client = context.GameHwnd != nint.Zero ? (MhxyAssistant.Core.Models.RectI?)context.Windows.GetClientRect(context.GameHwnd) : null,
            size = context.GameHwnd != nint.Zero ? (MhxyAssistant.Core.Models.SizeI?)context.Windows.GetClientSize(context.GameHwnd) : null,
        });

        WriteJson(archive, "environment.json", new
        {
            os = Environment.OSVersion.ToString(),
            runtime = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
            process64 = Environment.Is64BitProcess,
        });

        if (context.GameHwnd != nint.Zero)
        {
            try
            {
                using var image = context.Capture.CaptureClient(context.GameHwnd);
                WritePng(archive, "capture_foreground.png", image);
                WriteJson(archive, "capture_foreground_info.json", new { image.Width, image.Height, black_ratio = EstimateBlackRatio(image) });
            }
            catch (Exception ex)
            {
                WriteText(archive, "capture_foreground_error.txt", ex.ToString());
            }

            try
            {
                using var bg = context.Capture.CaptureClientBackground(context.GameHwnd);
                if (bg is not null)
                {
                    WritePng(archive, "capture_background.png", bg);
                    WriteJson(archive, "capture_background_info.json", new { bg.Width, bg.Height, black_ratio = EstimateBlackRatio(bg) });
                }
            }
            catch (Exception ex)
            {
                WriteText(archive, "capture_background_error.txt", ex.ToString());
            }
        }

        return zipPath;
    }

    private static void WriteJson(ZipArchive archive, string name, object value)
    {
        WriteText(archive, name, JsonSerializer.Serialize(value, new JsonSerializerOptions { WriteIndented = true }));
    }

    private static void WriteText(ZipArchive archive, string name, string text)
    {
        var entry = archive.CreateEntry(name);
        using var writer = new StreamWriter(entry.Open());
        writer.Write(text);
    }

    private static void WritePng(ZipArchive archive, string name, System.Drawing.Bitmap image)
    {
        var entry = archive.CreateEntry(name);
        using var stream = entry.Open();
        image.Save(stream, ImageFormat.Png);
    }

    private static double EstimateBlackRatio(System.Drawing.Bitmap image)
    {
        var black = 0;
        var total = 0;
        for (var y = 0; y < image.Height; y += 4)
        {
            for (var x = 0; x < image.Width; x += 4)
            {
                var c = image.GetPixel(x, y);
                if ((c.R + c.G + c.B) / 3 < 5)
                    black++;
                total++;
            }
        }
        return total == 0 ? 0 : (double)black / total;
    }
}
