using System.Windows;
using MhxyAssistant.App.ViewModels;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.App.Windows;

public partial class AiSettingsWindow : Window
{
    private readonly AiSettingsViewModel _viewModel;
    private bool _isInitializing = true;

    public AiSettingsWindow(AppConfig config)
    {
        InitializeComponent();
        _viewModel = new AiSettingsViewModel(config);
        DataContext = _viewModel;
        ApiKeyBox.Password = _viewModel.ApiKeyPlaceholder;
        _isInitializing = false;
    }

    private void ApiKeyBox_OnPasswordChanged(object sender, RoutedEventArgs e)
    {
        if (!_isInitializing)
            _viewModel.ApiKeyPlaceholder = ApiKeyBox.Password;
    }

    private void Close_OnClick(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
