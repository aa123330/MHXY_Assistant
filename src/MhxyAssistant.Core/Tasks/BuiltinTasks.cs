using System.Drawing;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;
using MhxyAssistant.Core.Vision;

namespace MhxyAssistant.Core.Tasks;

public sealed class ShimenTask : StepTaskBase
{
    public override string Id => "shimen";
    public override string Name => "师门任务";
    public override string Description => "回师门、找师傅接任务，按任务追踪与战斗/对话状态推进多轮师门。";

    private int _round;
    private string _taskType = "unknown";
    private string _lastTaskText = string.Empty;

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("回师门", async (ctx, ct) =>
            {
                if (!TaskFlow.EnsureReady(ctx, activate: true))
                    return StepResult.Fail("Game window is not bound or cannot be activated.");

                ctx.Input.Hotkey("f8");
                await DelayAsync(1500, ct);
                return StepResult.Next("已发送 F8，准备查找师傅/任务入口。");
            }, timeout: TimeSpan.FromSeconds(8), retries: 2),

            new("找师傅并接取任务", async (ctx, ct) =>
            {
                using var image = TaskFlow.CaptureReady(ctx);

                if (TaskFlow.TryClickTemplate(ctx, image, ctx.Config.Tasks.Shimen.MasterTemplate, 0.72, out var masterMessage))
                {
                    ctx.Log(masterMessage);
                    await DelayAsync(800, ct);
                    await TaskFlow.AdvanceDialogAsync(ctx, ct, clicks: 3).ConfigureAwait(false);
                    return StepResult.Next("已尝试与师傅对话。");
                }

                if (TaskFlow.TryClickTemplate(ctx, image, ctx.Config.Tasks.Shimen.TaskButtonTemplate, 0.70, out var taskMessage))
                {
                    ctx.Log(taskMessage);
                    await DelayAsync(800, ct);
                    return StepResult.Next("已点击任务按钮。");
                }

                if (TaskFlow.TryClickOcrText(ctx, image, TaskFlow.ShimenAcceptKeywords, out var ocrMessage))
                {
                    ctx.Log(ocrMessage);
                    await DelayAsync(800, ct);
                    return StepResult.Next("已点击师门 OCR 入口。");
                }

                if (TaskFlow.TryClickYoloClass(ctx, image, ["npc", "master", "dialog", "button"], out var yoloMessage))
                {
                    ctx.Log(yoloMessage);
                    await DelayAsync(800, ct);
                    return StepResult.Next("已点击疑似师门入口。");
                }

                return StepResult.Continue($"{masterMessage}; {taskMessage}; 未找到师门入口。");
            }, timeout: TimeSpan.FromSeconds(18), retries: 3),

            new("识别师门类型", async (ctx, ct) =>
            {
                await TaskFlow.AdvanceDialogAsync(ctx, ct, clicks: 4).ConfigureAwait(false);
                using var image = TaskFlow.CaptureReady(ctx);
                _lastTaskText = TaskFlow.ReadQuestTrackerText(ctx, image);
                _taskType = TaskFlow.IdentifyShimenTaskType(_lastTaskText);
                ctx.Log($"[shimen] 任务文本='{_lastTaskText}', type={_taskType}");
                return StepResult.Next();
            }, timeout: TimeSpan.FromSeconds(12), retries: 2),

            new("执行师门任务", async (ctx, ct) =>
            {
                var acted = _taskType switch
                {
                    "combat" or "escort" => await TaskFlow.GoFightOrInteractAsync(ctx, ct, "shimen").ConfigureAwait(false),
                    "patrol" => await TaskFlow.PatrolCyclesAsync(ctx, ct, cycles: 10, "shimen").ConfigureAwait(false),
                    "buy" or "use" or "submit" => await TaskFlow.GiveOrSubmitAsync(ctx, ct, "shimen").ConfigureAwait(false),
                    _ => await TaskFlow.GoFindOrInteractAsync(ctx, ct, "shimen").ConfigureAwait(false),
                };

                return acted
                    ? StepResult.Next($"师门任务执行阶段完成：{_taskType}。")
                    : StepResult.Continue("师门执行阶段未找到可操作目标。");
            }, timeout: TimeSpan.FromMinutes(3), retries: 2),

