using System.Drawing;
using System.Drawing.Drawing2D;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Vision;

public sealed class ImageHasher(int hashSize = 16) : IImageHasher
{
    public string Compute(Bitmap source)
    {
        using var resized = new Bitmap(hashSize, hashSize);
        using (var g = Graphics.FromImage(resized))
        {
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.DrawImage(source, 0, 0, hashSize, hashSize);
        }

        var values = new byte[hashSize * hashSize];
        var sum = 0;
        var index = 0;
        for (var y = 0; y < hashSize; y++)
        {
            for (var x = 0; x < hashSize; x++)
            {
                var c = resized.GetPixel(x, y);
                var gray = (byte)((c.R * 299 + c.G * 587 + c.B * 114) / 1000);
                values[index++] = gray;
                sum += gray;
            }
        }

        var average = sum / values.Length;
        var hex = new char[values.Length / 4];
        for (var i = 0; i < hex.Length; i++)
        {
            var value = 0;
            for (var j = 0; j < 4; j++)
                value = (value << 1) | (values[i * 4 + j] >= average ? 1 : 0);
            hex[i] = value.ToString("x")[0];
        }

        return new string(hex);
    }

    public int Hamming(string left, string right)
    {
        var length = Math.Max(left.Length, right.Length);
        left = left.PadRight(length, '0');
        right = right.PadRight(length, '0');
        var distance = 0;
        for (var i = 0; i < length; i++)
        {
            if (left[i] != right[i])
                distance++;
        }
        return distance;
    }

    public bool Matches(Bitmap source, string hash, int threshold = 20)
    {
        return Hamming(Compute(source), hash) < threshold;
    }

    public bool Compare(Bitmap left, Bitmap right, int threshold = 15)
    {
        return Hamming(Compute(left), Compute(right)) < threshold;
    }
}
