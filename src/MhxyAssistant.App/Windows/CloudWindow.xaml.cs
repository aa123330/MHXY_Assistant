using System.Windows;
using MhxyAssistant.App.ViewModels;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.App.Windows;

public partial class CloudWindow : Window
{
    public CloudWindow(AppConfig config)
    {
        InitializeComponent();
        DataContext = new CloudViewModel(config);
    }

    private void Close_OnClick(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
