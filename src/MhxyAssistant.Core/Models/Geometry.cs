namespace MhxyAssistant.Core.Models;

public readonly record struct PointI(int X, int Y);

public readonly record struct SizeI(int Width, int Height);

public readonly record struct RectI(int Left, int Top, int Right, int Bottom)
{
    public int Width => Right - Left;
    public int Height => Bottom - Top;
    public PointI Center => new(Left + Width / 2, Top + Height / 2);

    public bool Contains(PointI point)
    {
        return point.X >= Left && point.X < Right && point.Y >= Top && point.Y < Bottom;
    }
}
