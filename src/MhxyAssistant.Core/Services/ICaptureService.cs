using System.Drawing;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.Core.Services;

public interface ICaptureService
{
    Bitmap CaptureClient(nint hwnd, RectI? clientRegion = null);
    Bitmap? CaptureClientBackground(nint hwnd);
}
