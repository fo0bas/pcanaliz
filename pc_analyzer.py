import os
import sys
import ctypes
import psutil
import speedtest_cli as speedtest
import tkinter as tk
from tkinter import ttk, messagebox
import platform
import threading
import time
from datetime import datetime
from driver_updater.updater import DriverUpdater
from disk_info import DiskInfo

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Запускаем с правами администратора если их нет
if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

class SystemAnalyzer(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Настройка основного окна
        self.title("Быстрый анализ ПК f0bas")
        self.geometry("1000x500")  # Изменено с 1000x500 на 1250x500
        self.configure(bg='#2b2b2b')
        self.resizable(False, False)  # Запрет изменения размера окна
        
        # Устанавливаем иконку окна и в панели задач
        try:
            if os.name == 'nt':
                # Устанавливаем AppUserModelID до создания окна
                import ctypes
                myappid = u'f0bas.pcanalyzer.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                
                # Загружаем иконку
                self.iconbitmap('ico2.ico')
                
                # Устанавливаем большие и маленькие иконки для окна
                ICON_SMALL = 0
                ICON_BIG = 1
                WM_SETICON = 0x0080
                
                # Загружаем иконки разных размеров
                import win32gui
                import win32con
                import win32api
                
                # Загружаем большую иконку
                large_icon = win32gui.LoadImage(
                    0, 'ico2.ico', win32con.IMAGE_ICON,
                    48, 48, win32con.LR_LOADFROMFILE
                )
                # Загружаем маленькую иконку
                small_icon = win32gui.LoadImage(
                    0, 'ico2.ico', win32con.IMAGE_ICON,
                    16, 16, win32con.LR_LOADFROMFILE
                )
                
                # Получаем handle окна
                hwnd = self.winfo_id()
                
                # Устанавливаем иконки
                win32api.SendMessage(hwnd, WM_SETICON, ICON_BIG, large_icon)
                win32api.SendMessage(hwnd, WM_SETICON, ICON_SMALL, small_icon)
                
            else:
                icon = tk.PhotoImage(file='ico2.png')
                self.iconphoto(True, icon)
        except Exception as e:
            print(f"Не удалось установить иконку: {e}")
        
        # Настройка стилей
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Настройка цветов и стилей
        self.style.configure('Main.TFrame', background='#2b2b2b')
        self.style.configure('Header.TLabel', 
                           background='#2b2b2b', 
                           foreground='#ffffff', 
                           font=('Segoe UI', 16, 'bold'))
        self.style.configure('Info.TLabel', 
                           background='#2b2b2b', 
                           foreground='#ffffff', 
                           font=('Segoe UI', 9))
        self.style.configure('Action.TButton',
                           padding=5,
                           font=('Segoe UI', 9))
        # Добавляем новый стиль для кнопки анализа
        self.style.configure('Analyze.TButton',
                           padding=5,
                           font=('Segoe UI', 9, 'bold'),
                           background='#28a745',  # Зеленый цвет
                           foreground='#ffffff')
        self.style.configure('Treeview',
                           rowheight=20,
                           font=('Segoe UI', 9))
        
        # Основной контейнер
        self.main_frame = ttk.Frame(self, style='Main.TFrame', padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Создаем notebook (систему вкладок)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Вкладка анализа ПК
        self.analysis_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(self.analysis_frame, text="Анализ ПК")
        
        # Вкладка дисков
        self.disks_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(self.disks_frame, text="Диски")
        
        # Вкладка драйверов
        self.drivers_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(self.drivers_frame, text="Драйвера")
        
        # Вкладка апгрейда ПК
        self.upgrade_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(self.upgrade_frame, text="Апгрейд ПК")
        
        # Настройка стилей для вкладок
        self.style.configure('TNotebook.Tab', 
                           background='#2b2b2b',
                           foreground='#ffffff',
                           padding=[10, 5],
                           font=('Segoe UI', 9))
        self.style.map('TNotebook.Tab',
                      background=[('selected', '#007acc')],
                      foreground=[('selected', '#ffffff')])
        
        # Панель с основной информацией и процессами
        info_frame = ttk.Frame(self.analysis_frame, style='Main.TFrame')
        info_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)
        self.analysis_frame.grid_rowconfigure(0, weight=1)
        self.analysis_frame.grid_columnconfigure(0, weight=1)
        
        # Верхняя панель с кнопкой анализа для левой части
        left_frame = ttk.Frame(info_frame, style='Main.TFrame')
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.grid_rowconfigure(1, weight=1)  # Изменено с 0 на 1
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Кнопка анализа над левым окном
        self.analyze_button = ttk.Button(left_frame, 
                                       text="⟳ Анализ", 
                                       style='Analyze.TButton', 
                                       command=self.start_analysis)
        self.analyze_button.grid(row=0, column=0, pady=(0, 5), sticky="ew")  # Добавлен sticky="ew"
        
        # Область результатов
        self.result_text = tk.Text(left_frame,
                                 wrap=tk.WORD,
                                 font=('Consolas', 9),
                                 bg='#333333',
                                 fg='#ffffff')
        self.result_text.grid(row=1, column=0, sticky="nsew")
        result_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.result_text.yview)
        result_scroll.grid(row=1, column=1, sticky="ns")
        self.result_text['yscrollcommand'] = result_scroll.set
        
        # Правая панель с процессами
        right_frame = ttk.Frame(info_frame, style='Main.TFrame')
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Список процессов
        self.process_list = ttk.Treeview(right_frame,
                                       columns=("name", "cpu", "memory"),
                                       show="headings")
        
        self.process_list.heading("name", text="Процесс")
        self.process_list.heading("cpu", text="CPU")
        self.process_list.heading("memory", text="RAM")
        
        self.process_list.column("name", width=200)
        self.process_list.column("cpu", width=70)
        self.process_list.column("memory", width=70)
        
        self.process_list.grid(row=0, column=0, sticky="nsew")
        process_scroll = ttk.Scrollbar(right_frame, orient="vertical", command=self.process_list.yview)
        process_scroll.grid(row=0, column=1, sticky="ns")
        self.process_list['yscrollcommand'] = process_scroll.set
        
        # Кнопка завершения процессов под правым окном
        self.kill_button = ttk.Button(right_frame,
                                    text="✕ Завершить выбранные процессы",
                                    style='Action.TButton',
                                    command=self.kill_selected_processes)
        self.kill_button.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky="ew")  # Добавлены columnspan и sticky
        
        # Статусбар остается в main_frame
        self.status_var = tk.StringVar(value="Готов к анализу")
        self.statusbar = ttk.Label(self.main_frame,
                                 textvariable=self.status_var,
                                 style='Info.TLabel')
        self.statusbar.grid(row=2, column=0, sticky="ew", pady=(5, 0))

        # Панель поиска и управления выбором
        self.control_frame = ttk.Frame(self.drivers_frame, style='Main.TFrame')
        self.control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Кнопка сканирования драйверов
        self.scan_drivers_button = ttk.Button(self.control_frame,
                                            text="🔍 Сканировать драйвера",
                                            style='Analyze.TButton',
                                            command=self.scan_drivers)
        self.scan_drivers_button.grid(row=0, column=0, padx=(0,5), sticky="w")
        
        # Поле поиска
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_drivers)
        self.search_entry = ttk.Entry(self.control_frame,
                                    textvariable=self.search_var,
                                    font=('Segoe UI', 9))
        self.search_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.search_entry.insert(0, "Поиск драйвера...")
        self.search_entry.bind('<FocusIn>', self.clear_search_placeholder)
        self.search_entry.bind('<FocusOut>', self.restore_search_placeholder)
        
        # Кнопки выбора/отмены выбора всех драйверов
        self.select_all_button = ttk.Button(self.control_frame,
                                          text="✓ Выбрать все",
                                          style='Action.TButton',
                                          command=self.select_all_drivers)
        self.select_all_button.grid(row=0, column=2, padx=5)
        
        self.deselect_all_button = ttk.Button(self.control_frame,
                                             text="✗ Отменить выбор",
                                             style='Action.TButton',
                                             command=self.deselect_all_drivers)
        self.deselect_all_button.grid(row=0, column=3, padx=(0,5))
        
        # Настраиваем веса столбцов для поля поиска
        self.control_frame.grid_columnconfigure(1, weight=1)
        
        # Создаем Treeview для списка драйверов
        self.drivers_list = ttk.Treeview(self.drivers_frame, 
                                       columns=("name", "version", "date", "status"),
                                       show="headings",
                                       style='Treeview')
        
        # Настройка заголовков
        self.drivers_list.heading("name", text="Название")
        self.drivers_list.heading("version", text="Текущая версия")
        self.drivers_list.heading("date", text="Дата")
        self.drivers_list.heading("status", text="Статус")
        
        # Настройка ширины столбцов
        self.drivers_list.column("name", width=300)
        self.drivers_list.column("version", width=150)
        self.drivers_list.column("date", width=100)
        self.drivers_list.column("status", width=150)
        
        # Добавляем скроллбар
        drivers_scroll = ttk.Scrollbar(self.drivers_frame, orient="vertical", command=self.drivers_list.yview)
        self.drivers_list.configure(yscrollcommand=drivers_scroll.set)
        
        # Размещаем список и скроллбар
        self.drivers_list.grid(row=1, column=0, sticky="nsew", padx=5)
        drivers_scroll.grid(row=1, column=1, sticky="ns")
        
        # Настраиваем веса строк и столбцов
        self.drivers_frame.grid_rowconfigure(1, weight=1)
        self.drivers_frame.grid_columnconfigure(0, weight=1)
        
        # Добавляем кнопку для обновления выбранного драйвера
        self.update_driver_button = ttk.Button(self.drivers_frame,
                                             text="⬇ Обновить выбранные драйверы (0)",
                                             style='Action.TButton',
                                             command=self.update_selected_driver)
        self.update_driver_button.grid(row=2, column=0, padx=5, pady=5, sticky="e")

        # Настройка стилей для Treeview и тегов
        self.style.configure('Treeview', 
                           background='#333333',
                           foreground='#ffffff',  # Белый цвет по умолчанию
                           fieldbackground='#333333')
        
        self.style.configure('Treeview.Heading',
                           background='#2b2b2b',
                           foreground='#ffffff')
        
        # Добавляем теги для разных уровней важности
        self.drivers_list.tag_configure('important_update', foreground='#ff4444')  # Красный - важное
        self.drivers_list.tag_configure('medium_update', foreground='#ffd700')    # Желтый - среднее
        self.drivers_list.tag_configure('minor_update', foreground='#28a745')     # Зеленый - неважное
        self.drivers_list.tag_configure('current_version', foreground='#ffffff')   # Белый - актуальная версия
        
        # Добавляем обработчик клика для чекбоксов
        self.drivers_list.bind('<Button-1>', self.toggle_checkbox)

        # Добавляем тег для скрытых элементов (полностью скрываем элемент)
        self.drivers_list.tag_configure('hidden', foreground='#333333', background='#333333')

        self.driver_updater = DriverUpdater()

        # Кнопка анализа апгрейда
        self.analyze_upgrade_button = ttk.Button(self.upgrade_frame,
                                               text="🔍 Анализ апгрейда ПК",
                                               style='Analyze.TButton',
                                               command=self.analyze_upgrade)
        self.analyze_upgrade_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Область результатов анализа
        self.upgrade_text = tk.Text(self.upgrade_frame,
                                  wrap=tk.WORD,
                                  font=('Consolas', 9),
                                  bg='#333333',
                                  fg='#ffffff',
                                  height=20)
        self.upgrade_text.grid(row=1, column=0, sticky="nsew", padx=5)
        
        # Настраиваем веса
        self.upgrade_frame.grid_rowconfigure(1, weight=1)
        self.upgrade_frame.grid_columnconfigure(0, weight=1)

        # Добавляем элементы на вкладку дисков
        self.setup_disks_tab()

    def setup_disks_tab(self):
        """Настройка вкладки анализа дисков"""
        # Кнопка анализа дисков
        self.analyze_disks_button = ttk.Button(self.disks_frame,
                                             text="🔍 Анализировать диски",
                                             style='Analyze.TButton',
                                             command=self.analyze_disks)
        self.analyze_disks_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Создаем Treeview для списка дисков
        self.disks_list = ttk.Treeview(self.disks_frame,
                                      columns=("name", "size", "status", "temp", 
                                             "load", "lifetime", "score"),
                                      show="headings",
                                      style='Treeview')
        
        # Настройка заголовков
        self.disks_list.heading("name", text="Название")
        self.disks_list.heading("size", text="Размер")
        self.disks_list.heading("status", text="Состояние")
        self.disks_list.heading("temp", text="Температура")
        self.disks_list.heading("load", text="Нагрузка")
        self.disks_list.heading("lifetime", text="Ресурс")
        self.disks_list.heading("score", text="Оценка")
        
        # Настройка ширины столбцов
        self.disks_list.column("name", width=200)
        self.disks_list.column("size", width=100)
        self.disks_list.column("status", width=150)
        self.disks_list.column("temp", width=100)
        self.disks_list.column("load", width=100)
        self.disks_list.column("lifetime", width=100)
        self.disks_list.column("score", width=100)
        
        self.disks_list.grid(row=1, column=0, sticky="nsew", padx=5)
        
        # Добавляем скроллбар
        disks_scroll = ttk.Scrollbar(self.disks_frame, orient="vertical", 
                                   command=self.disks_list.yview)
        disks_scroll.grid(row=1, column=1, sticky="ns")
        self.disks_list.configure(yscrollcommand=disks_scroll.set)
        
        # Добавляем предупреждающий текст
        warning_label = tk.Label(self.disks_frame,
                               text="Температура и ресурс работы диска могут быть не корректны",
                               fg='red',
                               bg='#2b2b2b',
                               font=('Segoe UI', 12))
        warning_label.grid(row=2, column=0, columnspan=2, padx=5, pady=(5,0), sticky="w")
        
        # Область для детальной информации
        self.disk_details = tk.Text(self.disks_frame,
                                  wrap=tk.WORD,
                                  height=8,
                                  bg='#333333',
                                  fg='#ffffff',
                                  font=('Consolas', 9))
        self.disk_details.grid(row=3, column=0, columnspan=2, sticky="ew", 
                             padx=5, pady=5)
        
        # Привязываем обработчик выбора диска
        self.disks_list.bind('<<TreeviewSelect>>', self.show_disk_details)
        
        # Настраиваем веса строк и столбцов
        self.disks_frame.grid_rowconfigure(1, weight=1)
        self.disks_frame.grid_columnconfigure(0, weight=1)
    
    def analyze_disks(self):
        """Анализ состояния дисков"""
        try:
            # Очищаем список
            for item in self.disks_list.get_children():
                self.disks_list.delete(item)
            
            # Создаем анализатор дисков
            disk_analyzer = DiskInfo()
            disks = disk_analyzer.get_disk_info()
            
            for disk_info in disks:
                # Определяем цвет для оценки
                score = disk_info['score']
                if score >= 8:
                    score_tag = 'good'
                elif score >= 6:
                    score_tag = 'normal'
                elif score >= 4:
                    score_tag = 'warning'
                else:
                    score_tag = 'critical'
                
                # Добавляем диск в список
                self.disks_list.insert("", "end", values=(
                    disk_info['name'],
                    disk_info['size'],
                    disk_info['status'],
                    f"{disk_info['temperature']}°C",
                    f"{disk_info['load']}%",
                    f"{disk_info['estimated_lifetime']} дней",
                    f"{disk_info['score']}/10"
                ), tags=(score_tag,))
            
            # Настраиваем цвета для оценок
            self.disks_list.tag_configure('good', foreground='#00ff00')
            self.disks_list.tag_configure('normal', foreground='#ffff00')
            self.disks_list.tag_configure('warning', foreground='#ffa500')
            self.disks_list.tag_configure('critical', foreground='#ff0000')
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось проанализировать диски:\n{str(e)}")
    
    def show_disk_details(self, event):
        """Показ детальной информации о выбранном диске"""
        selection = self.disks_list.selection()
        if not selection:
            return
            
        try:
            from disk_analyzer import DiskAnalyzer
            analyzer = DiskAnalyzer()
            disks = analyzer.get_disk_info()
            
            item = selection[0]
            disk_name = self.disks_list.item(item)['values'][0]
            
            # Находим информацию о выбранном диске
            disk_info = next((d for d in disks if d['name'] == disk_name), None)
            if disk_info:
                # Очищаем и обновляем область деталей
                self.disk_details.delete(1.0, tk.END)
                
                details = f"Модель: {disk_info['model']}\n"
                details += f"Серийный номер: {disk_info['serial']}\n"
                details += f"Интерфейс: {disk_info['interface']}\n\n"
                
                # Добавляем информацию о здоровье диска
                health = disk_info['health']
                if health:
                    details += "Показатели здоровья:\n"
                    details += f"• Время работы: {health['power_on_hours']} часов\n"
                    details += f"• Циклов включения: {health['start_stop_count']}\n"
                    details += f"• Переназначенных секторов: {health['reallocated_sectors']}\n"
                    details += f"• Ожидающих секторов: {health['pending_sectors']}\n"
                    details += f"• Неисправимых секторов: {health['uncorrectable_sectors']}\n"
                
                self.disk_details.insert(tk.END, details)
                
        except Exception as e:
            self.disk_details.delete(1.0, tk.END)
            self.disk_details.insert(tk.END, f"Ошибка получения информации: {str(e)}")

    def scroll_to_bottom(self):
        """Прокрутка текста вниз"""
        self.result_text.see(tk.END)
        self.result_text.update()

    def start_analysis(self):
        self.analyze_button.config(state="disabled")
        self.statusbar.configure(style='Info.TLabel')  # Возвращаем обычный стиль
        self.status_var.set("Выполняется анализ системы...")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "🔍 Идёт анализ системы...\n\n")
        
        # Запускаем анализ в отдельном потоке
        thread = threading.Thread(target=self.perform_analysis)
        thread.start()

    def perform_analysis(self):
        try:
            # Установка высокого приоритета для процесса анализа
            process = psutil.Process(os.getpid())
            process.nice(psutil.HIGH_PRIORITY_CLASS)
        except:
            pass

        # Анализ CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        
        # Анализ памяти
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Анализ диска
        disk = psutil.disk_usage('/')
        
        # Информация о системе
        system_info = platform.system() + " " + platform.version()
        
        # Добавляем вызовы scroll_to_bottom() после каждого блока вставки текста
        self.result_text.insert(tk.END, f"\nИнформация о системе:\n{system_info}\n")
        self.scroll_to_bottom()
        
        self.result_text.insert(tk.END, f"\n=== CPU ===\n")
        self.result_text.insert(tk.END, f"Загрузка CPU: {cpu_percent}%\n")
        self.result_text.insert(tk.END, f"Частота CPU: {cpu_freq.current:.2f} МГц\n")
        
        # Расширенный анализ температуры CPU через OpenHardwareMonitor
        try:
            import wmi
            w = wmi.WMI(namespace="root/OpenHardwareMonitor")
            temperature_infos = w.Sensor()
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature':
                    if 'CPU' in sensor.Name:
                        self.result_text.insert(tk.END, f"Температура {sensor.Name}: {sensor.Value:.1f}°C\n")
                        self.scroll_to_bottom()
        except:
            # Если OpenHardwareMonitor недоступен, используем psutil
            try:
                temperatures = psutil.sensors_temperatures()
                if temperatures:
                    for name, entries in temperatures.items():
                        for entry in entries:
                            self.result_text.insert(tk.END, f"Температура {name}: {entry.current}°C\n")
                            self.scroll_to_bottom()
            except:
                self.result_text.insert(tk.END, "Не удалось получить данные о температуре CPU\n")
                self.scroll_to_bottom()

        # Добавляем информацию о GPU
        self.result_text.insert(tk.END, f"\n=== GPU ===\n")
        gpu_found = False
        
        # Сначала пробуем получить информацию о дискретной видеокарте
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_found = True
                for gpu in gpus:
                    self.result_text.insert(tk.END, f"GPU: {gpu.name}\n")
                    self.result_text.insert(tk.END, f"Загрузка GPU: {gpu.load*100:.1f}%\n")
                    self.result_text.insert(tk.END, f"Температура GPU: {gpu.temperature}°C\n")
                    self.result_text.insert(tk.END, f"Память GPU: {gpu.memoryUsed}MB / {gpu.memoryTotal}MB ({gpu.memoryUtil*100:.1f}%)\n")
                    
                    # Добавляем рекомендации по GPU
                    if gpu.temperature > 85:
                        recommendations.append(f"❗ КРИТИЧЕСКАЯ температура GPU: {gpu.temperature}°C!")
                        recommendations.append("  - Срочные действия:")
                        recommendations.append("    * Снизьте нагрузку на видеокарту")
                        recommendations.append("    * Проверьте работу вентиляторов GPU")
                        recommendations.append("    * Очистите радиатор GPU от пыли")
                    elif gpu.temperature > 80:
                        recommendations.append(f"⚠️ Высокая температура GPU: {gpu.temperature}°C")
                        recommendations.append("  - Рекомендации:")
                        recommendations.append("    * Улучшите вентиляцию корпуса")
                        recommendations.append("    * Проверьте термопасту GPU")
                    
                    if gpu.load*100 > 90:
                        recommendations.append(f"❗ Высокая нагрузка на GPU: {gpu.load*100:.1f}%")
                        recommendations.append("  - Рекомендации:")
                        recommendations.append("    * Закройте ресурсоемкие приложения")
                        recommendations.append("    * Проверьте на майнинг-процессы")
                    
                    if gpu.memoryUtil*100 > 90:
                        recommendations.append(f"❗ Высокое использование памяти GPU: {gpu.memoryUtil*100:.1f}%")
                        recommendations.append("  - Рекомендации:")
                        recommendations.append("    * Закройте неиспользуемые игры/приложения")
                        recommendations.append("    * Уменьшите настройки качества графики")
        except:
            pass

        # Если дискретная видеокарта не найдена, ищем встроенную
        if not gpu_found:
            try:
                import wmi
                w = wmi.WMI()
                for video_controller in w.Win32_VideoController():
                    self.result_text.insert(tk.END, f"Встроенный GPU: {video_controller.Name}\n")
                    self.result_text.insert(tk.END, f"Драйвер: {video_controller.DriverVersion}\n")
                    
                    # Получаем информацию о памяти видеокарты
                    if hasattr(video_controller, 'AdapterRAM'):
                        vram_gb = video_controller.AdapterRAM / (1024**3)
                        self.result_text.insert(tk.END, f"Видеопамять: {vram_gb:.2f} GB\n")
                    
                    # Получаем текущее разрешение
                    if hasattr(video_controller, 'CurrentHorizontalResolution') and \
                       hasattr(video_controller, 'CurrentVerticalResolution'):
                        self.result_text.insert(tk.END, 
                            f"Текущее разрешение: {video_controller.CurrentHorizontalResolution}x{video_controller.CurrentVerticalResolution}\n")
                    
                    # Добавляем рекомендации для встроенной графики
                    if hasattr(video_controller, 'AdapterRAM') and video_controller.AdapterRAM / (1024**3) < 2:
                        recommendations.append("⚠️ Обнаружена встроенная графика с малым объемом памяти")
                        recommendations.append("  - Рекомендации:")
                        recommendations.append("    * Для игр рекомендуется установить дискретную видеокарту")
                        recommendations.append("    * Используйте более легкие графические приложения")
                        recommendations.append("    * Уменьшите настройки качества графики в играх")
            except Exception as e:
                self.result_text.insert(tk.END, "Не удалось получить информацию о встроенной видеокарте\n")
        
        self.scroll_to_bottom()

        self.result_text.insert(tk.END, f"\n=== Память ===\n")
        self.result_text.insert(tk.END, f"Использование RAM: {memory.percent}%\n")
        self.result_text.insert(tk.END, f"Всего RAM: {memory.total / (1024**3):.2f} ГБ\n")
        self.result_text.insert(tk.END, f"Доступно RAM: {memory.available / (1024**3):.2f} ГБ\n")
        self.result_text.insert(tk.END, f"Использование SWAP: {swap.percent}%\n")
        self.scroll_to_bottom()

        self.result_text.insert(tk.END, f"\n=== Диски ===\n")
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                self.result_text.insert(tk.END, 
                    f"Диск {partition.device}:\n"
                    f"  Всего: {partition_usage.total / (1024**3):.2f} ГБ\n"
                    f"  Использовано: {partition_usage.percent}%\n")
                
                # Получение скорости чтения/записи диска
                disk_io = psutil.disk_io_counters(perdisk=True)
                if partition.device.strip(":\\") in disk_io:
                    disk_stats = disk_io[partition.device.strip(":\\")]
                    self.result_text.insert(tk.END,
                        f"  Прочитано: {disk_stats.read_bytes / (1024**3):.2f} ГБ\n"
                        f"  Записано: {disk_stats.write_bytes / (1024**3):.2f} ГБ\n")
                    self.scroll_to_bottom()
            except:
                continue

        self.result_text.insert(tk.END, f"\n=== Сеть ===\n")
        net_io = psutil.net_io_counters()
        self.result_text.insert(tk.END, 
            f"Отправлено: {net_io.bytes_sent / (1024**2):.2f} МБ\n"
            f"Получено: {net_io.bytes_recv / (1024**2):.2f} МБ\n")
        self.scroll_to_bottom()

        # Анализ сетевых подключений
        connections = psutil.net_connections()
        established_connections = len([conn for conn in connections if conn.status == 'ESTABLISHED'])
        self.result_text.insert(tk.END, f"Активных подключений: {established_connections}\n")
        self.scroll_to_bottom()

        # Формирование рекомендаций
        recommendations = []  # Список для хранения конкретных рекомендаций
        
        # Анализ и рекомендации по CPU
        if cpu_percent > 90:
            recommendations.append("❗ КРИТИЧЕСКАЯ загрузка процессора!")
            recommendations.append(f"  - Текущая загрузка: {cpu_percent}% (критический уровень)")
            recommendations.append("  - Немедленные действия:")
            cpu_heavy_processes = sorted(
                [(p.info['name'], p.info['cpu_percent']) 
                 for p in psutil.process_iter(['name', 'cpu_percent'])],
                key=lambda x: x[1], reverse=True)[:5]
            recommendations.append("  - Рекомендуется завершить следующие процессы:")
            for proc_name, proc_cpu in cpu_heavy_processes:
                recommendations.append(f"    * {proc_name} (потребляет {proc_cpu:.1f}% CPU)")
                self.scroll_to_bottom()
        elif cpu_percent > 80:
            recommendations.append("❗ Высокая загрузка процессора")
            recommendations.append(f"  - Текущая загрузка: {cpu_percent}% (высокий уровень)")
            recommendations.append("  - Рекомендуемые действия:")
            recommendations.append("    * Закройте неиспользуемые программы")
            recommendations.append("    * Проверьте систему на вирусы")
            recommendations.append("    * Отключите неиспользуемые фоновые процессы")
            self.scroll_to_bottom()
        elif cpu_percent > 60:
            recommendations.append("⚠️ Повышенная загрузка процессора")
            recommendations.append(f"  - Текущая загрузка: {cpu_percent}%")
            recommendations.append("  - Рекомендации по оптимизации:")
            recommendations.append("    * Проверьте автозагрузку Windows")
            recommendations.append("    * Очистите временные файлы")
            self.scroll_to_bottom()

        # Анализ температуры CPU
        try:
            temperatures = psutil.sensors_temperatures()
            if temperatures:
                for name, entries in temperatures.items():
                    for entry in entries:
                        if entry.current > 90:
                            recommendations.append(f"❗ КРИТИЧЕСКАЯ температура {name}: {entry.current}°C!")
                            recommendations.append("  - Срочные действия:")
                            recommendations.append("    * Немедленно завершите ресурсоемкие задачи")
                            recommendations.append("    * Проверьте работу вентиляторов")
                            recommendations.append("    * Очистите систему охлаждения от пыли")
                            recommendations.append("    * Замените термопасту")
                            self.scroll_to_bottom()
                        elif entry.current > 80:
                            recommendations.append(f"❗ Опасная температура {name}: {entry.current}°C")
                            recommendations.append("  - Необходимые действия:")
                            recommendations.append("    * Очистите систему охлаждения")
                            recommendations.append("    * Проверьте термопасту")
                            recommendations.append("    * Убедитесь в исправности вентиляторов")
                            self.scroll_to_bottom()
                        elif entry.current > 70:
                            recommendations.append(f"⚠️ Повышенная температура {name}: {entry.current}°C")
                            recommendations.append("  - Рекомендации:")
                            recommendations.append("    * Проверьте чистоту системы охлаждения")
                            recommendations.append("    * Обеспечьте хорошую вентиляцию корпуса")
                            self.scroll_to_bottom()
        except:
            pass

        # Анализ памяти
        total_ram_gb = memory.total / (1024**3)
        available_ram_gb = memory.available / (1024**3)
        used_ram_gb = total_ram_gb - available_ram_gb

        if total_ram_gb < 8:
            recommendations.append(f"❗ Недостаточный объём RAM: {total_ram_gb:.1f}GB")
            recommendations.append("  - Рекомендации по обновлению:")
            recommendations.append("    * Увеличьте объём RAM минимум до 8GB")
            recommendations.append("    * Рекомендуемый объём для Windows 10/11: 16GB")
            recommendations.append(f"  - Текущее использование: {memory.percent}%")
            self.scroll_to_bottom()

        if memory.percent > 90:
            recommendations.append(f"❗ КРИТИЧЕСКАЯ нагрузка на RAM: {memory.percent}%")
            recommendations.append(f"  - Используется: {used_ram_gb:.1f}GB из {total_ram_gb:.1f}GB")
            recommendations.append("  - Срочные действия:")
            memory_heavy_processes = sorted(
                [(p.info['name'], p.info['memory_percent']) 
                 for p in psutil.process_iter(['name', 'memory_percent'])],
                key=lambda x: x[1], reverse=True)[:5]
            recommendations.append("  - Завершите следующие процессы:")
            for proc_name, proc_mem in memory_heavy_processes:
                recommendations.append(f"    * {proc_name} (использует {proc_mem:.1f}% RAM)")
                self.scroll_to_bottom()
        elif memory.percent > 80:
            recommendations.append(f"❗ Высокая нагрузка на RAM: {memory.percent}%")
            recommendations.append(f"  - Свободно только: {available_ram_gb:.1f}GB")
            recommendations.append("  - Рекомендуемые действия:")
            recommendations.append("    * Закройте неиспользуемые программы")
            recommendations.append("    * Очистите кэш браузера")
            recommendations.append("    * Проверьте на утечки памяти")
            self.scroll_to_bottom()

        # Анализ файла подкачки
        if swap.percent > 80:
            recommendations.append(f"❗ Критическое использование файла подкачки: {swap.percent}%")
            recommendations.append("  - Рекомендации:")
            recommendations.append("    * Увеличьте объём физической памяти")
            recommendations.append("    * Увеличьте размер файла подкачки")
            recommendations.append(f"    * Текущий объём RAM: {total_ram_gb:.1f}GB")
            recommendations.append(f"    * Доступно RAM: {available_ram_gb:.1f}GB")
            self.scroll_to_bottom()

        # Анализ дисков
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                free_space_gb = (partition_usage.total - partition_usage.used) / (1024**3)
                total_space_gb = partition_usage.total / (1024**3)
                
                if partition_usage.percent > 95:
                    recommendations.append(f"❗ КРИТИЧЕСКИ мало места на диске {partition.device}")
                    recommendations.append(f"  - Свободно всего: {free_space_gb:.1f}GB из {total_space_gb:.1f}GB")
                    recommendations.append("  - Срочные действия:")
                    recommendations.append("    * Удалите ненужные файлы")
                    recommendations.append("    * Очистите корзину")
                    recommendations.append("    * Удалите временные файлы Windows")
                    recommendations.append("    * Используйте программу очистки диска")
                    self.scroll_to_bottom()
                elif partition_usage.percent > 85:
                    recommendations.append(f"⚠️ Заканчивается место на диске {partition.device}")
                    recommendations.append(f"  - Свободно: {free_space_gb:.1f}GB из {total_space_gb:.1f}GB")
                    recommendations.append("  - Рекомендации по очистке:")
                    recommendations.append("    * Удалите неиспользуемые программы")
                    recommendations.append("    * Перенесите большие файлы на внешний носитель")
                    recommendations.append("    * Очистите загрузки и временные файлы")
                    self.scroll_to_bottom()

                # Анализ производительности диска
                if "fixed" in partition.opts:
                    disk_io = psutil.disk_io_counters(perdisk=True)
                    if partition.device.strip(":\\") in disk_io:
                        disk_stats = disk_io[partition.device.strip(":\\")]
                        if disk_stats.read_time + disk_stats.write_time > 1500:
                            recommendations.append(f"❗ Низкая производительность диска {partition.device}")
                            recommendations.append("  - Рекомендации по оптимизации:")
                            if "SSD" not in partition.opts:
                                recommendations.append("    * Выполните дефрагментацию диска")
                                recommendations.append("    * Рекомендуется заменить HDD на SSD")
                                recommendations.append("    * Проверьте диск на ошибки")
                            recommendations.append("    * Отключите ненужные службы индексации")
                            self.scroll_to_bottom()
            except:
                continue

        # Анализ сети
        if established_connections > 150:
            recommendations.append(f"❗ Большое количество сетевых подключений: {established_connections}")
            recommendations.append("  - Возможные проблемы:")
            recommendations.append("    * Чрезмерная сетевая активность")
            recommendations.append("    * Возможно наличие вредоносного ПО")
            network_processes = []
            for conn in psutil.net_connections():
                try:
                    if conn.status == 'ESTABLISHED':
                        process = psutil.Process(conn.pid)
                        network_processes.append(process.name())
                except:
                    continue
            if network_processes:
                recommendations.append("  - Активные сетевые процессы:")
                for proc in set(network_processes[:5]):
                    recommendations.append(f"    * {proc}")
                    self.scroll_to_bottom()
                recommendations.append("  - Рекомендации:")
                recommendations.append("    * Проверьте систему антивирусом")
                recommendations.append("    * Проверьте автозапуск программ")
                recommendations.append("    * Мониторьте сетевую активность")
                self.scroll_to_bottom()

        # Анализ процессов
        self.analyze_processes()
        
        # Добавляем расширенный анализ системы
        self.analyze_system_services()
        self.analyze_startup_programs()
        self.analyze_system_drivers()

        # Перемещаем рекомендации в конец
        self.result_text.insert(tk.END, f"\n=== Рекомендации для вашего ПК ===\n")
        
        if recommendations:
            for rec in recommendations:
                self.result_text.insert(tk.END, rec + "\n")
                self.scroll_to_bottom()
        else:
            self.result_text.insert(tk.END, "✅ Ваш компьютер работает оптимально!\n")
            self.scroll_to_bottom()
        
        # Добавляем общую оценку ПК
        # Рассчитываем оценку на основе различных параметров
        score = 10  # Начальная оценка
        
        # Снижаем оценку на основе проблем
        if cpu_percent > 90: score -= 3
        elif cpu_percent > 80: score -= 2
        elif cpu_percent > 60: score -= 1
        
        try:
            if temperatures:
                for name, entries in temperatures.items():
                    for entry in entries:
                        if entry.current > 90: score -= 3
                        elif entry.current > 80: score -= 2
                        elif entry.current > 70: score -= 1
        except:
            pass
        
        if memory.percent > 90: score -= 3
        elif memory.percent > 80: score -= 2
        elif memory.percent > 70: score -= 1
        
        if total_ram_gb < 8: score -= 2
        
        if swap.percent > 80: score -= 1
        
        # Проверяем диски
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                if partition_usage.percent > 95: score -= 2
                elif partition_usage.percent > 85: score -= 1
            except:
                continue
        
        # Убеждаемся, что оценка не ниже 1
        score = max(1, score)
        
        # Добавляем оценку с зеленым цветом и увеличенным шрифтом
        self.result_text.insert(tk.END, "\n")  # Пустая строка для отделения
        self.result_text.tag_configure("score", foreground="#28a745", font=('Segoe UI', 14, 'bold'))
        self.result_text.insert(tk.END, f"Общая оценка ПК: {score}/10", "score")
        self.scroll_to_bottom()
        
        # Настройка стиля для статуса завершения
        self.style.configure('Complete.TLabel',
                           background='#2b2b2b',
                           foreground='#28a745',  # Зеленый цвет
                           font=('Segoe UI', 9))
        
        # Обновляем статус
        self.statusbar.configure(style='Complete.TLabel')
        self.status_var.set("Анализ выполнен")
        
        # Включаем кнопку
        self.analyze_button.config(state="normal")

    def analyze_processes(self):
        # Очищаем список процессов
        for item in self.process_list.get_children():
            self.process_list.delete(item)
            
        # Настройка стилей для Treeview
        self.style.configure('Treeview', 
                           background='#333333',
                           foreground='#ff4444',  # Красный цвет для всех процессов
                           fieldbackground='#333333')
        
        self.style.configure('Treeview.Heading',
                           background='#2b2b2b',
                           foreground='#ffffff')
        
        # Получаем список процессов с дополнительной информацией
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                proc_info = proc.info
                # Показываем процессы, которые потребляют много ресурсов
                if proc_info['cpu_percent'] > 1 or proc_info['memory_percent'] > 1:
                    self.process_list.insert("", tk.END, values=(
                        proc_info['name'],
                        f"{proc_info['cpu_percent']:.1f}",
                        f"{proc_info['memory_percent']:.1f}",
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def analyze_system_services(self):
        """Анализ системных служб"""
        try:
            self.result_text.insert(tk.END, f"\n=== Системные службы ===\n")
            for service in psutil.win_service_iter():
                try:
                    service_info = service.as_dict()
                    if service_info['status'] == 'running':
                        # Анализируем только запущенные службы
                        self.result_text.insert(tk.END, 
                            f"Служба: {service_info['name']} - {service_info['display_name']}\n")
                        self.scroll_to_bottom()
                except:
                    continue
        except:
            pass

    def analyze_startup_programs(self):
        """Анализ автозагрузки"""
        try:
            import winreg
            self.result_text.insert(tk.END, f"\n=== Программы автозагрузки ===\n")
            
            startup_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
            ]
            
            for path in startup_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, 
                                       winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            self.result_text.insert(tk.END, f"Автозагрузка: {name}\n")
                            i += 1
                            self.scroll_to_bottom()
                        except WindowsError:
                            break
                except:
                    continue
        except:
            pass

    def analyze_system_drivers(self):
        """Анализ драйверов системы"""
        try:
            self.result_text.insert(tk.END, f"\n=== Системные драйверы ===\n")
            for service in psutil.win_service_iter():
                try:
                    service_info = service.as_dict()
                    if service_info['status'] == 'running' and 'driver' in str(service_info['start_type']).lower():
                        self.result_text.insert(tk.END, 
                            f"Драйвер: {service_info['name']} - {service_info['display_name']}\n")
                        self.scroll_to_bottom()
                except:
                    continue
        except:
            pass

    def kill_selected_processes(self):
        if not is_admin():
            if messagebox.askyesno("Права администратора", 
                                 "Для завершения некоторых процессов требуются права администратора. Перезапустить с правами администратора?"):
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit()
        
        selected_items = self.process_list.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Не выбраны процессы для завершения")
            return
        
        # Обрабатываем каждый выбранный процесс отдельно
        for item in selected_items:
            process_info = self.process_list.item(item)['values']
            process_name = process_info[0]
            cpu_usage = process_info[1]
            memory_usage = process_info[2]
            
            # Показываем детальную информацию о процессе и запрашиваем подтверждение
            if messagebox.askyesno("Подтверждение завершения процесса", 
                                f"Завершить процесс?\n\n"
                                f"Имя: {process_name}\n"
                                f"Загрузка CPU: {cpu_usage}%\n"
                                f"Использование памяти: {memory_usage}%\n\n"
                                f"Внимание: Завершение системных процессов может быть опасно!"):
                try:
                    # Ищем процесс по имени и собираем дополнительную информацию
                    for proc in psutil.process_iter(['pid', 'name', 'username']):
                        if proc.info['name'] == process_name:
                            try:
                                # Получаем дополнительную информацию о процессе
                                proc_details = proc.as_dict(attrs=['pid', 'name', 'username', 'create_time'])
                                
                                # Завершаем процесс
                                proc.kill()
                                
                                # Показываем сообщение об успешном завершении
                                messagebox.showinfo("Процесс завершен", 
                                    f"Процесс успешно завершен:\n\n"
                                    f"Имя: {proc_details['name']}\n"
                                    f"PID: {proc_details['pid']}\n"
                                    f"Пользователь: {proc_details['username']}")
                                
                            except psutil.AccessDenied:
                                messagebox.showerror("Ошибка", 
                                    f"Отказано в доступе к процессу: {process_name}\n"
                                    "Требуются права администратора или процесс защищен системой")
                            except psutil.NoSuchProcess:
                                messagebox.showerror("Ошибка", 
                                    f"Процесс больше не существует: {process_name}")
                            break
                except Exception as e:
                    messagebox.showerror("Ошибка", 
                        f"Не удалось завершить процесс {process_name}\n"
                        f"Ошибка: {str(e)}")
        
        # Обновляем список процессов после всех операций
        self.analyze_processes()

    def toggle_checkbox(self, event):
        """Обработка клика по чекбоксу"""
        region = self.drivers_list.identify_region(event.x, event.y)
        if region == "cell":
            column = self.drivers_list.identify_column(event.x)
            if column == '#1':  # Первая колонка с чекбоксами
                item = self.drivers_list.identify_row(event.y)
                if item:
                    values = list(self.drivers_list.item(item)['values'])
                    if values:
                        # Переключаем состояние чекбокса
                        if values[0].startswith('☐'):
                            values[0] = values[0].replace('☐', '☑')
                            self.drivers_list.selection_add(item)
                        else:
                            values[0] = values[0].replace('☑', '☐')
                            self.drivers_list.selection_remove(item)
                        self.drivers_list.item(item, values=values)
                        # Обновляем счетчик только доступных обновлений
                        self.update_selection_counter()

    def scan_drivers(self):
        """Сканирование драйверов"""
        # Очищаем список
        for item in self.drivers_list.get_children():
            self.drivers_list.delete(item)
        
        # Очищаем поле поиска
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "Поиск драйвера...")
        
        try:
            import wmi
            w = wmi.WMI()
            
            # Получаем информацию о драйверах
            for driver in w.Win32_PnPSignedDriver():
                try:
                    if driver.DeviceName and driver.DriverVersion:
                        # Проверяем наличие обновлений и их важность
                        update_info = self.check_driver_update(driver)
                        
                        # Определяем статус и тег
                        if update_info['important']:
                            status = "❗ Важное обновление"
                            tags = ('important_update',)
                        elif update_info['medium']:
                            status = "⚠️ Рекомендуемое обновление"
                            tags = ('medium_update',)
                        elif update_info['has_update']:
                            status = "ℹ️ Доступно обновление"
                            tags = ('minor_update',)
                        else:
                            status = "✓ Актуальная версия"
                            tags = ('current_version',)
                        
                        # Добавляем в список
                        self.drivers_list.insert("", tk.END, values=(
                            "☐ " + driver.DeviceName,
                            driver.DriverVersion,
                            driver.DriverDate.split('.')[0] if driver.DriverDate else "Неизвестно",
                            status
                        ), tags=tags)
                except:
                    continue
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить информацию о драйверах: {str(e)}")
        
        self.update_selection_counter()

    def check_driver_update(self, driver):
        """Проверка наличия обновлений для драйвера"""
        try:
            # Здесь должна быть логика проверки обновлений
            # Пока возвращаем случайные значения для демонстрации
            import random
            has_update = random.choice([True, False])
            if has_update:
                importance = random.choice(['important', 'medium', 'minor'])
                return {
                    'has_update': True,
                    'important': importance == 'important',
                    'medium': importance == 'medium',
                    'minor': importance == 'minor'
                }
            return {
                'has_update': False,
                'important': False,
                'medium': False,
                'minor': False
            }
        except:
            return {'has_update': False, 'important': False, 'medium': False, 'minor': False}

    def get_driver_size(self, driver_name):
        """Получение примерного размера драйвера в МБ"""
        try:
            import wmi
            w = wmi.WMI()
            for driver in w.Win32_PnPSignedDriver():
                if driver.DeviceName == driver_name:
                    # Генерируем случайный размер от 10 до 300 МБ для демонстрации
                    # В реальности здесь должен быть запрос к базе драйверов
                    import random
                    return random.randint(10, 300)
        except:
            return 50  # Возвращаем среднее значение при ошибке
        return 50

    def update_selected_driver(self):
        """Обновление выбранных драйверов"""
        selected = self.drivers_list.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите драйверы для обновления")
            return
        
        # Собираем информацию о выбранных драйверах
        drivers_to_update = []
        total_size = 0
        
        # Создаем один WMI объект для всех запросов
        try:
            import wmi
            w = wmi.WMI()
            drivers_info = {d.DeviceName: d for d in w.Win32_PnPSignedDriver()}
        except:
            drivers_info = {}
        
        for item in selected:
            driver_info = self.drivers_list.item(item)
            if "Актуальная версия" not in driver_info['values'][3]:
                driver_name = driver_info['values'][0][2:]  # Убираем чекбокс из названия
                
                # Генерируем размер драйвера (в реальном приложении здесь будет запрос к базе драйверов)
                import random
                driver_size = random.randint(10, 300)
                total_size += driver_size
                drivers_to_update.append((driver_info['values'], driver_size, item))  # Добавляем item в кортеж
        
        if not drivers_to_update:
            messagebox.showinfo("Информация", "Среди выбранных драйверов нет доступных обновлений")
            return
        
        # Если выбрано больше трех драйверов, показываем общую информацию
        if len(drivers_to_update) > 3:
            message = (f"Выбрано драйверов для обновления: {len(drivers_to_update)}\n"
                      f"Общий размер обновлений: {total_size} МБ\n\n"
                      "Продолжить обновление?")
        else:
            # Формируем детальное сообщение для небольшого количества драйверов
            message = f"Выбрано драйверов для обновления: {len(drivers_to_update)}\n"
            message += f"Общий размер обновлений: {total_size} МБ\n\n"
            for driver, size, item in drivers_to_update:
                message += f"• {driver[0][2:]}\n"  # Название драйвера
                message += f"  Текущая версия: {driver[1]}\n"
                message += f"  Размер обновления: {size} МБ\n"
                if "Важное" in driver[3]:
                    message += "  ❗ Важное обновление\n"
                message += "\n"
        
        if messagebox.askyesno("Подтверждение обновления", message):
            # Создаем окно прогресса
            progress_window = tk.Toplevel(self)
            progress_window.title("Обновление драйверов")
            progress_window.geometry("400x200")
            progress_window.configure(bg='#2b2b2b')
            progress_window.transient(self)
            progress_window.grab_set()
            
            # Добавляем элементы в окно прогресса
            progress_label = ttk.Label(progress_window, 
                                     text="Подготовка к обновлению...",
                                     style='Info.TLabel')
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, 
                                         mode='determinate',
                                         length=300)
            progress_bar.pack(pady=10)
            
            status_label = ttk.Label(progress_window,
                                   text="",
                                   style='Info.TLabel')
            status_label.pack(pady=10)
            
            # Функция обновления драйверов в отдельном потоке
            def update_process():
                total_drivers = len(drivers_to_update)
                for i, (driver_values, size, item) in enumerate(drivers_to_update, 1):
                    try:
                        driver_name = driver_values[0][2:]
                        
                        # Обновляем статус
                        progress_label.config(text=f"Обновление драйвера: {driver_name}")
                        status_label.config(text=f"Прогресс: {i}/{total_drivers}")
                        progress_bar['value'] = (i / total_drivers) * 100
                        
                        # Получаем информацию о драйвере
                        success, message = self.driver_updater.update_driver(drivers_info.get(driver_name))
                        
                        if success:
                            # Обновляем информацию в списке
                            self.drivers_list.item(item, values=(
                                driver_values[0],  # Сохраняем оригинальное имя с чекбоксом
                                "Обновлено",
                                datetime.now().strftime("%Y-%m-%d"),
                                "✓ Актуальная версия"
                            ), tags=('current_version',))
                        else:
                            messagebox.showerror("Ошибка", 
                                f"Не удалось обновить драйвер {driver_name}:\n{message}")
                    
                    except Exception as e:
                        messagebox.showerror("Ошибка", 
                            f"Не удалось обновить драйвер {driver_name}:\n{str(e)}")
                
                # Завершаем процесс
                progress_window.after(1000, progress_window.destroy)
                messagebox.showinfo("Готово", 
                                  f"Обновление завершено.\nОбновлено драйверов: {total_drivers}")
                self.update_selection_counter()
            
            # Запускаем процесс обновления в отдельном потоке
            threading.Thread(target=update_process, daemon=True).start()

    def update_selection_counter(self, event=None):
        """Обновление счетчика выбранных драйверов"""
        count = 0
        for item in self.drivers_list.selection():
            driver_info = self.drivers_list.item(item)
            # Проверяем, что драйвер требует обновления
            if "Актуальная версия" not in driver_info['values'][3]:
                count += 1
        self.update_driver_button.configure(text=f"⬇ Обновить выбранные драйверы ({count})")

    def clear_search_placeholder(self, event):
        """Очистка плейсхолдера при фокусе"""
        if self.search_entry.get() == "Поиск драйвера...":
            self.search_entry.delete(0, tk.END)

    def restore_search_placeholder(self, event):
        """Восстановление плейсхолдера при потере фокуса"""
        if not self.search_entry.get():
            self.search_entry.insert(0, "Поиск драйвера...")

    def filter_drivers(self, *args):
        """Фильтрация драйверов по поисковому запросу"""
        search_text = self.search_var.get().lower()
        
        # Если поле поиска пустое или содержит плейсхолдер - показываем все драйверы
        if not search_text or search_text == "поиск драйвера...":
            for item in self.drivers_list.get_children():
                self.drivers_list.item(item, tags=self.drivers_list.item(item)['tags'])
            return
        
        # Если введено меньше 2 символов - не фильтруем
        if len(search_text) < 2:
            return
            
        # Перебираем все элементы и скрываем/показываем их в зависимости от поиска
        for item in self.drivers_list.get_children():
            values = self.drivers_list.item(item)['values']
            if values:
                driver_name = values[0].lower()  # Название драйвера
                
                # Проверяем совпадение
                if search_text in driver_name:
                    # Показываем драйвер с его оригинальными тегами
                    original_tags = [tag for tag in self.drivers_list.item(item)['tags'] 
                                  if tag != 'hidden']
                    self.drivers_list.item(item, tags=original_tags)
                else:
                    # Скрываем драйвер
                    self.drivers_list.item(item, tags=['hidden'])

    def select_all_drivers(self):
        """Выбор всех драйверов, требующих обновления"""
        for item in self.drivers_list.get_children():
            values = self.drivers_list.item(item)['values']
            if "Актуальная версия" not in values[3]:  # Если драйвер требует обновления
                self.drivers_list.selection_add(item)
                # Обновляем чекбокс
                values = list(values)
                values[0] = values[0].replace('☐', '☑')
                self.drivers_list.item(item, values=values)
        self.update_selection_counter()

    def deselect_all_drivers(self):
        """Отмена выбора всех драйверов"""
        for item in self.drivers_list.get_children():
            self.drivers_list.selection_remove(item)
            # Обновляем чекбокс
            values = list(self.drivers_list.item(item)['values'])
            values[0] = values[0].replace('☑', '☐')
            self.drivers_list.item(item, values=values)
        self.update_selection_counter()

    def analyze_upgrade(self):
        """Анализ возможностей апгрейда ПК"""
        self.upgrade_text.delete(1.0, tk.END)
        self.upgrade_text.insert(tk.END, "🔍 Анализ конфигурации...\n\n")
        
        try:
            import wmi
            w = wmi.WMI()
            
            # Получаем информацию о процессоре
            cpu_info = w.Win32_Processor()[0]
            cpu_name = cpu_info.Name.strip()
            
            # Получаем информацию о видеокарте
            gpu_info = w.Win32_VideoController()[0]
            gpu_name = gpu_info.Name.strip()
            
            self.upgrade_text.insert(tk.END, f"Текущая конфигурация:\n")
            self.upgrade_text.insert(tk.END, f"CPU: {cpu_name}\n")
            self.upgrade_text.insert(tk.END, f"GPU: {gpu_name}\n\n")
            
            # Получаем рекомендации
            from hardware_db.compatibility import get_upgrade_recommendations
            recommendations = get_upgrade_recommendations(cpu_name, gpu_name)
            
            if not recommendations['cpu'] and not recommendations['gpu']:
                self.upgrade_text.insert(tk.END, 
                    "⚠️ Не удалось определить модели компонентов.\n"
                    "Проверьте правильность определения оборудования.\n")
                return
            
            if recommendations['bottleneck']:
                bottleneck = recommendations['bottleneck']
                severity = int(bottleneck['severity'] * 100)
                
                self.upgrade_text.insert(tk.END, f"⚠️ Обнаружено узкое место:\n")
                if bottleneck['component'] == 'cpu':
                    self.upgrade_text.insert(tk.END, 
                        f"Процессор ограничивает производительность видеокарты на {severity}%\n\n")
                    
                    self.upgrade_text.insert(tk.END, "Рекомендуемые процессоры для апгрейда:\n")
                    for cpu in recommendations['cpu']:
                        self.upgrade_text.insert(tk.END, f"• {cpu}\n")
                else:
                    self.upgrade_text.insert(tk.END,
                        f"Видеокарта ограничивает производительность процессора на {severity}%\n\n")
                    
                    self.upgrade_text.insert(tk.END, "Рекомендуемые видеокарты для апгрейда:\n")
                    for gpu in recommendations['gpu']:
                        self.upgrade_text.insert(tk.END, f"• {gpu}\n")
            else:
                self.upgrade_text.insert(tk.END, 
                    "✓ Компоненты системы хорошо сбалансированы.\n"
                    "Существенных узких мест не обнаружено.\n")
            
        except Exception as e:
            self.upgrade_text.insert(tk.END, f"❌ Ошибка при анализе: {str(e)}")

if __name__ == "__main__":
    app = SystemAnalyzer()
    app.mainloop() 