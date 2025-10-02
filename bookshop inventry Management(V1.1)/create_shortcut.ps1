$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Bookshop.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\run_bookshop.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.IconLocation = "$PSScriptRoot\bookshop.ico"
$Shortcut.Save()