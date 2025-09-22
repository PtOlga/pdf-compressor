#!/usr/bin/env python3
"""
Утилиты для PDF компрессора
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import yaml
import json
from colorama import init, Fore, Style

# Инициализация colorama для Windows
init()

def setup_logging(log_file: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Настройка логирования с цветным выводом и файлом
    """
    # Создаем директорию для логов
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Настройка форматирования
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Базовая конфигурация
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[]
    )
    
    logger = logging.getLogger()
    logger.handlers.clear()
    
    # Консольный обработчик с цветами
    console_handler = ColoredConsoleHandler()
    console_handler.setFormatter(ColoredFormatter(log_format, date_format))
    logger.addHandler(console_handler)
    
    # Файловый обработчик
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(file_handler)
    
    return logger


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветным выводом"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }
    
    def format(self, record):
        # Сохраняем оригинальное сообщение
        original_msg = record.getMessage()
        
        # Добавляем эмодзи для разных типов сообщений
        emojis = {
            'DEBUG': '🔍',
            'INFO': '📄' if 'Processing' in original_msg else 
                   '✅' if any(word in original_msg for word in ['Completed', 'Success', 'Done']) else
                   '📊' if 'Stats' in original_msg else '📋',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '💥'
        }
        
        emoji = emojis.get(record.levelname, '📋')
        record.msg = f"{emoji} {original_msg}"
        
        # Форматируем с цветом
        color = self.COLORS.get(record.levelname, '')
        formatted = super().format(record)
        
        if color:
            # Применяем цвет только к уровню логирования
            parts = formatted.split('|')
            if len(parts) >= 2:
                parts[1] = f"{color}{parts[1].strip()}{Style.RESET_ALL}"
                formatted = ' | '.join(parts)
        
        return formatted


class ColoredConsoleHandler(logging.StreamHandler):
    """Обработчик для цветного вывода в консоль"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def format_file_size(bytes_size: int) -> str:
    """
    Форматирование размера файла в читаемый вид
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Форматирование длительности в читаемый вид
    """
    if seconds < 60:
        return f"{seconds:.1f} сек"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}м {remaining_seconds:.0f}с"
    
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    
    return f"{hours}ч {remaining_minutes}м"


def calculate_savings(original_size: int, compressed_size: int) -> Dict[str, Any]:
    """
    Вычисление статистики сжатия
    """
    if original_size == 0:
        return {
            'bytes_saved': 0,
            'percent_saved': 0,
            'compression_ratio': 0,
            'size_reduction': "0%"
        }
    
    bytes_saved = original_size - compressed_size
    percent_saved = (bytes_saved / original_size) * 100
    compression_ratio = original_size / compressed_size if compressed_size > 0 else float('inf')
    
    return {
        'bytes_saved': bytes_saved,
        'percent_saved': percent_saved,
        'compression_ratio': compression_ratio,
        'size_reduction': f"{percent_saved:.1f}%"
    }


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """
    Загрузка конфигурации из YAML файла
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # Валидация обязательных секций
        required_sections = ['folders', 'compression', 'limits']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Отсутствует обязательная секция в конфигурации: {section}")
        
        return config
        
    except yaml.YAMLError as e:
        raise ValueError(f"Ошибка парсинга YAML конфигурации: {e}")


def save_statistics(stats: Dict[str, Any], output_path: str = "temp/logs/stats.json"):
    """
    Сохранение статистики в JSON файл
    """
    stats_file = Path(output_path)
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Добавляем timestamp
    stats['timestamp'] = datetime.now().isoformat()
    stats['date'] = datetime.now().strftime('%Y-%m-%d')
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def load_statistics(stats_path: str = "temp/logs/stats.json") -> Dict[str, Any]:
    """
    Загрузка статистики из JSON файла
    """
    stats_file = Path(stats_path)
    
    if not stats_file.exists():
        return {}
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def validate_file_path(file_path: str) -> bool:
    """
    Проверка корректности пути к файлу
    """
    try:
        path = Path(file_path)
        return path.suffix.lower() == '.pdf' and not any(
            pattern in path.name.lower() 
            for pattern in ['compressed', '_comp', 'optimized', '_small', 'temp_']
        )
    except Exception:
        return False


def create_temp_dirs():
    """
    Создание временных директорий для работы
    """
    temp_dirs = [
        'temp/input',
        'temp/output',
        'temp/logs',
        'temp/backup'
    ]
    
    for dir_path in temp_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


def cleanup_temp_files(max_age_hours: int = 24):
    """
    Очистка старых временных файлов
    """
    temp_dir = Path('temp')
    if not temp_dir.exists():
        return
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    for file_path in temp_dir.rglob('*'):
        if file_path.is_file():
            try:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_path.unlink()
            except Exception:
                pass  # Игнорируем ошибки при удалении


def get_system_info() -> Dict[str, Any]:
    """
    Получение информации о системе
    """
    import platform
    import shutil
    
    return {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'available_space_gb': round(shutil.disk_usage('.').free / (1024**3), 2),
        'ghostscript_available': shutil.which('gs') is not None,
        'qpdf_available': shutil.which('qpdf') is not None
    }


def print_banner():
    """
    Вывод баннера приложения
    """
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════════╗
║                     PDF BATCH COMPRESSOR                     ║
║                    🗜️  Mega Cloud Edition                    ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
{Fore.GREEN}Система готова к работе! Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}
"""
    print(banner)


if __name__ == "__main__":
    # Тестирование утилит
    print_banner()
    logger = setup_logging(level="DEBUG")
    
    logger.debug("Это отладочное сообщение")
    logger.info("Processing файла test.pdf")
    logger.info("Completed успешно!")
    logger.warning("Предупреждение о размере файла")
    logger.error("Ошибка сжатия файла")
    
    print(f"Размер файла: {format_file_size(15678234)}")
    print(f"Длительность: {format_duration(3725.5)}")
    
    savings = calculate_savings(1000000, 350000)
    print(f"Экономия: {savings}")
