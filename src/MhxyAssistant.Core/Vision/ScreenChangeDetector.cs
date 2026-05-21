using System.Drawing;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Vision;

public sealed class ScreenChangeDetector : IScreenChangeDetector
{
    public bool HasChanged(Bitmap previous, Bitmap current, double threshold = 0.03)
    {
        if (previous.Width != current.Width || previous.Height != current.Height)
            return true;

        var changed = 0;
        var total = 0;
        for (var y = 0; y < current.Height; y += 4)
        {
            for (var x = 0; x < current.Width; x += 4)
            {
                var a = previous.GetPixel(x, y);
                var b = current.GetPixel(x, y);
                if (Math.Abs(a.R - b.R) + Math.Abs(a.G - b.G) + Math.Abs(a.B - b.B) > 45)
                    changed++;
                total++;
            }
        }

        return total > 0 && (double)changed / total >= threshold;
    }
}
