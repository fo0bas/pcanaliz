import os
import sys
import pythoncom
import struct
from typing import Dict, Optional
import psutil
import time
import win32com.client
import subprocess

# Проверяем и устанавливаем необходимые пакеты
def install_required_packages():
    try:
        import wmi
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wmi", "pywin32"])
        try:
            import wmi
        except ImportError:
            print("Failed to install WMI module")
            return None
    return wmi

# Инициализируем WMI
wmi_module = install_required_packages()
if not wmi_module:
    print("WMI module is not available. Some features will be limited.")

# Глобальные объекты WMI
WMI = None
WMI_WMI = None

def initialize_wmi():
    global WMI, WMI_WMI, wmi_module
    if wmi_module:
        try:
            pythoncom.CoInitialize()
            WMI = wmi_module.WMI()
            WMI_WMI = wmi_module.WMI(namespace="root\\WMI")
            return True
        except Exception as e:
            print(f"Failed to initialize WMI: {e}")
            WMI = None
            WMI_WMI = None
    return False

# Инициализируем WMI при импорте модуля
initialize_wmi()

class SmartAttribute:
    def __init__(self, raw_data):
        self.id = raw_data[0]
        self.flags = struct.unpack("<H", raw_data[1:3])[0]
        self.value = raw_data[3]
        self.worst = raw_data[4]
        self.raw = struct.unpack("<H", raw_data[5:7])[0]
        self.raw_value = struct.unpack("<Q", raw_data[5:13])[0]

def get_smart_data(device_id: str) -> Dict:
    """Получение SMART-данных для диска"""
    if not wmi_module or not WMI:
        return {
            'status': 'Unknown',
            'temperature': 0,
            'power_on_hours': 0,
            'reallocated_sectors': 0,
            'pending_sectors': 0,
            'uncorrectable_sectors': 0,
            'start_stop_count': 0,
            'load': 0,
            'health': 100,
            'smart_attributes': {}
        }

    try:
        # Переинициализируем WMI для текущего потока
        initialize_wmi()
        
        # Получаем номер диска
        disk_number = int(device_id.split('PHYSICALDRIVE')[-1])
        
        # Получаем информацию о диске
        disk = WMI.Win32_DiskDrive(Index=disk_number)[0]
        
        # Получаем SMART данные
        smart_data = {}
        try:
            for item in WMI_WMI.MSStorageDriver_ATAPISmartData():
                if item.InstanceName.split('_')[0] == str(disk_number):
                    vendor_specific = item.VendorSpecific
                    for i in range(0, len(vendor_specific), 12):
                        attr = SmartAttribute(vendor_specific[i:i+12])
                        smart_data[attr.id] = attr
        except Exception as e:
            print(f"Error getting SMART data: {e}")

        # Определяем тип диска
        is_ssd = _is_ssd(disk)
        
        # Формируем результат
        result = {
            'status': _get_disk_status(smart_data),
            'temperature': _get_disk_temperature(smart_data),
            'power_on_hours': _get_power_on_hours(smart_data),
            'reallocated_sectors': _get_attribute_raw(smart_data, 5),
            'pending_sectors': _get_attribute_raw(smart_data, 197),
            'uncorrectable_sectors': _get_attribute_raw(smart_data, 198),
            'start_stop_count': _get_attribute_raw(smart_data, 4),
            'load': _get_disk_load(disk_number),
            'health': _calculate_health(smart_data, is_ssd),
            'model': disk.Model,
            'serial': disk.SerialNumber,
            'interface': disk.InterfaceType
        }
        
        return result
        
    except Exception as e:
        print(f"Error in get_smart_data: {e}")
        return {
            'status': 'Error',
            'temperature': 0,
            'power_on_hours': 0,
            'reallocated_sectors': 0,
            'pending_sectors': 0,
            'uncorrectable_sectors': 0,
            'start_stop_count': 0,
            'load': 0,
            'health': 0,
            'model': 'Unknown',
            'serial': 'Unknown',
            'interface': 'Unknown'
        }
    finally:
        pythoncom.CoUninitialize()

