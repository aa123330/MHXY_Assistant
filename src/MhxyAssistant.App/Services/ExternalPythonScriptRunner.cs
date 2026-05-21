using System.Diagnostics;
using System.IO;
using System.Text;

namespace MhxyAssistant.App.Services;

public sealed class ExternalPythonScriptRunner
{
    public async Task<int> RunAsync(
        string pythonExecutable,
        string scriptPath,
        IEnumerable<string> arguments,
        string workingDirectory,
        Action<string> onOutput,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(pythonExecutable))
            pythonExecutable = "python";

        var resolvedScript = PathResolver.ResolveFile(scriptPath);
        if (!File.Exists(resolvedScript))
            throw new FileNotFoundException("Python script not found.", resolvedScript);

        var startInfo = new ProcessStartInfo
        {
            FileName = pythonExecutable,
            WorkingDirectory = string.IsNullOrWhiteSpace(workingDirectory) ? PathResolver.FindWorkspaceRoot() : workingDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };

        startInfo.ArgumentList.Add(resolvedScript);
        foreach (var argument in arguments)
            startInfo.ArgumentList.Add(argument);

        using var process = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
        process.OutputDataReceived += (_, e) => AppendLine(e.Data, onOutput);
        process.ErrorDataReceived += (_, e) => AppendLine(e.Data, onOutput);

        if (!process.Start())
            throw new InvalidOperationException("Failed to start Python process.");

        onOutput($"$ {pythonExecutable} {Quote(resolvedScript)} {string.Join(" ", arguments.Select(Quote))}");
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        await using var registration = cancellationToken.Register(() =>
        {
            try
            {
                if (!process.HasExited)
                    process.Kill(entireProcessTree: true);
            }
            catch (InvalidOperationException)
            {
            }
        });

        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        return process.ExitCode;
    }

    private static void AppendLine(string? line, Action<string> onOutput)
    {
        if (!string.IsNullOrWhiteSpace(line))
            onOutput(line);
    }

    private static string Quote(string value)
    {
        return value.Contains(' ') ? $"\"{value}\"" : value;
    }
}
