using System.Windows;
using MhxyAssistant.App.ViewModels;
using MhxyAssistant.Core.Models;

namespace MhxyAssistant.App.Windows;

public partial class YoloTrainingWindow : Window
{
    public YoloTrainingWindow(AppConfig config)
    {
        InitializeComponent();
        DataContext = new YoloTrainingViewModel(config);
    }

    private void Close_OnClick(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
