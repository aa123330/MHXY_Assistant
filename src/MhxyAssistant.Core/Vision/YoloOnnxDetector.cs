using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;
using OpenCvSharp;

namespace MhxyAssistant.Core.Vision;

public sealed class YoloOnnxDetector : IYoloDetector, IDisposable
{
    private readonly InferenceSession? _session;
    private readonly string _inputName;
    private readonly string[] _classNames;
    private readonly int _inputWidth;
    private readonly int _inputHeight;
    private readonly float _confidenceThreshold;
    private readonly float _iouThreshold;

    public YoloOnnxDetector(
        string modelPath,
        IReadOnlyList<string>? classNames = null,
        int inputWidth = 640,
        int inputHeight = 640,
        float confidenceThreshold = 0.25f,
        float iouThreshold = 0.45f)
    {
        _classNames = classNames?.ToArray() ?? [];
        _inputWidth = Math.Max(1, inputWidth);
        _inputHeight = Math.Max(1, inputHeight);
        _confidenceThreshold = Math.Clamp(confidenceThreshold, 0, 1);
        _iouThreshold = Math.Clamp(iouThreshold, 0, 1);
        _inputName = "images";

        if (string.IsNullOrWhiteSpace(modelPath) || !File.Exists(modelPath))
            return;

        try
        {
            _session = new InferenceSession(modelPath);
            _inputName = _session.InputMetadata.Keys.FirstOrDefault() ?? _inputName;
        }
        catch (OnnxRuntimeException)
        {
            _session = null;
        }
        catch (InvalidOperationException)
        {
            _session = null;
        }
        catch (ArgumentException)
        {
            _session = null;
        }
        catch (DllNotFoundException)
        {
            _session = null;
        }
    }

    public bool IsAvailable => _session is not null;

    public IReadOnlyList<DetectionResult> Detect(Bitmap source)
    {
        if (_session is null || source.Width <= 0 || source.Height <= 0)
            return [];

        var input = BuildInputTensor(source, out var scale, out var padX, out var padY);
        var inputValue = NamedOnnxValue.CreateFromTensor(_inputName, input);

        Tensor<float>? output;
        try
        {
            using var results = _session.Run([inputValue]);
            output = results.FirstOrDefault()?.AsTensor<float>();
            if (output is null)
                return [];

            var detections = ParseOutput(output, source.Width, source.Height, scale, padX, padY);
            return SuppressOverlaps(detections, _iouThreshold)
                .OrderByDescending(d => d.Confidence)
                .ToArray();
        }
        catch (OnnxRuntimeException)
        {
            return [];
        }
        catch (InvalidOperationException)
        {
            return [];
        }
    }

    public DetectionResult? FindClass(Bitmap source, int classId)
    {
        return Detect(source)
            .Where(d => d.ClassId == classId)
            .OrderByDescending(d => d.Confidence)
            .FirstOrDefault();
    }

