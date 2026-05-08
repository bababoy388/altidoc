Set ws = CreateObject("Wscript.Shell")
ws.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(Wscript.ScriptFullName)
ws.Run "venv\Scripts\python.exe altidoc.pyw", 0, False