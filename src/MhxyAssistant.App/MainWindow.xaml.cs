using System.Windows;
using MhxyAssistant.App.ViewModels;

namespace MhxyAssistant.App;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        DataContext = new MainViewModel();
    }
}
