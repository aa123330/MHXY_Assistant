using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;

namespace MhxyAssistant.App;

public partial class App : Application
{
    private static readonly string StartupLogPath = Path.Combine(AppContext.BaseDirectory, "debug", "startup.log");

    protected override void OnStartup(StartupEventArgs e)
    {
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
        TaskScheduler.UnobservedTaskException += OnUnobservedTaskException;
        base.OnStartup(e);
    }

    private void Application_Startup(object sender, StartupEventArgs e)
    {
        try
        {
            var window = new MainWindow();
            window.Show();
        }
        catch (Exception ex)
        {
            ReportStartupFailure(ex, handled: false);
            Shutdown(-1);
        }
    }

    private static void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        ReportStartupFailure(e.Exception, handled: true);
        e.Handled = true;
        Current.Shutdown(-1);
    }

    private static void OnUnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        ReportStartupFailure(e.ExceptionObject as Exception ?? new InvalidOperationException(e.ExceptionObject?.ToString()), handled: false);
    }

    private static void OnUnobservedTaskException(object? sender, UnobservedTaskExceptionEventArgs e)
    {
        ReportStartupFailure(e.Exception, handled: true);
        e.SetObserved();
    }

    private static void ReportStartupFailure(Exception? exception, bool handled)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(StartupLogPath)!);
            File.AppendAllText(
                StartupLogPath,
                $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] handled={handled}{Environment.NewLine}{exception}{Environment.NewLine}{Environment.NewLine}");
        }
        catch
        {
            // Keep the original startup failure visible even if logging is unavailable.
        }

        MessageBox.Show(
            $"MHXY Assistant 启动失败，错误日志已写入：{Environment.NewLine}{StartupLogPath}{Environment.NewLine}{Environment.NewLine}{exception?.Message}",
            "启动失败",
            MessageBoxButton.OK,
            MessageBoxImage.Error);
    }
}