using MhxyAssistant.Core.Services;

namespace MhxyAssistant.Core.Tasks;

public sealed class ShimenTask : StepTaskBase
{
    public override string Id => "shimen";
    public override string Name => "师门任务";
    public override string Description => "迁移目标：F8 回师门、模板找师傅、OCR 分类、20 轮任务。";

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("F8 回师门", async (ctx, ct) =>
            {
                ctx.Input.Hotkey("f8");
                await DelayAsync(1000, ct);
                return StepResult.Next();
            }, timeout: TimeSpan.FromSeconds(5), retries: 2),
            new("师门流程占位", (ctx, _) =>
            {
                ctx.Log("[迁移占位] 师门任务流程将在 C# 状态机中逐步补齐。");
                return Task.FromResult(StepResult.Complete());
            }),
        ];
    }
}

public sealed class ZhuoguiTask : StepTaskBase
{
    public override string Id => "zhuogui";
    public override string Name => "捉鬼任务";
    public override string Description => "迁移目标：钟馗、天眼、找鬼、战斗、交任务。";

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("使用天眼通符", async (ctx, ct) =>
            {
                ctx.Input.Hotkey("alt", "t");
                await DelayAsync(1000, ct);
                return StepResult.Next();
            }, timeout: TimeSpan.FromSeconds(5), retries: 2),
            new("捉鬼流程占位", (ctx, _) =>
            {
                ctx.Log("[迁移占位] 捉鬼任务流程将在 C# 状态机中逐步补齐。");
                return Task.FromResult(StepResult.Complete());
            }),
        ];
    }
}

public sealed class PlotTask : StepTaskBase
{
    public override string Id => "plot";
    public override string Name => "剧情任务";
    public override string Description => "迁移目标：红字/OCR 定位任务追踪栏并推进剧情。";

    protected override IReadOnlyList<TaskStep> BuildSteps(TaskContext context)
    {
        return
        [
            new("扫描任务追踪栏红字", (ctx, _) =>
            {
                if (ctx.GameHwnd == nint.Zero)
                    return Task.FromResult(StepResult.Continue("尚未绑定游戏窗口。"));

                using var image = ctx.Capture.CaptureClient(ctx.GameHwnd);
                var region = new Models.RectI((int)(image.Width * 0.62), 0, image.Width, (int)(image.Height * 0.55));
                var center = ctx.Colors.FindRedTextCenter(image, region);
                if (center is null)
                    return Task.FromResult(StepResult.Continue("未找到可点击的任务红字。"));

                ctx.Input.Click(center.Value);
                return Task.FromResult(StepResult.Next($"已点击任务目标：{center.Value.X},{center.Value.Y}"));
            }, timeout: TimeSpan.FromSeconds(10), retries: 3),
            new("等待交互或到达", async (ctx, ct) =>
            {
                await DelayAsync(1500, ct);
                if (ctx.GameHwnd == nint.Zero)
                    return StepResult.Continue();

                using var image = ctx.Capture.CaptureClient(ctx.GameHwnd);
                if (ctx.Colors.HasDialog(image) || ctx.Colors.HasBattleUi(image))
                    return StepResult.Complete("剧情任务已进入对话或战斗处理点。");

                return StepResult.Restart("继续扫描任务追踪栏。");
            }, timeout: TimeSpan.FromSeconds(20), retries: 2),
        ];
    }
}

public sealed class PatrolTask : AssistantTaskBase
{
    public override string Id => "patrol";
    public override string Name => "自动巡逻";
    public override string Description => "迁移目标：巡逻点循环、遇怪战斗、补给检查。";

    protected override Task ExecuteAsync(TaskContext context, CancellationToken cancellationToken)
    {
        context.Log("[迁移占位] 自动巡逻流程将在 C# 状态机中逐步补齐。");
        return Task.CompletedTask;
    }
}

public sealed class EscortTask : AssistantTaskBase
{
    public override string Id => "escort";
    public override string Name => "押镖任务";
    public override string Description => "迁移目标：接镖、护送、战斗、交镖。";

    protected override Task ExecuteAsync(TaskContext context, CancellationToken cancellationToken)
    {
        context.Log("[迁移占位] 押镖任务流程将在 C# 状态机中逐步补齐。");
        return Task.CompletedTask;
    }
}
