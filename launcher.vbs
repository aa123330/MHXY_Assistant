' MHXY Assistant - Launcher
' 双击此文件 → 启动 AI 辅助面板

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = strPath

' 通过 launcher.bat 启动（带错误处理和暂停）
objShell.Run "cmd /c """ & strPath & "\launcher.bat""", 1, False

Set objShell = Nothing
Set objFSO = Nothing