def _collect_all_smart_attributes(smart_data: Dict) -> Dict:
    """Сбор всех доступных SMART-атрибутов"""
    attributes = {}
    important_attrs = {
        1: "Raw Read Error Rate",
        5: "Reallocated Sector Count",
        7: "Seek Error Rate",
        9: "Power-On Hours",
        10: "Spin Retry Count",
        12: "Power Cycle Count",
        184: "End-to-End Error",
        187: "Reported Uncorrectable Errors",
        188: "Command Timeout",
        190: "Airflow Temperature",
        194: "Temperature",
        196: "Reallocation Event Count",
        197: "Current Pending Sector Count",
        198: "Offline Uncorrectable Sector Count",
        199: "Ultra DMA CRC Error Count",
        200: "Multi-Zone Error Rate"
    }
    
    for attr_id, attr_name in important_attrs.items():
        if attr_id in smart_data:
            attributes[attr_name] = {
                'id': attr_id,
                'value': smart_data[attr_id].value,
                'worst': smart_data[attr_id].worst,
                'raw': smart_data[attr_id].raw_value
            }
    
    return attributes

def _calculate_health(smart_data: Dict, is_ssd: bool) -> int:
    """Расчет общего здоровья диска в процентах"""
    if not smart_data:
        return 100
    
    health = 100
    deductions = []
    
    # Критические атрибуты
    critical_checks = [
        ('Reallocated Sector Count', 10, 30),
        ('Current Pending Sector Count', 10, 30),
        ('Offline Uncorrectable Sector Count', 5, 30)
    ]
    
    for attr_name, threshold, max_deduction in critical_checks:
        if attr_name in smart_data:
            value = smart_data[attr_name]['raw']
            if value > 0:
                deduction = min(max_deduction, (value / threshold) * max_deduction)
                deductions.append(('Critical', deduction, f"{attr_name}: {value}"))
    
    # Температура
    temp = _get_disk_temperature(smart_data)
    if temp > 0:  # Проверяем, что температура получена
        if temp > 60:
            deductions.append(('Temperature', min(30, (temp - 60) * 3), f"High temperature: {temp}°C"))
        elif temp > 50:
            deductions.append(('Temperature', min(15, (temp - 50) * 1.5), f"Elevated temperature: {temp}°C"))
    
    # Время работы
    power_on_hours = _get_power_on_hours(smart_data)
    power_on_years = power_on_hours / (24 * 365)
    if power_on_years > 5:
        deductions.append(('Age', min(20, (power_on_years - 5) * 4), f"Age: {power_on_years:.1f} years"))
    elif power_on_years > 3:
        deductions.append(('Age', min(10, (power_on_years - 3) * 2), f"Age: {power_on_years:.1f} years"))
    
    # Специфичные проверки для SSD
    if is_ssd and 'remaining_life' in smart_data:
        remaining_life = smart_data['remaining_life']['value']
        if remaining_life < 50:
            deductions.append(('SSD Life', (100 - remaining_life) / 2, f"SSD Life: {remaining_life}%"))
    
    # Применяем все вычеты
    total_deduction = 0
    for category, value, reason in sorted(deductions, key=lambda x: x[1], reverse=True):
        total_deduction += value
        print(f"Health deduction: {category} = -{value:.1f} ({reason})")
    
    health = max(0, min(100, 100 - total_deduction))
    return int(health)

def _get_attribute_value(smart_data: Dict, attribute_id: int) -> int:
    """Получение нормализованного значения SMART-атрибута"""
    if attribute_id in smart_data:
        return smart_data[attribute_id].value
    return 0

def _get_attribute_raw(smart_data: Dict, attribute_id: int) -> int:
    """Получение сырого значения SMART-атрибута"""
    if attribute_id in smart_data:
        return smart_data[attribute_id].raw_value
    return 0

