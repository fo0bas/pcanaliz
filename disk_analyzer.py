import wmi
import psutil
import win32com.client
import pythoncom
from typing import Dict, List
import time
import smart_data

class DiskAnalyzer:
    def __init__(self):
        self.wmi = wmi.WMI()
        
    def get_disk_info(self) -> List[Dict]:
        """Получение информации о всех дисках"""
        disks_info = []
        
        # Инициализируем COM для текущего потока
        pythoncom.CoInitialize()
        
        try:
            # Получаем физические диски через WMI
            physical_disks = self.wmi.Win32_DiskDrive()
            
            for disk in physical_disks:
                disk_info = {
                    'name': disk.Caption,
                    'size': self._format_size(disk.Size),
                    'model': disk.Model,
                    'serial': disk.SerialNumber,
                    'interface': disk.InterfaceType,
                    'status': self._get_disk_status(disk),
                    'health': self._get_disk_health(disk),
                    'temperature': self._get_disk_temperature(disk),
                    'load': self._get_disk_load(disk),
                    'estimated_lifetime': self._get_estimated_lifetime(disk),
                    'score': self._calculate_disk_score(disk)
                }
                disks_info.append(disk_info)
                
        finally:
            pythoncom.CoUninitialize()
            
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
    
    def _get_disk_status(self, disk) -> str:
        """Получение статуса диска через SMART"""
        try:
            smart = smart_data.get_smart_data(disk.DeviceID)
            if smart['status'] == 'OK':
                return "Исправен"
            elif smart['status'] == 'Warning':
                return "Внимание"
            else:
                return "Критическое состояние"
        except:
            return "Неизвестно"
    
    def _get_disk_health(self, disk) -> Dict:
        """Получение показателей здоровья диска"""
        try:
            smart = smart_data.get_smart_data(disk.DeviceID)
            return {
                'reallocated_sectors': smart.get('reallocated_sectors', 0),
                'pending_sectors': smart.get('pending_sectors', 0),
                'uncorrectable_sectors': smart.get('uncorrectable_sectors', 0),
                'power_on_hours': smart.get('power_on_hours', 0),
                'start_stop_count': smart.get('start_stop_count', 0)
            }
        except:
            return {}
    
    def _get_disk_temperature(self, disk) -> int:
        """Получение температуры диска"""
        try:
            smart = smart_data.get_smart_data(disk.DeviceID)
            return smart.get('temperature', 0)
        except:
            return 0
    
    def _get_disk_load(self, disk) -> float:
        """Получение текущей нагрузки на диск"""
        try:
            # Получаем статистику использования диска
            disk_io = psutil.disk_io_counters(perdisk=True)
            disk_name = disk.DeviceID.split('\\')[-1]
            if disk_name in disk_io:
                io = disk_io[disk_name]
                # Вычисляем нагрузку на основе активности чтения/записи
                return (io.read_bytes + io.write_bytes) / (1024 * 1024)  # MB/s
        except:
            pass
        return 0.0
    
    def _get_estimated_lifetime(self, disk) -> int:
        """Оценка оставшегося времени работы в днях"""
        try:
            health = self._get_disk_health(disk)
            
            # Базовая оценка на основе SMART-параметров
            base_lifetime = 365 * 2  # 2 года базовой оценки
            
            # Корректируем оценку на основе показателей
            if health:
                # Уменьшаем срок за каждый плохой сектор
                bad_sectors = (health['reallocated_sectors'] + 
                             health['pending_sectors'] + 
                             health['uncorrectable_sectors'])
                
                lifetime_reduction = bad_sectors * 5  # 5 дней за каждый плохой сектор
                
                # Учитываем время работы
                power_on_days = health['power_on_hours'] / 24
                wear_factor = power_on_days / (365 * 5)  # Относительно 5 лет работы
                
                estimated_days = base_lifetime - lifetime_reduction
                estimated_days *= (1 - wear_factor)
                
                return max(0, int(estimated_days))
            
        except:
            pass
        return -1
    
    def _calculate_disk_score(self, disk) -> int:
        """Расчет общей оценки состояния диска по шкале 1-10"""
        try:
            health = self._get_disk_health(disk)
            temperature = self._get_disk_temperature(disk)
            status = self._get_disk_status(disk)
            
            score = 10  # Начальная максимальная оценка
            
            # Снижаем оценку за плохие сектора
            if health:
                bad_sectors = (health['reallocated_sectors'] + 
                             health['pending_sectors'] + 
                             health['uncorrectable_sectors'])
                
                if bad_sectors > 0:
                    score -= min(5, bad_sectors)  # До -5 баллов за сектора
                
                # Учитываем время работы
                power_on_years = health['power_on_hours'] / (24 * 365)
                if power_on_years > 3:
                    score -= min(3, int(power_on_years - 3))  # До -3 баллов за возраст
            
            # Учитываем температуру
            if temperature > 50:  # Критическая температура
                score -= min(3, (temperature - 50) // 5)  # До -3 баллов за температуру
            
            # Учитываем статус
            if status == "Внимание":
                score -= 2
            elif status == "Критическое состояние":
                score -= 5
            
            return max(1, score)  # Минимальная оценка 1
            
        except:
            return 1  # При ошибке возвращаем минимальную оценку 