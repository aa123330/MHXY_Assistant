using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace MhxyAssistant.Core.Services;

public sealed class HttpCloudStorage : ICloudStorage, IDisposable
{
    private readonly HttpClient _client;
    private readonly bool _ownsClient;

    public HttpCloudStorage(string serverUrl, HttpClient? client = null)
    {
        _ownsClient = client is null;
        _client = client ?? new HttpClient { Timeout = TimeSpan.FromSeconds(120) };
        _client.BaseAddress = new Uri(serverUrl.TrimEnd('/') + "/");
    }

    public async Task<CloudResponse> CheckHealthAsync(CancellationToken cancellationToken = default)
    {
        return await GetResponseAsync("api/health", cancellationToken).ConfigureAwait(false);
    }

    public async Task<IReadOnlyList<CloudFileInfo>> ListFilesAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _client.GetAsync("api/list", cancellationToken).ConfigureAwait(false);
            if (!response.IsSuccessStatusCode)
                return [];

            var payload = await response.Content.ReadFromJsonAsync<CloudListPayload>(cancellationToken).ConfigureAwait(false);
            return payload?.Files?
                .Select(f => new CloudFileInfo(f.GetName(), f.GetSizeBytes(), ParseTime(f.GetModifiedAt())))
                .Where(f => !string.IsNullOrWhiteSpace(f.Name))
                .ToArray() ?? [];
        }
        catch
        {
            return [];
        }
    }

    public async Task<CloudResponse> UploadAsync(string localPath, string? remoteName = null, CancellationToken cancellationToken = default)
    {
        if (!File.Exists(localPath))
            return new CloudResponse(false, $"File not found: {localPath}");

        await using var file = File.OpenRead(localPath);
        using var content = new MultipartFormDataContent();
        content.Add(new StreamContent(file), "file", remoteName ?? Path.GetFileName(localPath));

        try
        {
            using var response = await _client.PostAsync("api/upload", content, cancellationToken).ConfigureAwait(false);
            return await ToCloudResponseAsync(response, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            return new CloudResponse(false, ex.Message);
        }
    }

    public async Task<string?> DownloadAsync(string remoteName, string saveDirectory, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(saveDirectory);
        var savePath = Path.Combine(saveDirectory, remoteName);

        try
        {
            await using var stream = await _client.GetStreamAsync($"api/download/{Uri.EscapeDataString(remoteName)}", cancellationToken).ConfigureAwait(false);
            await using var file = File.Create(savePath);
            await stream.CopyToAsync(file, cancellationToken).ConfigureAwait(false);
            return savePath;
        }
        catch
        {
            return null;
        }
    }

    public async Task<CloudResponse> DeleteAsync(string remoteName, CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _client.DeleteAsync($"api/delete/{Uri.EscapeDataString(remoteName)}", cancellationToken).ConfigureAwait(false);
            return await ToCloudResponseAsync(response, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            return new CloudResponse(false, ex.Message);
        }
    }

    public void Dispose()
    {
        if (_ownsClient)
            _client.Dispose();
    }

    private async Task<CloudResponse> GetResponseAsync(string path, CancellationToken cancellationToken)
    {
        try
        {
            using var response = await _client.GetAsync(path, cancellationToken).ConfigureAwait(false);
            return await ToCloudResponseAsync(response, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            return new CloudResponse(false, ex.Message);
        }
    }

    private static async Task<CloudResponse> ToCloudResponseAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        if (!response.IsSuccessStatusCode)
            return new CloudResponse(false, $"{(int)response.StatusCode} {response.ReasonPhrase}");

        try
        {
            var payload = await response.Content.ReadFromJsonAsync<CloudResponsePayload>(cancellationToken).ConfigureAwait(false);
            return new CloudResponse(payload?.Ok ?? true, payload?.Error);
        }
        catch (JsonException)
        {
            return new CloudResponse(true);
        }
    }

    private static DateTimeOffset? ParseTime(string? value)
    {
        return DateTimeOffset.TryParse(value, out var parsed) ? parsed : null;
    }

    private sealed class CloudResponsePayload
    {
        public bool? Ok { get; set; }
        public string? Error { get; set; }
    }

    private sealed class CloudListPayload
    {
        public List<CloudFilePayload>? Files { get; set; }
    }

    private sealed class CloudFilePayload
    {
        [JsonPropertyName("name")]
        public string? Name { get; set; }

        [JsonPropertyName("filename")]
        public string? FileName { get; set; }

        [JsonPropertyName("size")]
        public long? Size { get; set; }

        [JsonPropertyName("size_mb")]
        public double? SizeMb { get; set; }

        [JsonPropertyName("modified_at")]
        public string? ModifiedAt { get; set; }

        [JsonPropertyName("date")]
        public string? Date { get; set; }

        public string GetName() => Name ?? FileName ?? "";

        public long GetSizeBytes()
        {
            if (Size is { } bytes)
                return bytes;
            if (SizeMb is { } mb)
                return (long)(mb * 1024 * 1024);
            return 0;
        }

        public string? GetModifiedAt() => ModifiedAt ?? Date;
    }
}