            new("回师门交任务", async (ctx, ct) =>
            {
                ctx.Input.Hotkey("f8");
                await DelayAsync(1500, ct);

                using var image = TaskFlow.CaptureReady(ctx);
                if (TaskFlow.TryClickTemplate(ctx, image, ctx.Config.Tasks.Shimen.MasterTemplate, 0.70, out var masterMessage) ||
                    TaskFlow.TryClickOcrText(ctx, image, TaskFlow.ShimenAcceptKeywords, out masterMessage))
                {
                    ctx.Log(masterMessage);
                    await DelayAsync(800, ct);
                }

                await TaskFlow.AdvanceDialogAsync(ctx, ct, clicks: 5).ConfigureAwait(false);
                return StepResult.Next("已尝试回师门交任务。");
            }, timeout: TimeSpan.FromSeconds(30), retries: 2),

            new("检查师门轮次", (ctx, _) =>
            {
                _round++;
                var maxRounds = Math.Clamp(ctx.Config.Tasks.Shimen.MaxRounds, 1, 20);
                ctx.Log($"[shimen] 完成第 {_round}/{maxRounds} 轮。");

                if (_round >= maxRounds)
                    return Task.FromResult(StepResult.Complete("师门轮次已完成。"));

                return Task.FromResult(StepResult.Restart("继续下一轮师门。"));
            }, timeout: TimeSpan.FromSeconds(5), retries: 1),
        ];
    }
}

public sealed class ZhuoguiTask : StepTaskBase
{
    public override string Id => "zhuogui";
    public override string Name => "捉鬼任务";
    public override string Description => "找钟馗接任务，使用天眼定位鬼怪，点击追踪目标并处理战斗。";

    private int _round;

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("找钟馗接任务", async (ctx, ct) =>
            {
                if (!TaskFlow.EnsureReady(ctx, activate: true))
                    return StepResult.Fail("Game window is not bound or cannot be activated.");

                using var image = TaskFlow.CaptureReady(ctx);
                if (TaskFlow.TryClickOcrText(ctx, image, TaskFlow.ZhongKuiKeywords, out var ocrMessage) ||
                    TaskFlow.TryClickYoloClass(ctx, image, ["zhongkui", "npc", "dialog", "button"], out ocrMessage))
                {
                    ctx.Log(ocrMessage);
                    await DelayAsync(800, ct);
                    await TaskFlow.AdvanceDialogAsync(ctx, ct, clicks: 4).ConfigureAwait(false);
                    return StepResult.Next("已尝试接取捉鬼任务。");
                }

                await TaskFlow.AdvanceDialogAsync(ctx, ct, clicks: 2).ConfigureAwait(false);
                return StepResult.Next("未定位钟馗，已尝试推进当前对话。");
            }, timeout: TimeSpan.FromSeconds(20), retries: 3),

            new("使用天眼通符", async (ctx, ct) =>
            {
                ctx.Input.Hotkey("alt", "t");
                await DelayAsync(1000, ct);
                return StepResult.Next("已发送 Alt+T。");
            }, timeout: TimeSpan.FromSeconds(5), retries: 2),

            new("前往鬼怪目标", async (ctx, ct) =>
            {
                using var image = TaskFlow.CaptureReady(ctx);
                if (TaskFlow.TryClickOcrText(ctx, image, TaskFlow.GhostKeywords, out var ghostMessage) ||
                    TaskFlow.TryClickYoloClass(ctx, image, ["ghost", "monster", "npc"], out ghostMessage) ||
                    TaskFlow.TryClickQuestObjective(ctx, image, out ghostMessage))
                {
                    ctx.Log(ghostMessage);
                    await DelayAsync(1200, ct);
                    return StepResult.Next("已点击捉鬼目标/追踪。");
                }

                return StepResult.Continue("未找到鬼怪、地图线索或任务追踪目标。");
            }, timeout: TimeSpan.FromSeconds(25), retries: 3),

            new("处理捉鬼战斗与交付", async (ctx, ct) =>
            {
                var advanced = await TaskFlow.GoFightOrInteractAsync(ctx, ct, "zhuogui").ConfigureAwait(false);
                await TaskFlow.AdvanceDialogAsync(ctx, ct, clicks: 3).ConfigureAwait(false);
                _round++;

                var maxRounds = Math.Clamp(ctx.Config.Tasks.Zhuogui.MaxRounds, 1, 10);
                if (_round >= maxRounds)
                    return StepResult.Complete($"捉鬼已完成 {_round}/{maxRounds} 轮。");

                return advanced
                    ? StepResult.Restart($"捉鬼完成第 {_round}/{maxRounds} 轮，继续下一轮。")
                    : StepResult.Continue("捉鬼战斗/交付阶段未处理到明确状态。");
            }, timeout: TimeSpan.FromMinutes(5), retries: 2),
        ];
    }
}

