using System.Drawing;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Windows;

public sealed class CaptureService(IWindowService windows) : ICaptureService
{
    public Bitmap CaptureClient(nint hwnd, RectI? clientRegion = null)
    {
        var client = windows.GetClientRect(hwnd);
        var region = clientRegion is null
            ? client
            : new RectI(client.Left + clientRegion.Value.Left, client.Top + clientRegion.Value.Top, client.Left + clientRegion.Value.Right, client.Top + clientRegion.Value.Bottom);

        if (region.Width <= 0 || region.Height <= 0)
            throw new ArgumentOutOfRangeException(nameof(clientRegion), "Capture region must be positive.");

        var bitmap = new Bitmap(region.Width, region.Height);
        using var g = Graphics.FromImage(bitmap);
        g.CopyFromScreen(region.Left, region.Top, 0, 0, new Size(region.Width, region.Height));
        return bitmap;
    }

    public Bitmap? CaptureClientBackground(nint hwnd)
    {
        var size = windows.GetClientSize(hwnd);
        if (size.Width <= 0 || size.Height <= 0)
            return null;

        var bitmap = new Bitmap(size.Width, size.Height);
        using var g = Graphics.FromImage(bitmap);
        var hdc = g.GetHdc();
        try
        {
            return NativeMethods.PrintWindow(hwnd, hdc, 0x00000001 | 0x00000002) ? bitmap : null;
        }
        finally
        {
            g.ReleaseHdc(hdc);
        }
    }
}
