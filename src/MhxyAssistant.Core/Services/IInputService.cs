using MhxyAssistant.Core.Models;

namespace MhxyAssistant.Core.Services;

public interface IInputService
{
    PointI GetCursorPosition();
    bool MoveTo(PointI screenPoint, int variance = 5, bool human = false);
    bool Click(PointI screenPoint, string button = "left", int variance = 5, bool moveAway = true, RectI? bounds = null);
    bool DoubleClick(PointI screenPoint, int variance = 5);
    bool RightClick(PointI screenPoint, int variance = 5);
    bool Hotkey(params string[] keys);
}