public sealed class PlotTask : StepTaskBase
{
    public override string Id => "plot";
    public override string Name => "剧情任务";
    public override string Description => "定位任务追踪文字，并推进剧情对话或战斗。";

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("推进可见剧情目标", async (ctx, ct) =>
            {
                var advanced = await TaskFlow.AdvancePlotAsync(ctx, ct, maxCycles: 12, tag: "plot").ConfigureAwait(false);
                return advanced
                    ? StepResult.Complete("剧情推进完成安全循环。")
                    : StepResult.Continue("没有找到可点击的剧情目标、对话或战斗状态。");
            }, timeout: TimeSpan.FromMinutes(5), retries: 2),
        ];
    }
}

public sealed class PatrolTask : StepTaskBase
{
    public override string Id => "patrol";
    public override string Name => "自动巡逻";
    public override string Description => "按固定屏幕点位巡逻，遇到战斗自动处理，并恢复对话/任务追踪。";

    private int _cycles;

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("准备巡逻", (ctx, _) =>
            {
                if (!TaskFlow.EnsureReady(ctx, activate: true))
                    return Task.FromResult(StepResult.Fail("Game window is not bound or cannot be activated."));

                _cycles = 0;
                return Task.FromResult(StepResult.Next("巡逻循环启动。"));
            }, timeout: TimeSpan.FromSeconds(5), retries: 2),

            new("巡逻循环", async (ctx, ct) =>
            {
                var maxCycles = Math.Max(1, ctx.Config.Tasks.Patrol.MaxCycles);
                if (++_cycles > maxCycles)
                    return StepResult.Complete("巡逻达到安全循环上限。");

                var handled = await TaskFlow.HandleImmediateStateAsync(ctx, ct, "patrol").ConfigureAwait(false);
                if (handled)
                    return new StepResult(true, StepTransition.Repeat, $"巡逻第 {_cycles} 轮处理了即时状态。");

                var moved = await TaskFlow.PatrolCyclesAsync(ctx, ct, cycles: 1, "patrol").ConfigureAwait(false);
                return moved
                    ? new StepResult(true, StepTransition.Repeat, $"巡逻第 {_cycles} 轮移动完成。")
                    : StepResult.Continue("巡逻移动失败。");
            }, timeout: TimeSpan.FromSeconds(25), retries: 2),
        ];
    }
}

public sealed class EscortTask : StepTaskBase
{
    public override string Id => "escort";
    public override string Name => "押镖任务";
    public override string Description => "查找镖局/郑镖头入口，接镖后点击追踪护送并在目标 NPC 处交镖。";

    private int _round;
    private bool _accepted;
    private string _targetNpc = string.Empty;

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("接取押镖", async (ctx, ct) =>
            {
                if (!TaskFlow.EnsureReady(ctx, activate: true))
                    return StepResult.Fail("Game window is not bound or cannot be activated.");

                using var image = TaskFlow.CaptureReady(ctx);
                if (TaskFlow.TryClickOcrText(ctx, image, TaskFlow.EscortAcceptKeywords, out var message) ||
                    TaskFlow.TryClickYoloClass(ctx, image, ["escort", "npc", "dialog", "button"], out message))
                {
                    ctx.Log(message);
                    await DelayAsync(800, ct);
                }

                await TaskFlow.AdvanceDialogAsync(ctx, ct, clicks: 5).ConfigureAwait(false);
                _accepted = true;
                return StepResult.Next("已尝试接取押镖。");
            }, timeout: TimeSpan.FromSeconds(25), retries: 3),

            new("识别交付目标", async (ctx, ct) =>
            {
                using var image = TaskFlow.CaptureReady(ctx);
                var text = TaskFlow.ReadQuestTrackerText(ctx, image);
                _targetNpc = TaskFlow.ExtractEscortTarget(text);
                ctx.Log($"[escort] 任务文本='{text}', target='{_targetNpc}'");
                await DelayAsync(300, ct);
                return StepResult.Next();
            }, timeout: TimeSpan.FromSeconds(10), retries: 2),