def _get_disk_temperature(smart_data: Dict) -> int:
    """Получение температуры диска"""
    try:
        if WMI_WMI:  # Проверяем наличие WMI
            # Пробуем получить температуру через WMI
            for sensor in WMI_WMI.MSAcpi_ThermalZoneTemperature():
                temp = int(sensor.CurrentTemperature / 10.0 - 273.15)
                if 20 <= temp <= 100:
                    return temp
        
        # Если не удалось получить через WMI, пробуем SMART
        temp_attributes = [194, 190, 260, 192]
        temperatures = []
        
        for attr_id in temp_attributes:
            smart_temp = _get_attribute_raw(smart_data, attr_id)
            if 20 <= smart_temp <= 100:
                temperatures.append(smart_temp)
        
        if temperatures:
            return int(sum(temperatures) / len(temperatures))
            
        # Если не удалось получить температуру, пробуем через Win32_TemperatureProbe
        if WMI:
            for probe in WMI.Win32_TemperatureProbe():
                if probe.CurrentReading and 20 <= probe.CurrentReading <= 100:
                    return probe.CurrentReading
                
        return 0
    except Exception as e:
        print(f"Error getting temperature: {str(e)}")
        return 0

def _get_power_on_hours(smart_data: Dict) -> int:
    """Получение времени работы диска"""
    return _get_attribute_raw(smart_data, 9)

def _get_disk_status(smart_data: Dict) -> str:
    """Определение статуса диска на основе SMART-данных"""
    if not smart_data:
        return "Unknown"
    
    critical_attributes = {
        5: 10,   # Reallocated Sectors Count
        197: 10, # Current Pending Sectors
        198: 10  # Offline Uncorrectable
    }
    
    for attr_id, threshold in critical_attributes.items():
        if _get_attribute_raw(smart_data, attr_id) > threshold:
            return "Critical"
    
    warning_attributes = {
        5: 0,    # Any reallocated sectors
        197: 0,  # Any pending sectors
        198: 0,  # Any uncorrectable sectors
        194: 55  # Temperature threshold
    }
    
    for attr_id, threshold in warning_attributes.items():
        if _get_attribute_raw(smart_data, attr_id) > threshold:
            return "Warning"
    
    return "OK"

def _get_disk_load(disk_number: int) -> float:
    """Получение текущей нагрузки на диск"""
    try:
        # Делаем несколько замеров для точности
        samples = []
        
        for _ in range(3):
            disk_io = psutil.disk_io_counters(perdisk=True)
            physical_disks = {k: v for k, v in disk_io.items() if k.startswith('PhysicalDrive')}
            
            disk_name = f'PhysicalDrive{disk_number}'
            if disk_name in physical_disks:
                io = physical_disks[disk_name]
                # Сохраняем текущие значения
                samples.append((io.read_bytes + io.write_bytes, time.time()))
            time.sleep(0.5)  # Ждем полсекунды между замерами
        
        if len(samples) >= 2:
            # Вычисляем среднюю скорость между замерами
            speeds = []
            for i in range(1, len(samples)):
                bytes_diff = samples[i][0] - samples[i-1][0]
                time_diff = samples[i][1] - samples[i-1][1]
                if time_diff > 0:
                    speed = bytes_diff / time_diff / (1024 * 1024)  # МБ/с
                    speeds.append(speed)
            
            if speeds:
                return sum(speeds) / len(speeds)
    except Exception as e:
        print(f"Error getting disk load: {str(e)}")
    return 0.0

def _is_ssd(disk) -> bool:
    """Определение является ли диск SSD"""
    try:
        model = disk.Model.lower()
        desc = disk.Description.lower()
        media_type = getattr(disk, 'MediaType', '').lower()
        
        ssd_keywords = ['ssd', 'solid state', 'nvme', 'm.2']
        return any(keyword in text for keyword in ssd_keywords 
                  for text in [model, desc, media_type])
    except:
        return False

def get_disk_health_status(device_id: str) -> str:
    """
    Получение общего статуса здоровья диска
    
    Args:
        device_id: Идентификатор устройства
        
    Returns:
        Строка с состоянием: "OK", "Warning" или "Critical"
    """
    try:
        smart_data = get_smart_data(device_id)
        
        if smart_data['status'] == 'Critical':
            return 'Critical'
        elif smart_data['status'] == 'Warning':
            return 'Warning'
        elif smart_data['temperature'] > 55:
            return 'Warning'
        
        return 'OK'
    except:
        return 'Unknown'

def get_disk_temperature(device_id: str) -> Optional[int]:
    """
    Получение температуры диска
    
    Args:
        device_id: Идентификатор устройства
        
    Returns:
        Температура в градусах Цельсия или None в случае ошибки
    """
    try:
        smart_data = get_smart_data(device_id)
        return smart_data['temperature']
    except:
        return None 