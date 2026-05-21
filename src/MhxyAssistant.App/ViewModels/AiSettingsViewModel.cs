using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using MhxyAssistant.App.Services;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.App.ViewModels;

public sealed class AiSettingsViewModel : INotifyPropertyChanged
{
    private readonly UiSettingsStore _store = new();
    private readonly OpenAiCompatibleClient _client = new();
    private readonly UiSettings _settings;
    private bool _enabled;
    private string _provider;
    private string _baseUrl;
    private string _model;
    private string _apiKeyPlaceholder;
    private string _testMessage = "Say OK in one short sentence.";
    private string _chatResponse = "";
    private bool _isBusy;
    private string _statusText = "Ready";

    public AiSettingsViewModel(AppConfig config)
    {
        _settings = _store.Load();
        _enabled = _settings.Ai.Enabled;
        _provider = string.IsNullOrWhiteSpace(_settings.Ai.Provider) ? config.Ai.Provider : _settings.Ai.Provider;
        _baseUrl = string.IsNullOrWhiteSpace(_settings.Ai.BaseUrl) ? config.Ai.OpenAi.BaseUrl : _settings.Ai.BaseUrl;
        _model = string.IsNullOrWhiteSpace(_settings.Ai.Model) ? config.Ai.OpenAi.Model : _settings.Ai.Model;
        _apiKeyPlaceholder = string.IsNullOrWhiteSpace(_settings.Ai.ApiKeyPlaceholder)
            ? config.Ai.OpenAi.ApiKey
            : _settings.Ai.ApiKeyPlaceholder;

        SaveCommand = new RelayCommand(_ => Save());
        TestCommand = new RelayCommand(async _ => await TestConnectionAsync(), _ => !IsBusy);
        ChatTestCommand = new RelayCommand(async _ => await ChatTestAsync(), _ => !IsBusy);
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ICommand SaveCommand { get; }
    public ICommand TestCommand { get; }
    public ICommand ChatTestCommand { get; }

    public bool Enabled
    {
        get => _enabled;
        set => SetField(ref _enabled, value);
    }

    public string Provider
    {
        get => _provider;
        set => SetField(ref _provider, value);
    }

    public string BaseUrl
    {
        get => _baseUrl;
        set => SetField(ref _baseUrl, value);
    }

    public string Model
    {
        get => _model;
        set => SetField(ref _model, value);
    }

    public string ApiKeyPlaceholder
    {
        get => _apiKeyPlaceholder;
        set => SetField(ref _apiKeyPlaceholder, value);
    }

    public string TestMessage
    {
        get => _testMessage;
        set => SetField(ref _testMessage, value);
    }

    public string ChatResponse
    {
        get => _chatResponse;
        private set => SetField(ref _chatResponse, value);
    }

    public bool IsBusy
    {
        get => _isBusy;
        private set
        {
            if (SetField(ref _isBusy, value))
            {
                (TestCommand as RelayCommand)?.RaiseCanExecuteChanged();
                (ChatTestCommand as RelayCommand)?.RaiseCanExecuteChanged();
            }
        }
    }

    public string StatusText
    {
        get => _statusText;
        private set => SetField(ref _statusText, value);
    }

    private void Save()
    {
        _settings.Ai.Enabled = Enabled;
        _settings.Ai.Provider = Provider;
        _settings.Ai.BaseUrl = BaseUrl;
        _settings.Ai.Model = Model;
        _settings.Ai.ApiKeyPlaceholder = ApiKeyPlaceholder;
        var path = _store.Save(_settings);
        StatusText = $"Saved AI settings: {path}";
    }

    private async Task TestConnectionAsync()
    {
        await RunAiOperationAsync(async apiKey =>
        {
            var result = await _client.TestConnectionAsync(BaseUrl, apiKey, CancellationToken.None);
            StatusText = result == "OK" ? "Connection OK." : $"Connection failed: {result}";
        });
    }

    private async Task ChatTestAsync()
    {
        await RunAiOperationAsync(async apiKey =>
        {
            ChatResponse = await _client.SendChatAsync(BaseUrl, apiKey, Model, TestMessage, CancellationToken.None);
            StatusText = "Chat test completed.";
        });
    }

    private async Task RunAiOperationAsync(Func<string, Task> operation)
    {
        if (IsBusy)
            return;

        Save();
        IsBusy = true;
        try
        {
            var apiKey = OpenAiCompatibleClient.ResolveApiKey(ApiKeyPlaceholder);
            if (string.IsNullOrWhiteSpace(apiKey) && BaseUrl.Contains("openai.com", StringComparison.OrdinalIgnoreCase))
            {
                StatusText = "Missing API key.";
                return;
            }

            await operation(apiKey);
        }
        catch (Exception ex)
        {
            StatusText = $"AI test failed: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private bool SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }
}
