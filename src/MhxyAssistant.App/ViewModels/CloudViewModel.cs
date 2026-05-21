using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using MhxyAssistant.App.Services;
using MhxyAssistant.Core.Models;
using MhxyAssistant.Core.Services;

namespace MhxyAssistant.App.ViewModels;

public sealed class CloudViewModel : INotifyPropertyChanged
{
    private readonly UiSettingsStore _store = new();
    private readonly UiSettings _settings;
    private string _serverUrl;
    private string _uploadPath;
    private string _downloadDirectory;
    private CloudServerItem? _selectedItem;
    private bool _isBusy;
    private string _statusText = "Ready";

    public CloudViewModel(AppConfig config)
    {
        _settings = _store.Load();
        _serverUrl = string.IsNullOrWhiteSpace(_settings.Cloud.ServerUrl) ? config.CloudTrain.ServerUrl : _settings.Cloud.ServerUrl;
        _uploadPath = string.IsNullOrWhiteSpace(_settings.Cloud.UploadPath) ? "tools/ml/data.yaml" : _settings.Cloud.UploadPath;
        _downloadDirectory = string.IsNullOrWhiteSpace(_settings.Cloud.DownloadDirectory) ? "downloads" : _settings.Cloud.DownloadDirectory;

        ServerItems = new ObservableCollection<CloudServerItem>();
        SaveCommand = new RelayCommand(_ => Save());
        RefreshCommand = new RelayCommand(async _ => await RefreshAsync(), _ => !IsBusy);
        UploadCommand = new RelayCommand(async _ => await UploadAsync(), _ => !IsBusy);
        DownloadCommand = new RelayCommand(async _ => await DownloadAsync(), _ => !IsBusy && SelectedItem is not null);
        DeleteCommand = new RelayCommand(async _ => await DeleteAsync(), _ => !IsBusy && SelectedItem is not null);
        HealthCommand = new RelayCommand(async _ => await CheckHealthAsync(), _ => !IsBusy);
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<CloudServerItem> ServerItems { get; }
    public ICommand SaveCommand { get; }
    public ICommand RefreshCommand { get; }
    public ICommand UploadCommand { get; }
    public ICommand DownloadCommand { get; }
    public ICommand DeleteCommand { get; }
    public ICommand HealthCommand { get; }

    public string ServerUrl
    {
        get => _serverUrl;
        set => SetField(ref _serverUrl, value);
    }

    public string UploadPath
    {
        get => _uploadPath;
        set => SetField(ref _uploadPath, value);
    }

    public string DownloadDirectory
    {
        get => _downloadDirectory;
        set => SetField(ref _downloadDirectory, value);
    }

    public CloudServerItem? SelectedItem
    {
        get => _selectedItem;
        set
        {
            if (SetField(ref _selectedItem, value))
                RaiseCommandStates();
        }
    }

    public bool IsBusy
    {
        get => _isBusy;
        private set
        {
            if (SetField(ref _isBusy, value))
                RaiseCommandStates();
        }
    }

    public string StatusText
    {
        get => _statusText;
        private set => SetField(ref _statusText, value);
    }

    private void Save()
    {
        _settings.Cloud.ServerUrl = ServerUrl;
        _settings.Cloud.UploadPath = UploadPath;
        _settings.Cloud.DownloadDirectory = DownloadDirectory;
        var path = _store.Save(_settings);
        StatusText = $"Saved cloud settings: {path}";
    }

    private async Task CheckHealthAsync()
    {
        await WithBusyAsync(async storage =>
        {
            var response = await storage.CheckHealthAsync();
            StatusText = response.Ok ? "Cloud storage health check OK." : $"Cloud storage health check failed: {response.Error}";
        });
    }

    private async Task RefreshAsync()
    {
        await WithBusyAsync(async storage =>
        {
            await LoadFilesAsync(storage);
        });
    }

    private async Task UploadAsync()
    {
        await WithBusyAsync(async storage =>
        {
            var localPath = PathResolver.ResolveFile(UploadPath);
            var response = await storage.UploadAsync(localPath);
            StatusText = response.Ok ? $"Uploaded: {Path.GetFileName(localPath)}" : $"Upload failed: {response.Error}";
            if (response.Ok)
                await LoadFilesAsync(storage);
        });
    }

    private async Task DownloadAsync()
    {
        if (SelectedItem is null)
            return;

        await WithBusyAsync(async storage =>
        {
            var directory = PathResolver.ResolveDirectory(DownloadDirectory);
            var path = await storage.DownloadAsync(SelectedItem.Name, directory);
            StatusText = path is null ? $"Download failed: {SelectedItem.Name}" : $"Downloaded: {path}";
        });
    }

    private async Task DeleteAsync()
    {
        if (SelectedItem is null)
            return;

        await WithBusyAsync(async storage =>
        {
            var response = await storage.DeleteAsync(SelectedItem.Name);
            StatusText = response.Ok ? $"Deleted: {SelectedItem.Name}" : $"Delete failed: {response.Error}";
            if (response.Ok)
                await LoadFilesAsync(storage);
        });
    }

    private async Task LoadFilesAsync(ICloudStorage storage)
    {
        ServerItems.Clear();
        var files = await storage.ListFilesAsync();
        foreach (var file in files)
            ServerItems.Add(new CloudServerItem(file.Name, FormatSize(file.Size), file.ModifiedAt?.ToString("yyyy-MM-dd HH:mm") ?? "-"));

        StatusText = $"Cloud file list refreshed: {ServerItems.Count} item(s).";
    }

    private async Task WithBusyAsync(Func<ICloudStorage, Task> action)
    {
        if (IsBusy)
            return;

        Save();
        IsBusy = true;
        try
        {
            using var storage = new HttpCloudStorage(ServerUrl);
            await action(storage);
        }
        catch (Exception ex)
        {
            StatusText = $"Cloud operation failed: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    private void RaiseCommandStates()
    {
        (RefreshCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (UploadCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (DownloadCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (DeleteCommand as RelayCommand)?.RaiseCanExecuteChanged();
        (HealthCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }

    private static string FormatSize(long size)
    {
        if (size <= 0)
            return "-";

        return size < 1024 * 1024 ? $"{size / 1024.0:0.#} KB" : $"{size / 1024.0 / 1024.0:0.#} MB";
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

public sealed record CloudServerItem(string Name, string Size, string ModifiedAt);
