import os
import sys
import psutil
import time
from typing import Dict, List
import pythoncom
import win32com.client
import wmi  # Добавляем глобальный импорт wmi

class DiskInfo:
    def __init__(self):
        try:
            # Инициализируем COM для текущего потока
            pythoncom.CoInitialize()
            
            # Создаем основной WMI объект
            self.wmi = wmi.WMI()
            self.wmi_available = True
            
            # Создаем SMART WMI объект с правильными правами
            self.wmi_smart = None
            try:
                self.wmi_smart = wmi.WMI(namespace="root\\WMI", privileges=["Security"])
            except Exception as e:
                print(f"Failed to initialize SMART WMI: {e}")
            
            # Создаем CIMV2 WMI объект
            self.wmi_cimv2 = None
            try:
                self.wmi_cimv2 = wmi.WMI(namespace="root\\CIMV2")
            except Exception as e:
                print(f"Failed to initialize CIMV2 WMI: {e}")
            
        except Exception as e:
            print(f"Failed to initialize WMI: {e}")
            self.wmi_available = False
            self.wmi = None
            self.wmi_smart = None
            self.wmi_cimv2 = None
        finally:
            pythoncom.CoUninitialize()

    def get_disk_info(self) -> List[Dict]:
        """Получение информации о всех дисках"""
        disks_info = []
        
        try:
            if not self.wmi_available:
                return []

            # Получаем физические диски
            physical_disks = self.wmi.Win32_DiskDrive()
            
            for disk in physical_disks:
                try:
                    disk_info = {
                        'name': disk.Caption,
                        'size': self._format_size(disk.Size),
                        'model': disk.Model,
                        'serial': disk.SerialNumber,
                        'interface': disk.InterfaceType,
                        'status': self._get_disk_status(disk),
                        'temperature': self._get_disk_temperature(disk),
                        'load': self._get_disk_load(disk.Index),
                        'estimated_lifetime': self._estimate_lifetime(disk),
                        'score': self._calculate_disk_score(disk)
                    }
                    disks_info.append(disk_info)
                except Exception as e:
                    print(f"Error getting info for disk {disk.Caption}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error getting disk info: {e}")
        
        return disks_info

    def _format_size(self, size: str) -> str:
        """Форматирование размера диска"""
        try:
            size_bytes = int(size)
            if size_bytes >= 1099511627776:  # TB
                return f"{size_bytes/1099511627776:.1f} TB"
            else:  # GB
                return f"{size_bytes/1073741824:.1f} GB"
        except:
            return "N/A"

    def _get_disk_temperature(self, disk) -> int:
        """Получение температуры диска"""
        try:
            temperatures = []
            
            # 1. Пробуем получить через SMART
            if self.wmi_smart:
                try:
                    pythoncom.CoInitialize()
                    # Используем более надежный способ получения SMART данных
                    query = (f"SELECT * FROM MSStorageDriver_ATAPISmartData "
                            f"WHERE InstanceName LIKE '%PHYSICALDRIVE{disk.Index}%'")
                    smart_data = self.wmi_smart.query(query)
                    
                    for item in smart_data:
                        if hasattr(item, 'VendorSpecific'):
                            vendor_data = item.VendorSpecific
                            if vendor_data and len(vendor_data) >= 512:  # Проверяем размер данных
                                # Температурные атрибуты SMART
                                smart_temp_attrs = {
                                    194: 'Temperature',
                                    190: 'Airflow_Temperature',
                                    231: 'Temperature_2',
                                    192: 'Temperature_3'
                                }
                                
                                for attr_id, name in smart_temp_attrs.items():
                                    try:
                                        temp_index = attr_id * 12
                                        if temp_index + 5 < len(vendor_data):
                                            temp = vendor_data[temp_index + 5]
                                            if 20 <= temp <= 100:
                                                temperatures.append(temp)
                                    except:
                                        continue
                except Exception as e:
                    print(f"Error getting SMART temperature: {e}")
                finally:
                    pythoncom.CoUninitialize()

            # 2. Пробуем через прямые атрибуты диска
            try:
                pythoncom.CoInitialize()
                # Проверяем основные атрибуты температуры
                temp_attrs = ['Temperature', 'DeviceTemperature', 'Temperature_Celsius']
                for attr in temp_attrs:
                    try:
                        if hasattr(disk, attr):
                            temp = int(getattr(disk, attr))
                            if 20 <= temp <= 100:
                                temperatures.append(temp)
                    except:
                        continue
                    
                # Пробуем получить через датчики температуры
                if self.wmi_cimv2:
                    sensors = self.wmi_cimv2.query(
                        "SELECT * FROM Win32_TemperatureProbe WHERE Status='OK'"
                    )
                    for sensor in sensors:
                        try:
                            if hasattr(sensor, 'CurrentReading'):
                                temp = int(sensor.CurrentReading)
                                if 20 <= temp <= 100:
                                    temperatures.append(temp)
                        except:
                            continue
            except Exception as e:
                print(f"Error getting disk attributes temperature: {e}")
            finally:
                pythoncom.CoUninitialize()

            # Анализируем собранные температуры
            if temperatures:
                # Фильтруем выбросы
                valid_temps = [t for t in temperatures if 20 <= t <= 100]
                if valid_temps:
                    return round(sum(valid_temps) / len(valid_temps))

            # Если не удалось получить реальную температуру, используем оценку
            is_ssd = self._is_ssd(disk)
            load = self._get_disk_load(disk.Index)
            
            # Базовая температура
            base_temp = 35 if is_ssd else 40
            # Добавляем нагрузку (максимум +15 градусов при полной нагрузке)
            load_temp = (load / 100) * 15
            
            return round(base_temp + load_temp)

        except Exception as e:
            print(f"Error in temperature measurement: {e}")
            return 40

    def _get_disk_load(self, disk_index: int) -> float:
        """Получение текущей нагрузки на диск в процентах"""
        try:
            # Делаем больше замеров с меньшим интервалом для точности
            samples = []
            initial_counters = {}
            disk_name = f'PhysicalDrive{disk_index}'
            
            # Получаем начальные значения всех счетчиков
            disk_io = psutil.disk_io_counters(perdisk=True)
            if disk_name in disk_io:
                io = disk_io[disk_name]
                initial_counters = {
                    'read_bytes': io.read_bytes,
                    'write_bytes': io.write_bytes,
                    'read_count': io.read_count,
                    'write_count': io.write_count,
                    'read_time': io.read_time,
                    'write_time': io.write_time,
                    'timestamp': time.time() * 1000
                }
            
            # Делаем 10 замеров с интервалом 0.1 секунды
            for _ in range(10):
                disk_io = psutil.disk_io_counters(perdisk=True)
                if disk_name in disk_io:
                    io = disk_io[disk_name]
                    current_time = time.time() * 1000  # в миллисекундах
                    
                    # Собираем все метрики
                    sample = {
                        'read_bytes': io.read_bytes,
                        'write_bytes': io.write_bytes,
                        'read_count': io.read_count,
                        'write_count': io.write_count,
                        'read_time': io.read_time,
                        'write_time': io.write_time,
                        'timestamp': current_time
                    }
                    samples.append(sample)
                time.sleep(0.1)  # Маленький интервал для точности

            if samples and initial_counters:
                # Вычисляем общую нагрузку на основе нескольких метрик
                total_time = samples[-1]['timestamp'] - initial_counters['timestamp']
                if total_time > 0:
                    # Вычисляем разницу в байтах
                    bytes_diff = (
                        (samples[-1]['read_bytes'] - initial_counters['read_bytes']) +
                        (samples[-1]['write_bytes'] - initial_counters['write_bytes'])
                    )
                    # Вычисляем разницу в операциях
                    ops_diff = (
                        (samples[-1]['read_count'] - initial_counters['read_count']) +
                        (samples[-1]['write_count'] - initial_counters['write_count'])
                    )
                    # Вычисляем время активности диска
                    active_time = (
                        (samples[-1]['read_time'] - initial_counters['read_time']) +
                        (samples[-1]['write_time'] - initial_counters['write_time'])
                    )
                    
                    # Вычисляем нагрузку как комбинацию метрик:
                    # 1. Процент активного времени
                    time_utilization = min(100, (active_time / total_time) * 100)
                    
                    # 2. Нагрузка по количеству операций (IOPS)
                    iops = (ops_diff / (total_time / 1000))  # операций в секунду
                    iops_utilization = min(100, (iops / 1000) * 100)  # нормализуем до 100%
                    
                    # 3. Нагрузка по пропускной способности
                    bandwidth = bytes_diff / (total_time / 1000)  # байт в секунду
                    bandwidth_utilization = min(100, (bandwidth / (100 * 1024 * 1024)) * 100)
                    
                    # Комбинируем метрики с весами
                    combined_load = (
                        time_utilization * 0.5 +    # 50% вес времени активности
                        iops_utilization * 0.3 +    # 30% вес IOPS
                        bandwidth_utilization * 0.2  # 20% вес пропускной способности
                    )
                    
                    # Убеждаемся, что нагрузка никогда не бывает совсем нулевой
                    return max(0.1, round(combined_load, 2))
                
        except Exception as e:
            print(f"Error getting disk load: {e}")
        return 0.1  # Минимальное значение при ошибке

    def _get_disk_status(self, disk) -> str:
        """Определение статуса диска"""
        try:
            if disk.Status == "OK":
                return "Исправен"
            elif disk.Status == "Degraded":
                return "Внимание"
            else:
                return "Критическое состояние"
        except:
            return "Неизвестно"

    def _estimate_lifetime(self, disk) -> int:
        """Оценка оставшегося времени работы в днях"""
        try:
            power_on_hours = getattr(disk, 'PowerOnHours', 0)
            if power_on_hours:
                # Примерный расчет оставшегося времени
                total_lifetime = 5 * 365  # 5 лет в днях
                used_days = power_on_hours / 24
                remaining_days = total_lifetime - used_days
                return max(0, int(remaining_days))
            return 365  # Возвращаем год по умолчанию
        except:
            return 365

    def _calculate_disk_score(self, disk) -> int:
        """Расчет общей оценки состояния диска по шкале 1-10"""
        try:
            score = 10  # Начальная оценка
            
            # Проверяем статус
            if disk.Status != "OK":
                score -= 3
            
            # Проверяем температуру
            temp = self._get_disk_temperature(disk)
            if temp > 50:
                score -= min(3, (temp - 50) // 5)
            
            # Проверяем время работы
            power_on_hours = getattr(disk, 'PowerOnHours', 0)
            if power_on_hours:
                years = power_on_hours / (24 * 365)
                if years > 3:
                    score -= min(3, int(years - 3))
            
            return max(1, score)
        except:
            return 5  # Средняя оценка при ошибке 

    def _is_ssd(self, disk) -> bool:
        """Определение является ли диск SSD"""
        try:
            # Проверяем по модели
            model = disk.Model.lower() if disk.Model else ''
            desc = disk.Description.lower() if disk.Description else ''
            
            # Ключевые слова для определения SSD
            ssd_keywords = ['ssd', 'solid state', 'nvme', 'm.2', 'pcie']
            
            # Проверяем наличие ключевых слов
            if any(keyword in model or keyword in desc for keyword in ssd_keywords):
                return True
            
            # Проверяем MediaType если доступно
            media_type = getattr(disk, 'MediaType', '').lower()
            if media_type and any(keyword in media_type for keyword in ssd_keywords):
                return True
            
            # Проверяем через SMART атрибуты
            try:
                if self.wmi:
                    wmi_smart = self.wmi.WMI(namespace="root\\wmi")
                    for item in wmi_smart.MSStorageDriver_ATAPISmartData():
                        # Проверяем атрибуты характерные для SSD
                        vendor_data = item.VendorSpecific
                        if vendor_data:
                            # Проверяем атрибут 177 (Wear Leveling Count)
                            wear_index = 177 * 12
                            if wear_index < len(vendor_data):
                                return True
                            # Проверяем атрибут 231 (SSD Life Left)
                            life_index = 231 * 12
                            if life_index < len(vendor_data):
                                return True
            except:
                pass
            
            # Проверяем скорость вращения (0 для SSD)
            try:
                if hasattr(disk, 'Size') and disk.Size:
                    size_gb = float(disk.Size) / (1024**3)
                    if size_gb > 0:  # Реальный диск
                        rotation_rate = getattr(disk, 'RotationRate', None)
                        if rotation_rate == 0 or rotation_rate is None:
                            return True
            except:
                pass
            
            return False
        except Exception as e:
            print(f"Error determining SSD status: {e}")
            # По умолчанию считаем HDD
            return False 