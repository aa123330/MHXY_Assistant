using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Windows;

public sealed class InputService : IInputService
{
    private readonly Random _random = new();

    public PointI GetCursorPosition()
    {
        NativeMethods.GetCursorPos(out var point);
        return new PointI(point.X, point.Y);
    }

    public bool MoveTo(PointI screenPoint, int variance = 5, bool human = false)
    {
        var target = Jitter(screenPoint, variance);
        return SetPosition(target);
    }

    public bool Click(PointI screenPoint, string button = "left", int variance = 5, bool moveAway = true, RectI? bounds = null)
    {
        var target = Clamp(Jitter(screenPoint, variance), bounds);
        if (!SetPosition(target))
            return false;

        var (down, up) = ButtonFlags(button);
        var ok = SendMouse(0, 0, down) && SendMouse(0, 0, up);
        if (ok && moveAway)
            MoveAway(target);
        return ok;
    }

    public bool DoubleClick(PointI screenPoint, int variance = 5)
    {
        return Click(screenPoint, variance: variance, moveAway: false)
            && Click(screenPoint, variance: 0);
    }

    public bool RightClick(PointI screenPoint, int variance = 5)
    {
        return Click(screenPoint, "right", variance);
    }

    public bool Hotkey(params string[] keys)
    {
        var vkCodes = keys.Select(ToVirtualKey).Where(vk => vk != 0).ToArray();
        if (vkCodes.Length != keys.Length)
            return false;

        foreach (var vk in vkCodes)
        {
            if (!SendKey(vk, false))
                return false;
            Thread.Sleep(_random.Next(15, 31));
        }

        Thread.Sleep(50);

        foreach (var vk in vkCodes.Reverse())
        {
            if (!SendKey(vk, true))
                return false;
            Thread.Sleep(_random.Next(15, 31));
        }

        return true;
    }

    private bool SetPosition(PointI point)
    {
        var (x, y) = ToAbsolute(point);
        return SendMouse(x, y, NativeMethods.MouseEventFMove | NativeMethods.MouseEventFAbsolute | NativeMethods.MouseEventFVirtualDesk);
    }

    private bool SendMouse(int dx, int dy, uint flags)
    {
        var input = new NativeMethods.INPUT
        {
            Type = NativeMethods.InputMouse,
            Data = new NativeMethods.INPUTUNION
            {
                MouseInput = new NativeMethods.MOUSEINPUT
                {
                    Dx = dx,
                    Dy = dy,
                    DwFlags = flags,
                },
            },
        };
        return NativeMethods.SendInput(1, [input], System.Runtime.InteropServices.Marshal.SizeOf<NativeMethods.INPUT>()) == 1;
    }

    private static bool SendKey(ushort vk, bool keyUp)
    {
        var input = new NativeMethods.INPUT
        {
            Type = NativeMethods.InputKeyboard,
            Data = new NativeMethods.INPUTUNION
            {
                KeyboardInput = new NativeMethods.KEYBDINPUT
                {
                    Vk = vk,
                    Flags = keyUp ? NativeMethods.KeyEventFKeyUp : 0,
                },
            },
        };
        return NativeMethods.SendInput(1, [input], System.Runtime.InteropServices.Marshal.SizeOf<NativeMethods.INPUT>()) == 1;
    }

    private static ushort ToVirtualKey(string key)
    {
        return key.Trim().ToLowerInvariant() switch
        {
            "ctrl" or "control" => 0x11,
            "shift" => 0x10,
            "alt" => 0x12,
            "tab" => 0x09,
            "enter" or "return" => 0x0D,
            "esc" or "escape" => 0x1B,
            "space" => 0x20,
            "f1" => 0x70,
            "f2" => 0x71,
            "f3" => 0x72,
            "f4" => 0x73,
            "f5" => 0x74,
            "f6" => 0x75,
            "f7" => 0x76,
            "f8" => 0x77,
            "f9" => 0x78,
            "f10" => 0x79,
            "f11" => 0x7A,
            "f12" => 0x7B,
            { Length: 1 } text when char.IsLetterOrDigit(text[0]) => (ushort)char.ToUpperInvariant(text[0]),
            _ => 0,
        };
    }

    private PointI Jitter(PointI point, int variance)
    {
        if (variance <= 0)
            return point;
        return new PointI(point.X + _random.Next(-variance, variance + 1), point.Y + _random.Next(-variance, variance + 1));
    }

    private static PointI Clamp(PointI point, RectI? bounds)
    {
        if (bounds is null)
            return point;
        return new PointI(
            Math.Max(bounds.Value.Left, Math.Min(point.X, bounds.Value.Right)),
            Math.Max(bounds.Value.Top, Math.Min(point.Y, bounds.Value.Bottom)));
    }

    private void MoveAway(PointI point)
    {
        var angle = _random.NextDouble() * Math.PI * 2;
        var radius = _random.Next(25, 55);
        SetPosition(new PointI(point.X + (int)(Math.Cos(angle) * radius), point.Y + (int)(Math.Sin(angle) * radius)));
    }

    private static (uint Down, uint Up) ButtonFlags(string button)
    {
        return button.Equals("right", StringComparison.OrdinalIgnoreCase)
            ? (NativeMethods.MouseEventFRightDown, NativeMethods.MouseEventFRightUp)
            : (NativeMethods.MouseEventFLeftDown, NativeMethods.MouseEventFLeftUp);
    }

    private static (int X, int Y) ToAbsolute(PointI point)
    {
        var vx = NativeMethods.GetSystemMetrics(76);
        var vy = NativeMethods.GetSystemMetrics(77);
        var vw = Math.Max(NativeMethods.GetSystemMetrics(78), 1);
        var vh = Math.Max(NativeMethods.GetSystemMetrics(79), 1);
        return (
            (point.X - vx) * 65535 / Math.Max(vw - 1, 1),
            (point.Y - vy) * 65535 / Math.Max(vh - 1, 1));
    }
}
