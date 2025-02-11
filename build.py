import PyInstaller.__main__
import os

# Создаем директорию для сборки если её нет
if not os.path.exists('dist'):
    os.makedirs('dist')

PyInstaller.__main__.run([
    'pc_analyzer.py',
    '--name=PC_Analyzer',
    '--onefile',
    '--noconsole',
    '--icon=ico2.ico',
    '--add-data=requirements.txt;.',
    '--clean',
    '--windowed',
]) 