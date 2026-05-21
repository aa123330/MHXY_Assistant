namespace MhxyAssistant.Core.Services;

public interface ICloudStorage
{
    Task<CloudResponse> CheckHealthAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<CloudFileInfo>> ListFilesAsync(CancellationToken cancellationToken = default);
    Task<CloudResponse> UploadAsync(string localPath, string? remoteName = null, CancellationToken cancellationToken = default);
    Task<string?> DownloadAsync(string remoteName, string saveDirectory, CancellationToken cancellationToken = default);
    Task<CloudResponse> DeleteAsync(string remoteName, CancellationToken cancellationToken = default);
}

public sealed record CloudResponse(bool Ok, string? Error = null);

public sealed record CloudFileInfo(string Name, long Size = 0, DateTimeOffset? ModifiedAt = null);