            new("护送并交镖", async (ctx, ct) =>
            {
                if (!_accepted)
                    return StepResult.Continue("押镖尚未接取。");

                var advanced = await TaskFlow.GoFindOrInteractAsync(ctx, ct, "escort").ConfigureAwait(false);
                var submitted = await TaskFlow.GiveOrSubmitAsync(ctx, ct, "escort").ConfigureAwait(false);
                _round++;

                var maxRounds = Math.Max(1, ctx.Config.Tasks.Escort.MaxRounds);
                if (_round >= maxRounds)
                    return StepResult.Complete($"押镖完成 {_round}/{maxRounds} 轮。");

                _accepted = false;
                return advanced || submitted
                    ? StepResult.Restart($"押镖完成第 {_round}/{maxRounds} 轮，继续下一轮。")
                    : StepResult.Continue("押镖护送/交付阶段未找到可操作目标。");
            }, timeout: TimeSpan.FromMinutes(4), retries: 2),
        ];
    }
}

internal static class TaskFlow
{
    public static readonly string[] ShimenAcceptKeywords = ["师门", "师傅", "师父", "门派", "任务", "领取", "接受"];
    public static readonly string[] ZhongKuiKeywords = ["钟馗", "捉鬼", "地府", "任务", "领取", "接受"];
    public static readonly string[] GhostKeywords = ["鬼", "僵尸", "马面", "牛头", "骷髅", "妖怪", "坐标", "长安", "傲来", "朱紫", "建邺", "东海湾"];
    public static readonly string[] EscortAcceptKeywords = ["押镖", "镖", "郑镖头", "镖银", "四级镖", "普通镖", "领取", "接受", "交付", "送达"];

    private static readonly string[] DoneKeywords = ["已完成", "完成", "已结束", "领取奖励", "任务完成", "已领取", "20/20"];

    private static readonly Dictionary<string, string[]> ShimenTypeKeywords = new(StringComparer.OrdinalIgnoreCase)
    {
        ["combat"] = ["战斗", "击败", "消灭", "打败", "怪物", "妖魔", "示威"],
        ["buy"] = ["购买", "买", "商会", "杂货"],
        ["use"] = ["使用", "给予", "给"],
        ["submit"] = ["上交", "提交", "交给", "献给"],
        ["escort"] = ["护送", "保护"],
        ["deliver"] = ["送信", "传话", "告诉", "通知"],
        ["patrol"] = ["巡逻"],
    };

    public static bool EnsureReady(TaskContext context, bool activate)
    {
        return context.EnsureGameWindow(activate);
    }

    public static Bitmap CaptureReady(TaskContext context)
    {
        if (!EnsureReady(context, activate: false))
            throw new InvalidOperationException("Game window is not bound or cannot be captured.");

        return context.CaptureGameClient();
    }

    public static async Task<bool> AdvancePlotAsync(TaskContext context, CancellationToken cancellationToken, int maxCycles, string tag)
    {
        var acted = false;
        for (var cycle = 1; cycle <= maxCycles; cycle++)
        {
            cancellationToken.ThrowIfCancellationRequested();

            if (await HandleImmediateStateAsync(context, cancellationToken, tag).ConfigureAwait(false))
            {
                acted = true;
                await Task.Delay(600, cancellationToken).ConfigureAwait(false);
                continue;
            }

            using var image = CaptureReady(context);
            if (TryClickQuestObjective(context, image, out var objectiveMessage) ||
                TryClickOcrText(context, image, ["继续", "确定", "任务", "领取", "接受", "交付", "下一步"], out objectiveMessage))
            {
                context.Log($"[{tag}] {objectiveMessage}");
                acted = true;
                await Task.Delay(900, cancellationToken).ConfigureAwait(false);
                continue;
            }

            context.Log($"[{tag}] no plot action in cycle {cycle}/{maxCycles}.");
            await Task.Delay(600, cancellationToken).ConfigureAwait(false);
        }

        return acted;
    }

