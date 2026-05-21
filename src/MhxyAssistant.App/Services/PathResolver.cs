using System.IO;

namespace MhxyAssistant.App.Services;

public static class PathResolver
{
    public static string ResolveFile(string path)
    {
        if (string.IsNullOrWhiteSpace(path) || Path.IsPathRooted(path))
            return path;

        foreach (var root in CandidateRoots())
        {
            var candidate = Path.GetFullPath(Path.Combine(root, path));
            if (File.Exists(candidate))
                return candidate;
        }

        return Path.GetFullPath(path);
    }

    public static string ResolveDirectory(string path)
    {
        if (string.IsNullOrWhiteSpace(path) || Path.IsPathRooted(path))
            return path;

        foreach (var root in CandidateRoots())
        {
            var candidate = Path.GetFullPath(Path.Combine(root, path));
            if (Directory.Exists(candidate))
                return candidate;
        }

        return Path.GetFullPath(path);
    }

    public static string FindWorkspaceRoot()
    {
        foreach (var root in CandidateRoots())
        {
            if (File.Exists(Path.Combine(root, "config.yaml")) || Directory.Exists(Path.Combine(root, "tools", "ml")))
                return root;
        }

        return Directory.GetCurrentDirectory();
    }

    private static IEnumerable<string> CandidateRoots()
    {
        yield return Directory.GetCurrentDirectory();
        yield return AppContext.BaseDirectory;

        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            yield return dir.FullName;
            dir = dir.Parent;
        }
    }
}