    public DetectionResult? FindClassName(Bitmap source, string className)
    {
        if (string.IsNullOrWhiteSpace(className))
            return null;

        return Detect(source)
            .Where(d => string.Equals(d.ClassName, className, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(d => d.Confidence)
            .FirstOrDefault();
    }

    public void Dispose()
    {
        _session?.Dispose();
    }

    private DenseTensor<float> BuildInputTensor(Bitmap source, out float scale, out int padX, out int padY)
    {
        using var sourceMat = BitmapToMat(source);

        scale = Math.Min((float)_inputWidth / sourceMat.Width, (float)_inputHeight / sourceMat.Height);
        var resizedWidth = Math.Max(1, (int)Math.Round(sourceMat.Width * scale));
        var resizedHeight = Math.Max(1, (int)Math.Round(sourceMat.Height * scale));
        padX = (_inputWidth - resizedWidth) / 2;
        padY = (_inputHeight - resizedHeight) / 2;

        using var resized = new Mat();
        Cv2.Resize(sourceMat, resized, new OpenCvSharp.Size(resizedWidth, resizedHeight));
        using var canvas = new Mat(
            new OpenCvSharp.Size(_inputWidth, _inputHeight),
            MatType.CV_8UC3,
            new Scalar(114, 114, 114));
        using (var roi = new Mat(canvas, new OpenCvSharp.Rect(padX, padY, resizedWidth, resizedHeight)))
        {
            resized.CopyTo(roi);
        }

        var tensor = new DenseTensor<float>([1, 3, _inputHeight, _inputWidth]);
        for (var y = 0; y < _inputHeight; y++)
        {
            for (var x = 0; x < _inputWidth; x++)
            {
                var pixel = canvas.Get<Vec3b>(y, x);
                tensor[0, 0, y, x] = pixel.Item2 / 255f;
                tensor[0, 1, y, x] = pixel.Item1 / 255f;
                tensor[0, 2, y, x] = pixel.Item0 / 255f;
            }
        }

        return tensor;
    }

    private IReadOnlyList<DetectionResult> ParseOutput(
        Tensor<float> output,
        int sourceWidth,
        int sourceHeight,
        float scale,
        int padX,
        int padY)
    {
        var dimensions = output.Dimensions.ToArray();
        if (dimensions.Length != 3)
            return [];

        var values = output.ToArray();
        var rows = dimensions[1];
        var columns = dimensions[2];

        if (rows < columns && rows >= 6)
            return ParseTransposedRows(values, rows, columns, sourceWidth, sourceHeight, scale, padX, padY);

        if (columns >= 6)
            return ParseRows(values, rows, columns, sourceWidth, sourceHeight, scale, padX, padY);

        if (rows >= 6)
            return ParseTransposedRows(values, rows, columns, sourceWidth, sourceHeight, scale, padX, padY);

        return [];
    }

    private IReadOnlyList<DetectionResult> ParseRows(
        float[] values,
        int rows,
        int columns,
        int sourceWidth,
        int sourceHeight,
        float scale,
        int padX,
        int padY)
    {
        var detections = new List<DetectionResult>();
        for (var row = 0; row < rows; row++)
        {
            var offset = row * columns;
            AddDetection(
                detections,
                values[offset],
                values[offset + 1],
                values[offset + 2],
                values[offset + 3],
                values.AsSpan(offset + 4, columns - 4),
                sourceWidth,
                sourceHeight,
                scale,
                padX,
                padY);
        }

        return detections;
    }

    private IReadOnlyList<DetectionResult> ParseTransposedRows(
        float[] values,
        int rows,
        int columns,
        int sourceWidth,
        int sourceHeight,
        float scale,
        int padX,
        int padY)
    {
        var detections = new List<DetectionResult>();
        var scores = new float[rows - 4];

        for (var column = 0; column < columns; column++)
        {
            for (var scoreIndex = 0; scoreIndex < scores.Length; scoreIndex++)
                scores[scoreIndex] = values[(scoreIndex + 4) * columns + column];

            AddDetection(
                detections,
                values[column],
                values[columns + column],
                values[2 * columns + column],
                values[3 * columns + column],
                scores,
                sourceWidth,
                sourceHeight,
                scale,
                padX,
                padY);
        }

        return detections;
    }

    private void AddDetection(
        List<DetectionResult> detections,
        float centerX,
        float centerY,
        float width,
        float height,
        ReadOnlySpan<float> scoreValues,
        int sourceWidth,
        int sourceHeight,
        float scale,
        int padX,
        int padY)
    {
        if (scoreValues.Length == 0)
            return;

        var hasObjectness = _classNames.Length > 0 && scoreValues.Length == _classNames.Length + 1;
        var objectness = hasObjectness ? scoreValues[0] : 1f;
        var scoreStart = hasObjectness ? 1 : 0;

        var classId = -1;
        var bestClassScore = 0f;
        for (var i = scoreStart; i < scoreValues.Length; i++)
        {
            if (scoreValues[i] <= bestClassScore)
                continue;

            bestClassScore = scoreValues[i];
            classId = i - scoreStart;
        }

        var confidence = objectness * bestClassScore;
        if (classId < 0 || confidence < _confidenceThreshold)
            return;

        var left = (centerX - width / 2 - padX) / scale;
        var top = (centerY - height / 2 - padY) / scale;
        var right = (centerX + width / 2 - padX) / scale;
        var bottom = (centerY + height / 2 - padY) / scale;

        var rect = new RectI(
            ClampToInt(left, 0, sourceWidth),
            ClampToInt(top, 0, sourceHeight),
            ClampToInt(right, 0, sourceWidth),
            ClampToInt(bottom, 0, sourceHeight));

        if (rect.Width <= 0 || rect.Height <= 0)
            return;

        detections.Add(new DetectionResult(
            classId,
            GetClassName(classId),
            confidence,
            rect,
            rect.Center));
    }

    private string GetClassName(int classId)
    {
        return classId >= 0 && classId < _classNames.Length
            ? _classNames[classId]
            : classId.ToString();
    }

    private static int ClampToInt(float value, int min, int max)
    {
        if (float.IsNaN(value) || float.IsInfinity(value))
            return min;

        return Math.Clamp((int)Math.Round(value), min, max);
    }

    private static IReadOnlyList<DetectionResult> SuppressOverlaps(
        IEnumerable<DetectionResult> detections,
        double iouThreshold)
    {
        var accepted = new List<DetectionResult>();
        foreach (var detection in detections.OrderByDescending(d => d.Confidence))
        {
            if (accepted.All(existing =>
                    existing.ClassId != detection.ClassId ||
                    IntersectionOverUnion(existing.BBox, detection.BBox) < iouThreshold))
            {
                accepted.Add(detection);
            }
        }

        return accepted;
    }

    private static double IntersectionOverUnion(RectI a, RectI b)
    {
        var left = Math.Max(a.Left, b.Left);
        var top = Math.Max(a.Top, b.Top);
        var right = Math.Min(a.Right, b.Right);
        var bottom = Math.Min(a.Bottom, b.Bottom);
        var intersection = Math.Max(0, right - left) * Math.Max(0, bottom - top);
        var areaA = Math.Max(0, a.Width) * Math.Max(0, a.Height);
        var areaB = Math.Max(0, b.Width) * Math.Max(0, b.Height);
        var union = areaA + areaB - intersection;
        return union == 0 ? 0 : (double)intersection / union;
    }

    private static Mat BitmapToMat(Bitmap bitmap)
    {
        using var clone = bitmap.Clone(
            new Rectangle(0, 0, bitmap.Width, bitmap.Height),
            PixelFormat.Format24bppRgb);
        var data = clone.LockBits(
            new Rectangle(0, 0, clone.Width, clone.Height),
            ImageLockMode.ReadOnly,
            PixelFormat.Format24bppRgb);
        try
        {
            var mat = new Mat(clone.Height, clone.Width, MatType.CV_8UC3);
            var rowBytes = clone.Width * 3;
            var buffer = new byte[rowBytes];
            for (var y = 0; y < clone.Height; y++)
            {
                Marshal.Copy(data.Scan0 + y * data.Stride, buffer, 0, rowBytes);
                Marshal.Copy(buffer, 0, IntPtr.Add(mat.Data, (int)(y * mat.Step())), rowBytes);
            }

            return mat;
        }
        finally
        {
            clone.UnlockBits(data);
        }
    }
}
