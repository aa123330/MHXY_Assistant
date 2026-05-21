using System.Text;
using System.Text.RegularExpressions;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Windows;

public sealed class WindowService : IWindowService
{
    public nint FindWindowByTitle(string titlePart)
    {
        foreach (var window in ListVisibleWindows())
        {
            if (window.Title.Contains(titlePart, StringComparison.OrdinalIgnoreCase))
                return window.Hwnd;
        }
        return nint.Zero;
    }

    public nint FindWindowByRegex(string pattern)
    {
        var regex = new Regex(pattern);
        foreach (var window in ListVisibleWindows())
        {
            if (regex.IsMatch(window.Title))
                return window.Hwnd;
        }
        return nint.Zero;
    }

    public IReadOnlyList<WindowInfo> ListVisibleWindows()
    {
        var windows = new List<WindowInfo>();
        NativeMethods.EnumWindows((hwnd, _) =>
        {
            if (!NativeMethods.IsWindowVisible(hwnd))
                return true;

            var title = GetWindowText(hwnd);
            if (string.IsNullOrWhiteSpace(title))
                return true;

            windows.Add(new WindowInfo(hwnd, title, GetClassName(hwnd)));
            return true;
        }, nint.Zero);
        return windows;
    }

    public bool IsWindowValid(nint hwnd) => hwnd != nint.Zero && NativeMethods.IsWindow(hwnd) && NativeMethods.IsWindowVisible(hwnd);

    public bool IsWindowMinimized(nint hwnd) => NativeMethods.IsIconic(hwnd);

    public RectI GetWindowRect(nint hwnd)
    {
        NativeMethods.GetWindowRect(hwnd, out var rect);
        return new RectI(rect.Left, rect.Top, rect.Right, rect.Bottom);
    }

    public RectI GetClientRect(nint hwnd)
    {
        NativeMethods.GetClientRect(hwnd, out var rect);
        var topLeft = new NativeMethods.POINT { X = rect.Left, Y = rect.Top };
        NativeMethods.ClientToScreen(hwnd, ref topLeft);
        return new RectI(topLeft.X, topLeft.Y, topLeft.X + rect.Right - rect.Left, topLeft.Y + rect.Bottom - rect.Top);
    }

    public SizeI GetClientSize(nint hwnd)
    {
        NativeMethods.GetClientRect(hwnd, out var rect);
        return new SizeI(rect.Right - rect.Left, rect.Bottom - rect.Top);
    }

    public PointI ClientToScreen(nint hwnd, PointI point)
    {
        var p = new NativeMethods.POINT { X = point.X, Y = point.Y };
        NativeMethods.ClientToScreen(hwnd, ref p);
        return new PointI(p.X, p.Y);
    }

    public PointI ScreenToClient(nint hwnd, PointI point)
    {
        var p = new NativeMethods.POINT { X = point.X, Y = point.Y };
        NativeMethods.ScreenToClient(hwnd, ref p);
        return new PointI(p.X, p.Y);
    }

    public bool IsPointInClient(nint hwnd, PointI screenPoint)
    {
        var client = ScreenToClient(hwnd, screenPoint);
        NativeMethods.GetClientRect(hwnd, out var rect);
        return client.X >= rect.Left && client.X < rect.Right && client.Y >= rect.Top && client.Y < rect.Bottom;
    }

    public bool ActivateWindow(nint hwnd)
    {
        if (IsWindowMinimized(hwnd))
            NativeMethods.ShowWindow(hwnd, NativeMethods.SwRestore);
        return NativeMethods.SetForegroundWindow(hwnd);
    }

    public bool SetWindowSize(nint hwnd, int width, int height)
    {
        var rect = GetWindowRect(hwnd);
        return NativeMethods.SetWindowPos(hwnd, nint.Zero, rect.Left, rect.Top, width, height, NativeMethods.SwpShowWindow);
    }

    public bool VerifyClickWindow(nint hwnd, PointI screenPoint)
    {
        if (!IsWindowValid(hwnd) || IsWindowMinimized(hwnd) || !IsPointInClient(hwnd, screenPoint))
            return false;

        var atPoint = NativeMethods.WindowFromPoint(new NativeMethods.POINT { X = screenPoint.X, Y = screenPoint.Y });
        while (atPoint != nint.Zero)
        {
            if (atPoint == hwnd)
                return true;
            atPoint = NativeMethods.GetParent(atPoint);
        }
        return false;
    }

    private static string GetWindowText(nint hwnd)
    {
        var sb = new StringBuilder(512);
        NativeMethods.GetWindowTextW(hwnd, sb, sb.Capacity);
        return sb.ToString();
    }

    private static string GetClassName(nint hwnd)
    {
        var sb = new StringBuilder(256);
        NativeMethods.GetClassNameW(hwnd, sb, sb.Capacity);
        return sb.ToString();
    }
}