    public static async Task<bool> GoFightOrInteractAsync(TaskContext context, CancellationToken cancellationToken, string tag)
    {
        var acted = false;
        for (var i = 0; i < 30; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (await HandleImmediateStateAsync(context, cancellationToken, tag).ConfigureAwait(false))
            {
                acted = true;
                await Task.Delay(700, cancellationToken).ConfigureAwait(false);
                continue;
            }

            using var image = CaptureReady(context);
            if (TryClickYoloClass(context, image, ["monster", "ghost", "npc"], out var targetMessage) ||
                TryClickOcrText(context, image, GhostKeywords.Concat(["战斗", "妖怪", "怪物"]).ToArray(), out targetMessage) ||
                TryClickQuestObjective(context, image, out targetMessage))
            {
                context.Log($"[{tag}] {targetMessage}");
                acted = true;
                await Task.Delay(1400, cancellationToken).ConfigureAwait(false);
                continue;
            }

            if (acted)
                break;

            await Task.Delay(600, cancellationToken).ConfigureAwait(false);
        }

        return acted;
    }

    public static async Task<bool> GoFindOrInteractAsync(TaskContext context, CancellationToken cancellationToken, string tag)
    {
        var acted = false;
        for (var i = 0; i < 24; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (await HandleImmediateStateAsync(context, cancellationToken, tag).ConfigureAwait(false))
            {
                acted = true;
                continue;
            }

            using var image = CaptureReady(context);
            if (TryClickQuestObjective(context, image, out var message) ||
                TryClickOcrText(context, image, ["交给", "送达", "交付", "给予", "任务", "继续", "确定"], out message))
            {
                context.Log($"[{tag}] {message}");
                acted = true;
                await Task.Delay(1200, cancellationToken).ConfigureAwait(false);
                continue;
            }

            if (acted)
                break;

            await Task.Delay(700, cancellationToken).ConfigureAwait(false);
        }

        return acted;
    }

    public static async Task<bool> GiveOrSubmitAsync(TaskContext context, CancellationToken cancellationToken, string tag)
    {
        var acted = await HandleImmediateStateAsync(context, cancellationToken, tag).ConfigureAwait(false);
        context.Input.Hotkey("alt", "g");
        await Task.Delay(900, cancellationToken).ConfigureAwait(false);

        using var image = CaptureReady(context);
        if (TryClickOcrText(context, image, ["给予", "上交", "提交", "交付", "镖银", "物品", "确定"], out var message) ||
            TryClickYoloClass(context, image, ["item", "button", "dialog"], out message))
        {
            context.Log($"[{tag}] {message}");
            acted = true;
            await Task.Delay(700, cancellationToken).ConfigureAwait(false);
        }

        await AdvanceDialogAsync(context, cancellationToken, clicks: 3).ConfigureAwait(false);
        return acted;
    }

    public static async Task<bool> PatrolCyclesAsync(TaskContext context, CancellationToken cancellationToken, int cycles, string tag)
    {
        var moved = false;
        for (var i = 0; i < cycles; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (await HandleImmediateStateAsync(context, cancellationToken, tag).ConfigureAwait(false))
                continue;

            using var image = CaptureReady(context);
            var point = GetSafePatrolPoint(image, Math.Abs(Environment.TickCount / 1000) + i);
            if (!context.ClickClient(point, variance: 16))
                return moved;

            moved = true;
            await Task.Delay(1500, cancellationToken).ConfigureAwait(false);
        }

        return moved;
    }

    public static async Task<bool> HandleImmediateStateAsync(TaskContext context, CancellationToken cancellationToken, string tag)
    {
        if (!EnsureReady(context, activate: false))
            return false;

        using var image = context.CaptureGameClient();
        var state = context.States?.Detect(image);
        if (state is not null && state.State != GameState.Unknown)
            context.Log($"[{tag}] state={state.State} via {state.Method} ({state.Confidence:0.00})");

        if (state?.State == GameState.Battle || context.Colors.HasBattleUi(image))
        {
            if (context.Battle is not null && await context.Battle.HandleAsync(context, cancellationToken).ConfigureAwait(false))
                return true;

            context.Log($"[{tag}] detected battle but no battle handler completed it.");
            return false;
        }

        if (state?.State == GameState.Dialog || context.Colors.HasDialog(image))
        {
            await AdvanceDialogAsync(context, cancellationToken).ConfigureAwait(false);
            return true;
        }

        return false;
    }

