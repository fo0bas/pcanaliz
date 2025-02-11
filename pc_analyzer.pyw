import os
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox

def run_as_admin():
    if is_admin():
        return True
    else:
        # Перезапуск программы с правами администратора без окна командной строки
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable.replace("python.exe", "pythonw.exe"), 
                                          " ".join(sys.argv), None, 0)  # 0 вместо 1 скрывает окно
        return False

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    # Скрываем консоль для текущего процесса
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass
    
    if not is_admin():
        if messagebox.askyesno("Права администратора", 
                             "Для полного анализа системы рекомендуется запуск с правами администратора. Запустить с правами администратора?"):
            run_as_admin()
            sys.exit()
    
    app = SystemAnalyzer()
    app.mainloop() 