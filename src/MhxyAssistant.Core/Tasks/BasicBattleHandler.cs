using System.Drawing;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Tasks;

public sealed class BasicBattleHandler : IBattleHandler
{
    private static readonly string[] TargetPrompts = ["请选择", "选择目标", "选择攻击", "请点击", "攻击目标"];
    private static readonly string[] EnemyKeywords = ["妖", "怪", "鬼", "僵尸", "马面", "牛头", "骷髅", "护卫", "强盗"];

    private int _wrongClicks;

    public async Task<bool> HandleAsync(TaskContext context, CancellationToken cancellationToken)
    {
        if (!context.EnsureGameWindow())
            return false;

        using var image = context.CaptureGameClient();
        if (!context.Colors.HasBattleUi(image))
        {
            _wrongClicks = 0;
            return false;
        }

        context.Log("[battle] Battle UI detected.");

        if (TryHandleTargetPopup(context, image))
        {
            await Task.Delay(350, cancellationToken).ConfigureAwait(false);
            return true;
        }

        var action = context.Config.Battle.DefaultAction;
        if (action.Equals("skill", StringComparison.OrdinalIgnoreCase))
            context.Input.Hotkey("alt", "w");
        else if (action.Equals("defend", StringComparison.OrdinalIgnoreCase))
            context.Input.Hotkey("alt", "d");
        else
            context.Input.Hotkey("alt", "a");

        await Task.Delay(350, cancellationToken).ConfigureAwait(false);

        using var targeting = context.CaptureGameClient();
        if (TryClickEnemyTarget(context, targeting))
        {
            _wrongClicks = 0;
            await Task.Delay(900, cancellationToken).ConfigureAwait(false);
            return true;
        }

        _wrongClicks++;
        if (_wrongClicks >= Math.Max(1, context.Config.Battle.MaxWrongClicks))
        {
            context.Log("[battle] Target selection failed repeatedly; trying keyboard fallback.");
            context.Input.Hotkey("esc");
            await Task.Delay(150, cancellationToken).ConfigureAwait(false);
            context.Input.Hotkey("alt", "a");
            await Task.Delay(150, cancellationToken).ConfigureAwait(false);
            context.Input.Hotkey("tab");
            await Task.Delay(150, cancellationToken).ConfigureAwait(false);
            context.Input.Hotkey("alt", "a");
            _wrongClicks = 0;
            return true;
        }

        context.Input.Hotkey("esc");
        return true;
    }

    private static bool TryHandleTargetPopup(TaskContext context, Bitmap image)
    {
        if (context.Config.Battle.PopupDetection)
        {
            foreach (var templateName in context.Config.Battle.PopupTemplates)
            {
                var path = ResolveBattleTemplate(templateName);
                if (path is null)
                    continue;

                var match = context.Templates.MatchBest(image, path, 0.70);
                if (match is null)
                    continue;

                var selected = SelectPopupCharacter(context, image, match.BBox);
                context.Log($"[battle] handled target popup via template {Path.GetFileName(path)}.");
                return context.ClickClient(selected, variance: 6);
            }
        }

        var promptRegion = new RectI((int)(image.Width * 0.15), 0, (int)(image.Width * 0.85), (int)(image.Height * 0.32));
        var hasPrompt = context.Ocr.Recognize(image, promptRegion)
            .Any(result => TargetPrompts.Any(prompt => result.Text.Contains(prompt, StringComparison.OrdinalIgnoreCase)));
        if (!hasPrompt)
            return false;

        var fallback = new PointI((int)(image.Width * 0.35), (int)(image.Height * 0.45));
        context.Log("[battle] handled target popup via OCR prompt.");
        return context.ClickClient(fallback, variance: 8);
    }

    private static PointI SelectPopupCharacter(TaskContext context, Bitmap image, RectI popup)
    {
        var characterAreaTop = Math.Min(image.Height - 1, popup.Top + Math.Max(45, popup.Height / 4));
        var characterAreaHeight = Math.Max(80, popup.Height / 2);
        var characterAreaBottom = Math.Min(image.Height, characterAreaTop + characterAreaHeight);
        var characterWidth = Math.Max(1, popup.Width / 4);

        if (context.Yolo.IsAvailable)
        {
            var detections = context.Yolo.Detect(image)
                .Where(detection => popup.Contains(detection.Center))
                .Where(detection => detection.ClassName.Contains("npc", StringComparison.OrdinalIgnoreCase) ||
                                    detection.ClassName.Contains("monster", StringComparison.OrdinalIgnoreCase) ||
                                    detection.ClassName.Contains("character", StringComparison.OrdinalIgnoreCase))
                .OrderByDescending(detection => detection.Confidence)
                .ToArray();

            if (detections.Length > 0)
                return detections[0].Center;
        }

        var slot = 1;
        return new PointI(
            popup.Left + slot * characterWidth + characterWidth / 2,
            characterAreaTop + (characterAreaBottom - characterAreaTop) / 2);
    }

    private static bool TryClickEnemyTarget(TaskContext context, Bitmap image)
    {
        if (context.Yolo.IsAvailable)
        {
            var target = context.Yolo.Detect(image)
                .Where(detection => detection.ClassName.Contains("monster", StringComparison.OrdinalIgnoreCase) ||
                                    detection.ClassName.Contains("ghost", StringComparison.OrdinalIgnoreCase) ||
                                    detection.ClassName.Contains("enemy", StringComparison.OrdinalIgnoreCase))
                .OrderByDescending(detection => detection.Confidence)
                .FirstOrDefault();

            if (target is not null)
                return context.ClickClient(target.Center, variance: 10);
        }

        var enemyRegion = new RectI(
            (int)(image.Width * 0.08),
            (int)(image.Height * 0.10),
            (int)(image.Width * 0.92),
            (int)(image.Height * 0.62));

        var ocrTarget = context.Ocr.Recognize(image, enemyRegion)
            .Where(result => !string.IsNullOrWhiteSpace(result.Text))
            .Where(result => EnemyKeywords.Any(keyword => result.Text.Contains(keyword, StringComparison.OrdinalIgnoreCase)) ||
                             result.Text.Trim().Length >= 2)
            .OrderByDescending(result => result.Confidence)
            .FirstOrDefault();

        if (ocrTarget is not null)
        {
            var point = new PointI(ocrTarget.BBox.Center.X, ocrTarget.BBox.Bottom + 35);
            return context.ClickClient(point, variance: 10);
        }

        var fallback = new PointI(image.Width / 2, (int)(image.Height * 0.38));
        return context.ClickClient(fallback, variance: 24);
    }

    private static string? ResolveBattleTemplate(string templateName)
    {
        if (string.IsNullOrWhiteSpace(templateName))
            return null;

        var candidates = new List<string>();
        if (Path.IsPathRooted(templateName))
            candidates.Add(templateName);
        else
        {
            candidates.Add(templateName);
            candidates.Add(Path.Combine("data", "templates", "battle", templateName));
            candidates.Add(Path.Combine("data", "templates", templateName));
        }

        var bases = new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory };
        foreach (var candidate in candidates)
        {
            if (File.Exists(candidate))
                return Path.GetFullPath(candidate);

            foreach (var root in bases)
            {
                var rooted = Path.GetFullPath(Path.Combine(root, candidate));
                if (File.Exists(rooted))
                    return rooted;
            }
        }

        return null;
    }
}