    public static bool TryClickQuestObjective(TaskContext context, Bitmap image, out string message)
    {
        var region = GetTaskTrackerRegion(context, image);
        var redCenter = context.Colors.FindRedTextCenter(image, region);
        var ocrCandidate = FindOcrObjective(context, image, region);
        var target = redCenter ?? ocrCandidate?.BBox.Center;
        if (target is null)
        {
            message = "No quest tracker target found.";
            return false;
        }

        var adjusted = AdjustClickPoint(target.Value, 0);
        var label = string.IsNullOrWhiteSpace(ocrCandidate?.Text) ? "red quest text" : ocrCandidate.Text.Trim();
        if (!context.ClickClient(adjusted, variance: 4))
        {
            message = $"Quest target click rejected: {adjusted.X},{adjusted.Y}.";
            return false;
        }

        message = $"Clicked quest objective '{label}' at client={adjusted.X},{adjusted.Y}.";
        return true;
    }

    public static bool TryClickFeature(TaskContext context, Bitmap image, IReadOnlyList<string> featureNames, out string message)
    {
        foreach (var featureName in featureNames.Where(name => !string.IsNullOrWhiteSpace(name)))
        {
            var match = context.ColorFeatures is MultiColorFeatureDetector detector ? detector.Find(image, featureName) : null;
            if (match is null)
                continue;

            if (!context.ClickClient(match.Point, variance: 5))
            {
                message = $"Feature click rejected: {featureName}.";
                return false;
            }

            message = $"Clicked color feature '{featureName}' score={match.Score:0.00} at client={match.Point.X},{match.Point.Y}.";
            return true;
        }

        message = "No color feature matched.";
        return false;
    }
    public static bool TryClickOcrText(TaskContext context, Bitmap image, IReadOnlyList<string> keywords, out string message)
    {
        var normalizedKeywords = keywords.Where(keyword => !string.IsNullOrWhiteSpace(keyword)).ToArray();
        var candidates = context.Ocr.Recognize(image)
            .Where(result => !string.IsNullOrWhiteSpace(result.Text))
            .Select(result => (Result: result, Text: result.Text.Trim()))
            .Where(item => normalizedKeywords.Any(keyword => item.Text.Contains(keyword, StringComparison.OrdinalIgnoreCase)))
            .OrderByDescending(item => item.Result.Confidence)
            .ToArray();

        var best = candidates.FirstOrDefault();
        if (best.Result is null)
        {
            message = $"No OCR text matched: {string.Join(",", normalizedKeywords)}.";
            return false;
        }

        if (!context.ClickClient(best.Result.BBox.Center, variance: 5))
        {
            message = $"OCR target click rejected: '{best.Text}'.";
            return false;
        }

        message = $"Clicked OCR text '{best.Text}' at client={best.Result.BBox.Center.X},{best.Result.BBox.Center.Y}.";
        return true;
    }

    public static bool TryClickYoloClass(TaskContext context, Bitmap image, IReadOnlyList<string> classNames, out string message)
    {
        if (!context.Yolo.IsAvailable)
        {
            message = "YOLO detector is not available.";
            return false;
        }

        var detections = context.Yolo.Detect(image)
            .Where(detection => classNames.Any(name => detection.ClassName.Contains(name, StringComparison.OrdinalIgnoreCase)))
            .OrderByDescending(detection => detection.Confidence)
            .ToArray();

        var best = detections.FirstOrDefault();
        if (best is null)
        {
            message = $"No YOLO class matched: {string.Join(",", classNames)}.";
            return false;
        }

        if (!context.ClickClient(best.Center, variance: 8))
        {
            message = $"YOLO target click rejected: {best.ClassName}.";
            return false;
        }

        message = $"Clicked YOLO target '{best.ClassName}' ({best.Confidence:0.00}) at client={best.Center.X},{best.Center.Y}.";
        return true;
    }

    public static bool TryClickTemplate(TaskContext context, Bitmap image, string templateName, double threshold, out string message)
    {
        var path = ResolveTemplatePath(context, templateName);
        if (path is null)
        {
            message = $"Template not found: {templateName}.";
            return false;
        }

        var match = context.Templates.MatchBest(image, path, threshold);
        if (match is null)
        {
            message = $"Template did not match: {Path.GetFileName(path)}.";
            return false;
        }

        if (!context.ClickClient(match.Center, variance: 5))
        {
            message = $"Template click rejected: {match.TemplateName}.";
            return false;
        }

        message = $"Clicked template '{match.TemplateName}' score={match.Score:0.00} at client={match.Center.X},{match.Center.Y}.";
        return true;
    }

    public static string ReadQuestTrackerText(TaskContext context, Bitmap image)
    {
        var region = GetTaskTrackerRegion(context, image);
        var results = context.Ocr.Recognize(image, region)
            .Where(result => !string.IsNullOrWhiteSpace(result.Text))
            .Select(result => result.Text.Trim());
        return string.Join(" ", results);
    }

