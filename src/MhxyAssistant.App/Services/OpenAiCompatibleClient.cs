using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json.Serialization;

namespace MhxyAssistant.App.Services;

public sealed class OpenAiCompatibleClient
{
    private readonly HttpClient _client = new() { Timeout = TimeSpan.FromSeconds(60) };

    public async Task<string> TestConnectionAsync(string baseUrl, string apiKey, CancellationToken cancellationToken)
    {
        var url = Combine(baseUrl, "models");
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        AddAuth(request, apiKey);

        using var response = await _client.SendAsync(request, cancellationToken).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
            return $"{(int)response.StatusCode} {response.ReasonPhrase}";

        return "OK";
    }

    public async Task<string> SendChatAsync(string baseUrl, string apiKey, string model, string message, CancellationToken cancellationToken)
    {
        var url = Combine(baseUrl, "chat/completions");
        using var request = new HttpRequestMessage(HttpMethod.Post, url);
        AddAuth(request, apiKey);
        request.Content = JsonContent.Create(new ChatRequest(
            model,
            new[]
            {
                new ChatMessage("system", "You are a concise assistant for connection testing."),
                new ChatMessage("user", string.IsNullOrWhiteSpace(message) ? "Reply with a short OK." : message),
            },
            Stream: false));

        using var response = await _client.SendAsync(request, cancellationToken).ConfigureAwait(false);
        var payload = await response.Content.ReadFromJsonAsync<ChatResponse>(cancellationToken).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
            return payload?.Error?.Message ?? $"{(int)response.StatusCode} {response.ReasonPhrase}";

        return payload?.Choices?.FirstOrDefault()?.Message?.Content?.Trim() ?? "(empty response)";
    }

    public static string ResolveApiKey(string value)
    {
        if (value.StartsWith("${", StringComparison.Ordinal) && value.EndsWith("}", StringComparison.Ordinal))
        {
            var name = value[2..^1];
            return Environment.GetEnvironmentVariable(name) ?? string.Empty;
        }

        return value;
    }

    private static void AddAuth(HttpRequestMessage request, string apiKey)
    {
        if (!string.IsNullOrWhiteSpace(apiKey))
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
    }

    private static string Combine(string baseUrl, string path)
    {
        return $"{baseUrl.TrimEnd('/')}/{path.TrimStart('/')}";
    }

    private sealed record ChatRequest(
        [property: JsonPropertyName("model")] string Model,
        [property: JsonPropertyName("messages")] IReadOnlyList<ChatMessage> Messages,
        [property: JsonPropertyName("stream")] bool Stream);

    private sealed record ChatMessage(
        [property: JsonPropertyName("role")] string Role,
        [property: JsonPropertyName("content")] string Content);

    private sealed class ChatResponse
    {
        [JsonPropertyName("choices")]
        public List<ChatChoice>? Choices { get; set; }

        [JsonPropertyName("error")]
        public ChatError? Error { get; set; }
    }

    private sealed class ChatChoice
    {
        [JsonPropertyName("message")]
        public ChatMessage? Message { get; set; }
    }

    private sealed class ChatError
    {
        [JsonPropertyName("message")]
        public string? Message { get; set; }
    }
}
