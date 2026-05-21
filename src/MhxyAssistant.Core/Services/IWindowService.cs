using MhxyAssistant.Core.Models;

namespace MhxyAssistant.Core.Services;

public interface IWindowService
{
    nint FindWindowByTitle(string titlePart);
    nint FindWindowByRegex(string pattern);
    IReadOnlyList<WindowInfo> ListVisibleWindows();
    bool IsWindowValid(nint hwnd);
    bool IsWindowMinimized(nint hwnd);
    RectI GetWindowRect(nint hwnd);
    RectI GetClientRect(nint hwnd);
    SizeI GetClientSize(nint hwnd);
    PointI ClientToScreen(nint hwnd, PointI point);
    PointI ScreenToClient(nint hwnd, PointI point);
    bool IsPointInClient(nint hwnd, PointI screenPoint);
    bool ActivateWindow(nint hwnd);
    bool SetWindowSize(nint hwnd, int width, int height);
    bool VerifyClickWindow(nint hwnd, PointI screenPoint);
}

public sealed record WindowInfo(nint Hwnd, string Title, string ClassName);