    public static string IdentifyShimenTaskType(string text)
    {
        foreach (var (type, keywords) in ShimenTypeKeywords)
        {
            if (keywords.Any(keyword => text.Contains(keyword, StringComparison.OrdinalIgnoreCase)))
                return type;
        }

        return "unknown";
    }

    public static string ExtractEscortTarget(string text)
    {
        foreach (var keyword in new[] { "交给", "送至", "送给", "交付给", "送达" })
        {
            var index = text.IndexOf(keyword, StringComparison.OrdinalIgnoreCase);
            if (index < 0)
                continue;

            var start = index + keyword.Length;
            var length = Math.Min(8, Math.Max(0, text.Length - start));
            return text.Substring(start, length).Trim();
        }

        return string.Empty;
    }

    public static PointI GetSafePatrolPoint(Bitmap image, int cycle)
    {
        var points = new[]
        {
            new PointI((int)(image.Width * 0.35), (int)(image.Height * 0.42)),
            new PointI((int)(image.Width * 0.65), (int)(image.Height * 0.42)),
            new PointI((int)(image.Width * 0.62), (int)(image.Height * 0.68)),
            new PointI((int)(image.Width * 0.38), (int)(image.Height * 0.68)),
        };

        return points[Math.Abs(cycle) % points.Length];
    }

    public static async Task AdvanceDialogAsync(TaskContext context, CancellationToken cancellationToken, int clicks = 8)
    {
        using var image = context.CaptureGameClient();
        var point = new PointI(image.Width / 2, (int)(image.Height * 0.86));
        for (var i = 0; i < clicks; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            context.ClickClient(point, variance: 8);
            await Task.Delay(350, cancellationToken).ConfigureAwait(false);
        }
    }

    private static RectI GetTaskTrackerRegion(TaskContext context, Bitmap image)
    {
        return context.Config.Regions.TryGetValue("task_tracker", out var configured)
            ? configured
            : new RectI((int)(image.Width * 0.62), 0, image.Width, (int)(image.Height * 0.55));
    }

    private static OcrResult? FindOcrObjective(TaskContext context, Bitmap image, RectI region)
    {
        return context.Ocr.Recognize(image, region)
            .Where(result => !string.IsNullOrWhiteSpace(result.Text))
            .Where(result => result.Text.Trim().Length >= 2)
            .Where(result => !IsDoneText(result.Text))
            .Where(result => !(result.Text.All(char.IsDigit) && result.Text.Length > 3))
            .OrderByDescending(ScoreOcrCandidate)
            .FirstOrDefault();
    }

    private static double ScoreOcrCandidate(OcrResult result)
    {
        var text = result.Text.Trim();
        var score = result.Confidence;
        if (text.Length is >= 2 and <= 12)
            score += 2;
        if (text.Any(c => c >= '\u4e00' && c <= '\u9fff'))
            score += 3;
        if (ShimenTypeKeywords.Values.SelectMany(static keywords => keywords).Any(keyword => text.Contains(keyword, StringComparison.OrdinalIgnoreCase)))
            score += 2;
        score += result.BBox.Center.Y / 1000.0;
        return score;
    }

    private static bool IsDoneText(string text)
    {
        return DoneKeywords.Any(keyword => text.Contains(keyword, StringComparison.OrdinalIgnoreCase));
    }

    private static PointI AdjustClickPoint(PointI point, int retry)
    {
        var offsets = new[]
        {
            new PointI(8, -2),
            new PointI(0, -4),
            new PointI(14, 0),
            new PointI(-6, -6),
            new PointI(0, 2),
        };
        var offset = offsets[Math.Min(retry, offsets.Length - 1)];
        return new PointI(point.X + offset.X, point.Y + offset.Y);
    }

    private static string? ResolveTemplatePath(TaskContext context, string templateName)
    {
        if (string.IsNullOrWhiteSpace(templateName))
            return null;

        var candidates = new List<string>();
        if (Path.IsPathRooted(templateName))
            candidates.Add(templateName);
        else
        {
            candidates.Add(templateName);
            candidates.Add(Path.Combine(context.Config.SceneDetection.TemplateDir, templateName));
            candidates.Add(Path.Combine("data", "templates", "tasks", templateName));
            candidates.Add(Path.Combine("data", "templates", "npc", templateName));
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
