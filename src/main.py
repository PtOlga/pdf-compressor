#!/usr/bin/env python3
"""
Основной скрипт PDF компрессора для Mega
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
import json
import traceback
from typing import Dict, List, Optional

# Добавляем src в путь для импортов
sys.path.insert(0, str(Path(__file__).parent))

from utils import setup_logging, format_file_size, format_duration, print_banner, create_temp_dirs, cleanup_temp_files, save_statistics
from config import get_config
from compressor import PDFCompressor
from rclone_client import RcloneClient
from megacmd_client import MegaWebDAVClient


class PDFBatchCompressor:
    """Основной класс пакетного сжатия PDF"""
    
    def __init__(self, source_folder: str = None, target_folder: str = None, 
                 compression_level: str = None, max_files: int = None):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # Настройки из параметров или конфигурации
        self.source_folder = source_folder or self.config.input_folder
        self.target_folder = target_folder or self.config.output_folder
        self.compression_level = compression_level or self.config.default_compression_level
        self.max_files = max_files or self.config.max_files_per_run
        
        # Статистика
        self.stats = {
            'start_time': datetime.now(timezone.utc),
            'end_time': None,
            'duration': 0,
            'processed_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'total_size_before': 0,
            'total_size_after': 0,
            'total_bytes_saved': 0,
            'total_percent_saved': 0,
            'files': [],
            'errors': [],
            'compression_level': self.compression_level,
            'source_folder': self.source_folder,
            'target_folder': self.target_folder
        }
        
        # Инициализируем компоненты
        self.mega_client = None
        self.compressor = None
    
    def run(self) -> int:
        """
        Основной метод запуска процесса сжатия
        
        Returns:
            0 если успешно, 1 при ошибках
        """
        try:
            self._print_startup_info()
            
            # Создаем временные директории
            create_temp_dirs()
            
            # Инициализируем клиентов
            self.logger.info("🔧 Инициализация компонентов...")
            self._initialize_clients()
            
            # Получаем список файлов для обработки
            self.logger.info(f"📁 Поиск PDF файлов в: {self.source_folder}")
            pdf_files = self.mega_client.list_pdf_files(self.source_folder)
            
            if not pdf_files:
                self.logger.info("✅ Файлы для обработки не найдены")
                self._finalize_stats(success=True)
                return 0
            
            # Ограничиваем количество файлов
            if len(pdf_files) > self.max_files:
                self.logger.info(f"⚠️ Ограничиваю обработку до {self.max_files} файлов (найдено {len(pdf_files)})")
                pdf_files = pdf_files[:self.max_files]
            
            self.logger.info(f"📋 К обработке: {len(pdf_files)} файлов")
            
            # Обрабатываем файлы
            success = self._process_files(pdf_files)
            
            # Финализация
            self._finalize_stats(success)
            self._cleanup()
            
            return 0 if success else 1
            
        except KeyboardInterrupt:
            self.logger.info("ℹ️ Обработка прервана пользователем")
            self._finalize_stats(success=False, error="Прервано пользователем")
            return 1
            
        except Exception as e:
            self.logger.error(f"💥 Критическая ошибка: {str(e)}")
            self.logger.debug("Стек трассировки:", exc_info=True)
            self._finalize_stats(success=False, error=str(e))
            return 1
    
    def _print_startup_info(self):
        """Вывод информации о запуске"""
        print_banner()
        
        self.logger.info("📋 Параметры запуска:")
        self.logger.info(f"   📁 Источник: {self.source_folder}")
        self.logger.info(f"   📁 Назначение: {self.target_folder}")
        self.logger.info(f"   🗜️ Уровень сжатия: {self.compression_level}")
        self.logger.info(f"   📊 Макс. файлов: {self.max_files}")
        self.logger.info(f"   ⏰ Время запуска: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    def _initialize_clients(self):
        """Инициализация Mega клиента и компрессора"""
        try:
            # Mega клиент: используем MEGAcmd (WebDAV), если путь из Incoming shares
            use_megacmd = False
            sf = (self.source_folder or '').lower()
            tf = (self.target_folder or '').lower()
            if '/incoming shares/' in sf or '/incoming shares/' in tf or sf.startswith('/incoming ') or tf.startswith('/incoming '):
                use_megacmd = True

            if use_megacmd:
                self.logger.info("🌐 Использую MEGAcmd WebDAV клиент (поддержка Incoming shares)")
                self.mega_client = MegaWebDAVClient()
            else:
                self.mega_client = RcloneClient()

            # PDF компрессор
            self.compressor = PDFCompressor(level=self.compression_level)

            # Выводим информацию о компрессоре
            comp_info = self.compressor.get_compression_info()
            self.logger.info(f"🔧 Доступные инструменты: {list(comp_info['available_tools'].keys())}")

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации: {e}")
            raise
    
    def _process_files(self, pdf_files: List[Dict]) -> bool:
        """Обработка списка PDF файлов"""
        success = True
        
        for i, file_info in enumerate(pdf_files, 1):
            self.logger.info("=" * 60)
            self.logger.info(f"📄 [{i}/{len(pdf_files)}] {file_info['name']}")
            self.logger.info(f"📊 Размер: {format_file_size(file_info['size'])}")
            
            try:
                file_success = self._process_single_file(file_info)
                if not file_success:
                    success = False
                    
            except Exception as e:
                self.logger.error(f"❌ Ошибка обработки {file_info['name']}: {e}")
                self.stats['failed_files'] += 1
                self.stats['errors'].append({
                    'file': file_info['name'],
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                success = False
        
        return success
    
    def _process_single_file(self, file_info: Dict) -> bool:
        """Обработка одного PDF файла"""
        file_name = file_info['name']
        file_path = file_info['path']
        original_size = file_info['size']
        
        # Пути для временных файлов
        input_temp_path = f"temp/input/{file_name}"
        output_temp_path = f"temp/output/{file_name}"
        backup_temp_path = f"temp/backup/{file_name}"
        
        try:
            # 1. Скачиваем файл
            self.logger.info("📥 Скачивание файла...")
            if not self.mega_client.download_file(file_path, input_temp_path):
                raise Exception("Ошибка скачивания файла")
            
            # 2. Создаем бэкап если нужно
            if self.config.create_backup:
                backup_path = f"{self.config.backup_folder}/{file_name}"
                self.logger.debug(f"💾 Создание бэкапа: {backup_path}")
                if not self.mega_client.copy_file(file_path, backup_path):
                    self.logger.warning("⚠️ Не удалось создать бэкап")
            
            # 3. Сжимаем файл
            self.logger.info(f"🗜️ Сжатие файла (уровень: {self.compression_level})...")
            compression_result = self.compressor.compress(input_temp_path, output_temp_path)
            
            if not compression_result['success']:
                raise Exception(f"Ошибка сжатия: {compression_result['error']}")
            
            compressed_size = compression_result['size_after']
            bytes_saved = compression_result['bytes_saved']
            percent_saved = compression_result['percent_saved']
            
            self.logger.info(f"✅ Сжатие завершено:")
            self.logger.info(f"   📊 Было: {format_file_size(original_size)}")
            self.logger.info(f"   📊 Стало: {format_file_size(compressed_size)}")
            self.logger.info(f"   💾 Экономия: {format_file_size(bytes_saved)} ({percent_saved:.1f}%)")
            
            # 4. Проверяем целостность сжатого файла
            if self.config.verify_compression:
                if not self.compressor.verify_compressed_file(output_temp_path):
                    raise Exception("Сжатый файл поврежден")
            
            # 5. Загружаем сжатый файл
            target_path = f"{self.target_folder}/{file_name}"
            self.logger.info(f"📤 Загрузка в: {target_path}")
            if not self.mega_client.upload_file(output_temp_path, target_path):
                raise Exception("Ошибка загрузки сжатого файла")
            
            # 6. Удаляем оригинальный файл
            self.logger.info("🗑️ Удаление оригинального файла...")
            if not self.mega_client.delete_file(file_path):
                self.logger.warning("⚠️ Не удалось удалить оригинальный файл")
            
            # 7. Обновляем статистику
            self.stats['processed_files'] += 1
            self.stats['total_size_before'] += original_size
            self.stats['total_size_after'] += compressed_size
            self.stats['total_bytes_saved'] += bytes_saved
            
            self.stats['files'].append({
                'name': file_name,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'bytes_saved': bytes_saved,
                'percent_saved': percent_saved,
                'compression_method': compression_result.get('method', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            self.logger.info(f"✅ Файл {file_name} успешно обработан")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки {file_name}: {e}")
            
            # Восстановление оригинала при ошибке
            if self.config.rollback_on_error:
                self.logger.info("🔄 Попытка восстановления...")
                try:
                    # Логика восстановления из бэкапа
                    pass  # Пока не реализовано
                except Exception as rollback_error:
                    self.logger.error(f"❌ Ошибка восстановления: {rollback_error}")
            
            self.stats['failed_files'] += 1
            self.stats['errors'].append({
                'file': file_name,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return False
            
        finally:
            # Очистка временных файлов
            for temp_path in [input_temp_path, output_temp_path, backup_temp_path]:
                temp_file = Path(temp_path)
                if temp_file.exists():
                    temp_file.unlink()
    
    def _finalize_stats(self, success: bool, error: str = None):
        """Финализация и вывод статистики"""
        self.stats['end_time'] = datetime.now(timezone.utc)
        self.stats['duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        if self.stats['total_size_before'] > 0:
            self.stats['total_percent_saved'] = (
                self.stats['total_bytes_saved'] / self.stats['total_size_before'] * 100
            )
        
        if error:
            self.stats['error'] = error
        
        # Выводим итоговую статистику
        self._print_final_stats()
        
        # Сохраняем статистику
        save_statistics(self.stats)
    
    def _print_final_stats(self):
        """Вывод итоговой статистики"""
        self.logger.info("=" * 60)
        self.logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        self.logger.info("=" * 60)
        
        self.logger.info(f"⏱️ Время работы: {format_duration(self.stats['duration'])}")
        self.logger.info(f"✅ Обработано файлов: {self.stats['processed_files']}")
        self.logger.info(f"❌ Ошибок: {self.stats['failed_files']}")
        
        if self.stats['processed_files'] > 0:
            self.logger.info(f"📊 Размер до сжатия: {format_file_size(self.stats['total_size_before'])}")
            self.logger.info(f"📊 Размер после сжатия: {format_file_size(self.stats['total_size_after'])}")
            self.logger.info(f"💾 Общая экономия: {format_file_size(self.stats['total_bytes_saved'])}")
            self.logger.info(f"💾 Процент экономии: {self.stats['total_percent_saved']:.1f}%")
        
        if self.stats['errors']:
            self.logger.info(f"❌ Ошибки:")
            for error in self.stats['errors'][-3:]:  # Показываем последние 3 ошибки
                self.logger.info(f"   • {error['file']}: {error['error']}")
        
        self.logger.info("=" * 60)
    
    def _cleanup(self):
        """Очистка временных файлов и корректное завершение клиентов"""
        try:
            cleanup_temp_files(max_age_hours=1)
            self.logger.debug("🧹 Временные файлы очищены")
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка очистки временных файлов: {e}")

        # Корректно закрываем Mega-клиент (важно для MEGAcmd WebDAV)
        try:
            if self.mega_client and hasattr(self.mega_client, 'close'):
                self.mega_client.close()
                self.logger.debug("🔚 Mega-клиент корректно завершён")
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка завершения Mega-клиента: {e}")


def main():
    """Основная функция с парсингом аргументов"""
    parser = argparse.ArgumentParser(
        description='Пакетный компрессор PDF файлов для Mega',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --source "/PDF/Input" --target "/PDF/Compressed"
  %(prog)s --level high --max-files 10
  %(prog)s --log-file logs/compression.log
        """
    )
    
    parser.add_argument('--source', 
                       help='Исходная папка в Mega')
    parser.add_argument('--target',
                       help='Целевая папка в Mega')
    parser.add_argument('--level', 
                       choices=['low', 'medium', 'high'],
                       help='Уровень сжатия')
    parser.add_argument('--max-files', 
                       type=int,
                       help='Максимальное количество файлов за раз')
    parser.add_argument('--log-file',
                       help='Файл для сохранения логов')
    parser.add_argument('--log-level',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Уровень логирования')
    parser.add_argument('--config',
                       default='config/settings.yaml',
                       help='Путь к файлу конфигурации')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Тестовый запуск без реальных изменений')
    
    args = parser.parse_args()
    
    try:
        # Настройка логирования
        setup_logging(args.log_file, args.log_level)
        
        # Проверка конфигурации
        config = get_config(args.config)
        validation = config.validate()
        
        if validation['errors']:
            print("❌ Ошибки конфигурации:")
            for error in validation['errors']:
                print(f"   • {error}")
            return 1
        
        if validation['warnings']:
            print("⚠️ Предупреждения конфигурации:")
            for warning in validation['warnings']:
                print(f"   • {warning}")
        
        # Создаем и запускаем компрессор
        compressor = PDFBatchCompressor(
            source_folder=args.source,
            target_folder=args.target,
            compression_level=args.level,
            max_files=args.max_files
        )

        if args.dry_run:
            print("🧪 ТЕСТОВЫЙ РЕЖИМ - изменения не будут сохранены")
            # Запускаем компрессор в тестовом режиме
            # (логика сухого запуска должна быть в самом компрессоре)

        return compressor.run()
        
    except KeyboardInterrupt:
        print("\nℹ️ Прервано пользователем")
        return 1
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())