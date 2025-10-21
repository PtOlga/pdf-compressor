#!/usr/bin/env python3
"""
Отладочный скрипт для диагностики проблем с поиском файлов в Mega
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import get_config
from mega_client import MegaClient
from utils import setup_logging, format_file_size

def debug_mega_files():
    """Отладка файлов в Mega"""
    
    # Настраиваем логирование
    setup_logging(level="DEBUG")
    logger = __import__('logging').getLogger(__name__)
    
    try:
        logger.info("=" * 60)
        logger.info("🔍 ОТЛАДКА MEGA КЛИЕНТА")
        logger.info("=" * 60)
        
        # Загружаем конфигурацию
        config = get_config()
        logger.info(f"\n📋 Конфигурация:")
        logger.info(f"   Входная папка: {config.input_folder}")
        logger.info(f"   Выходная папка: {config.output_folder}")
        logger.info(f"   Мин. размер файла: {config.min_file_size_kb} KB")
        logger.info(f"   Макс. размер файла: {config.max_file_size_mb} MB")
        logger.info(f"   Паттерны пропуска: {config.skip_patterns}")
        
        # Подключаемся к Mega
        logger.info(f"\n🔐 Подключение к Mega...")
        client = MegaClient()
        
        # Получаем ВСЕ файлы в аккаунте
        logger.info(f"\n📂 Получение всех файлов из Mega...")
        all_files = client.mega.get_files()
        
        logger.info(f"📊 Всего объектов в Mega: {len(all_files)}")
        
        # Анализируем структуру
        logger.info(f"\n📁 Структура папок и файлов:")
        logger.info(f"{'ID':<20} {'Тип':<6} {'Имя':<40} {'Размер':<12} {'Путь'}")
        logger.info("-" * 120)
        
        for file_id, file_info in list(all_files.items())[:50]:  # Первые 50
            if not isinstance(file_info, dict):
                continue
            
            if 'a' not in file_info:
                continue
            
            name = file_info['a'].get('n', '?')
            file_type = file_info.get('t', '?')
            size = file_info.get('s', 0)
            
            # Определяем тип
            if file_type == 1:
                type_str = "ПАПКА"
            elif file_type == 0:
                type_str = "ФАЙЛ"
            else:
                type_str = f"ТИП{file_type}"
            
            # Получаем полный путь
            file_path = client._get_file_path(file_id, all_files)
            
            size_str = format_file_size(size) if size > 0 else "-"
            
            logger.info(f"{file_id:<20} {type_str:<6} {name:<40} {size_str:<12} {file_path}")
        
        # Ищем PDF файлы в целевой папке
        logger.info(f"\n🔎 Поиск PDF файлов в папке: {config.input_folder}")
        logger.info("-" * 120)
        
        pdf_count = 0
        for file_id, file_info in all_files.items():
            if not isinstance(file_info, dict) or 'a' not in file_info:
                continue
            
            name = file_info['a'].get('n', '')
            file_path = client._get_file_path(file_id, all_files)
            size = file_info.get('s', 0)
            
            # Проверяем, это ли PDF в целевой папке
            if file_path and file_path.startswith(config.input_folder.rstrip('/')):
                if name.lower().endswith(('.pdf', '.PDF')):
                    pdf_count += 1
                    logger.info(f"✅ Найден PDF: {name}")
                    logger.info(f"   Путь: {file_path}")
                    logger.info(f"   Размер: {format_file_size(size)}")
                    logger.info(f"   ID: {file_id}")
                    logger.info("")
        
        if pdf_count == 0:
            logger.warning(f"⚠️ PDF файлы не найдены в папке {config.input_folder}")
            
            # Проверяем, существует ли сама папка
            logger.info(f"\n🔍 Проверка существования папки...")
            folder_found = False
            for file_id, file_info in all_files.items():
                if not isinstance(file_info, dict) or 'a' not in file_info:
                    continue
                
                name = file_info['a'].get('n', '')
                file_path = client._get_file_path(file_id, all_files)
                file_type = file_info.get('t', 0)
                
                if file_path == config.input_folder and file_type == 1:
                    logger.info(f"✅ Папка найдена: {file_path}")
                    folder_found = True
                    break
            
            if not folder_found:
                logger.error(f"❌ Папка {config.input_folder} не найдена в Mega!")
                logger.info(f"\n💡 Доступные папки:")
                for file_id, file_info in all_files.items():
                    if not isinstance(file_info, dict) or 'a' not in file_info:
                        continue
                    
                    file_type = file_info.get('t', 0)
                    if file_type == 1:  # Папка
                        name = file_info['a'].get('n', '')
                        file_path = client._get_file_path(file_id, all_files)
                        logger.info(f"   📁 {file_path}")
        else:
            logger.info(f"\n✅ Найдено {pdf_count} PDF файлов")
        
        # Используем встроенный метод
        logger.info(f"\n📋 Результат list_pdf_files():")
        pdf_files = client.list_pdf_files(config.input_folder)
        logger.info(f"Найдено файлов: {len(pdf_files)}")
        for f in pdf_files:
            logger.info(f"   - {f['name']} ({format_file_size(f['size'])})")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Отладка завершена")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(debug_mega_files())

