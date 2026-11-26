Option Explicit
Dim shell, fs
Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
shell.CurrentDirectory = fs.GetParentFolderName(WScript.ScriptFullName)
shell.Run """.venv\Scripts\pythonw.exe"" ""main_agent.py""", 0, False
