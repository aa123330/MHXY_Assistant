using System.Drawing;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.Core.Services;

public interface IGameStateDetector
{
    GameStateDetection Detect(Bitmap source);
}
