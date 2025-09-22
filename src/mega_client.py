#!/usr/bin/env python3
"""
Клиент для работы с облачным хранилищем Mega
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import fnmatch

try:
    from mega import Mega
except ImportError:
    print("❌ Библиотека mega.py не установлена. Установите: pip install mega.py")
    raise

from config import get_config
from utils import format_file_size, validate_file_path


class MegaClient:
    """Клиент для работы с Mega облачным хранилищем"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.mega = None
        self._authenticated = False
        
        # Настройки повторных попыток
        self.max_retries = 3
        self.retry_delay = 2  # секунды
        
        # Подключаемся к Mega
        self._connect()
    
    def _connect(self):
        """Подключение к Mega аккаунту"""
        email = self.config.mega_email
        password = self.config.mega_password
        
        if not email or not password:
            raise ValueError(
                "Не настроены данные для Mega. "
                "Установите переменные окружения MEGA_EMAIL и MEGA_PASSWORD"
            )
        
        try:
            self.logger.info("🔐 Подключение к Mega...")
            self.mega = Mega()
            
            # Аутентификация с повторными попытками
            for attempt in range(self.max_retries):
                try:
                    self.mega = self.mega.login(email, password)
                    self._authenticated = True
                    self.logger.info("✅ Успешно подключен к Mega")
                    break
                    
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    self.logger.warning(f"⚠️ Попытка {attempt + 1} неудачна: {e}")
                    time.sleep(self.retry_delay)
            
            # Проверяем квоту
            self._check_quota()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к Mega: {e}")
            raise
    
    def _check_quota(self):
        """Проверка квоты Mega аккаунта"""
        try:
            quota_info = self.mega.get_quota()
            total_space = quota_info['total']
            used_space = quota_info['used']
            free_space = total_space - used_space
            
            self.logger.info(f"💾 Mega квота:")
            self.logger.info(f"   📊 Всего: {format_file_size(total_space)}")
            self.logger.info(f"   📊 Использовано: {format_file_size(used_space)}")
            self.logger.info(f"   📊 Свободно: {format_file_size(free_space)}")
            
            # Предупреждение если места мало
            if free_space < 100 * 1024 * 1024:  # < 100 MB
                self.logger.warning(f"⚠️ Мало свободного места в Mega: {format_file_size(free_space)}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось получить информацию о квоте: {e}")
    
    def _ensure_connected(self):
        """Проверка соединения с Mega"""
        if not self._authenticated or not self.mega:
            raise ConnectionError("Не подключен к Mega")
    
    def _retry_on_failure(self, func, *args, **kwargs):
        """Выполнение функции с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                self.logger.warning(f"⚠️ Попытка {attempt + 1} неудачна: {e}")
                time.sleep(self.retry_delay * (attempt + 1))  # Увеличиваем задержку
    
    def list_pdf_files(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Получение списка PDF файлов в указанной папке
        
        Args:
            folder_path: путь к папке в Mega
            
        Returns:
            список словарей с информацией о файлах
        """
        self._ensure_connected()
        
        try:
            self.logger.info(f"🔍 Сканирование папки: {folder_path}")
            
            # Получаем все файлы
            files = self._retry_on_failure(self.mega.get_files)
            
            pdf_files = []
            skip_patterns = self.config.skip_patterns
            
            for file_id, file_info in files.items():
                if not isinstance(file_info, dict) or 'a' not in file_info:
                    continue
                
                file_name = file_info['a'].get('n', '')
                file_size = file_info.get('s', 0)
                
                # Проверяем путь к файлу
                file_path = self._get_file_path(file_id, files)
                if not file_path or not file_path.startswith(folder_path.rstrip('/')):
                    continue
                
                # Проверяем расширение
                if not file_name.lower().endswith(('.pdf', '.PDF')):
                    continue
                
                # Проверяем паттерны исключения
                if any(fnmatch.fnmatch(file_name.lower(), pattern.lower()) 
                       for pattern in skip_patterns):
                    self.logger.debug(f"⏭️ Пропускаю файл по паттерну: {file_name}")
                    continue
                
                # Проверяем размер файла
                min_size = self.config.min_file_size_kb * 1024
                max_size = self.config.max_file_size_mb * 1024 * 1024
                
                if file_size < min_size:
                    self.logger.debug(f"⏭️ Пропускаю маленький файл: {file_name} ({format_file_size(file_size)})")
                    continue
                
                if file_size > max_size:
                    self.logger.debug(f"⏭️ Пропускаю большой файл: {file_name} ({format_file_size(file_size)})")
                    continue
                
                pdf_files.append({
                    'id': file_id,
                    'name': file_name,
                    'size': file_size,
                    'path': file_path,
                    'parent_id': file_info.get('p'),
                    'created_time': file_info.get('ts', 0)
                })
            
            # Сортируем по времени создания (старые сначала)
            pdf_files.sort(key=lambda x: x['created_time'])
            
            self.logger.info(f"📋 Найдено PDF файлов: {len(pdf_files)}")
            for file_info in pdf_files[:5]:  # Показываем первые 5
                self.logger.info(f"   📄 {file_info['name']} ({format_file_size(file_info['size'])})")
            
            if len(pdf_files) > 5:
                self.logger.info(f"   📄 ... и еще {len(pdf_files) - 5} файлов")
            
            return pdf_files
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения списка файлов: {e}")
            raise
    
    def _get_file_path(self, file_id: str, all_files: Dict) -> str:
        """Получение полного пути к файлу"""
        try:
            path_parts = []
            current_id = file_id
            
            while current_id in all_files:
                file_info = all_files[current_id]
                if 'a' not in file_info:
                    break
                
                name = file_info['a'].get('n', '')
                if name:
                    path_parts.insert(0, name)
                
                parent_id = file_info.get('p')
                if not parent_id:
                    break
                    
                current_id = parent_id
            
            if path_parts:
                return '/' + '/'.join(path_parts)
            else:
                return ''
                
        except Exception:
            return ''
    
    def download_file(self, file_path: str, local_path: str) -> bool:
        """
        Скачивание файла из Mega
        
        Args:
            file_path: путь к файлу в Mega
            local_path: локальный путь для сохранения
            
        Returns:
            True если успешно, False иначе
        """
        self._ensure_connected()
        
        try:
            # Создаем директорию для файла
            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            self.logger.debug(f"📥 Скачивание {file_path} -> {local_path}")
            
            # Скачиваем с повторными попытками
            self._retry_on_failure(
                self.mega.download_url, 
                file_path, 
                dest_path=str(local_file.parent),
                dest_filename=local_file.name
            )
            
            if local_file.exists():
                file_size = local_file.stat().st_size
                self.logger.debug(f"✅ Скачано: {format_file_size(file_size)}")
                return True
            else:
                self.logger.error(f"❌ Файл не найден после скачивания: {local_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка скачивания {file_path}: {e}")
            return False
    
    def upload_file(self, local_path: str, mega_path: str) -> bool:
        """
        Загрузка файла в Mega
        
        Args:
            local_path: локальный путь к файлу
            mega_path: путь в Mega для сохранения
            
        Returns:
            True если успешно, False иначе
        """
        self._ensure_connected()
        
        local_file = Path(local_path)
        if not local_file.exists():
            self.logger.error(f"❌ Локальный файл не найден: {local_path}")
            return False
        
        try:
            file_size = local_file.stat().st_size
            self.logger.debug(f"📤 Загрузка {local_path} -> {mega_path} ({format_file_size(file_size)})")
            
            # Получаем папку назначения
            mega_dir = str(Path(mega_path).parent)
            mega_filename = Path(mega_path).name
            
            # Создаем папку если не существует
            self._ensure_folder_exists(mega_dir)
            
            # Загружаем с повторными попытками
            self._retry_on_failure(
                self.mega.upload,
                str(local_file),
                dest=mega_dir,
                dest_filename=mega_filename
            )
            
            self.logger.debug(f"✅ Загружено: {mega_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки {local_path}: {e}")
            return False
    
    def _ensure_folder_exists(self, folder_path: str):
        """Создание папки в Mega если она не существует"""
        if not folder_path or folder_path == '/':
            return
        
        try:
            # Проверяем существование папки
            files = self.mega.get_files()
            
            # Ищем папку
            for file_id, file_info in files.items():
                if (isinstance(file_info, dict) and 
                    'a' in file_info and 
                    file_info['a'].get('n') == Path(folder_path).name and
                    file_info.get('t') == 1):  # t=1 означает папку
                    return  # Папка существует
            
            # Создаем папку
            parent_dir = str(Path(folder_path).parent)
            folder_name = Path(folder_path).name
            
            if parent_dir != '/':
                self._ensure_folder_exists(parent_dir)
            
            self.mega.create_folder(folder_name, dest=parent_dir)
            self.logger.debug(f"📁 Создана папка: {folder_path}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось создать папку {folder_path}: {e}")
    
    def delete_file(self, file_path: str) -> bool:
        """
        Удаление файла из Mega
        
        Args:
            file_path: путь к файлу в Mega
            
        Returns:
            True если успешно, False иначе
        """
        self._ensure_connected()
        
        try:
            self.logger.debug(f"🗑️ Удаление файла: {file_path}")
            
            # Находим файл по пути
            files = self.mega.get_files()
            file_id = None
            
            for fid, file_info in files.items():
                if (isinstance(file_info, dict) and 
                    self._get_file_path(fid, files) == file_path):
                    file_id = fid
                    break
            
            if file_id:
                self._retry_on_failure(self.mega.delete, file_id)
                self.logger.debug(f"✅ Файл удален: {Path(file_path).name}")
                return True
            else:
                self.logger.warning(f"⚠️ Файл для удаления не найден: {file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка удаления {file_path}: {e}")
            return False
    
    def move_file(self, source_path: str, target_path: str) -> bool:
        """
        Перемещение файла в Mega
        
        Args:
            source_path: исходный путь
            target_path: целевой путь
            
        Returns:
            True если успешно, False иначе
        """
        self._ensure_connected()
        
        try:
            self.logger.debug(f"📋 Перемещение {source_path} -> {target_path}")
            
            # Сначала копируем файл
            if self.copy_file(source_path, target_path):
                # Затем удаляем исходный
                return self.delete_file(source_path)
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка перемещения {source_path}: {e}")
            return False
    
    def copy_file(self, source_path: str, target_path: str) -> bool:
        """
        Копирование файла в Mega
        
        Args:
            source_path: исходный путь
            target_path: целевой путь
            
        Returns:
            True если успешно, False иначе
        """
        # Для копирования скачиваем и загружаем обратно
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            try:
                if self.download_file(source_path, tmp_file.name):
                    return self.upload_file(tmp_file.name, target_path)
                return False
            finally:
                Path(tmp_file.name).unlink(missing_ok=True)
    
    def get_folder_info(self, folder_path: str) -> Dict[str, Any]:
        """
        Получение информации о папке
        
        Args:
            folder_path: путь к папке
            
        Returns:
            словарь с информацией о папке
        """
        self._ensure_connected()
        
        try:
            pdf_files = self.list_pdf_files(folder_path)
            
            total_size = sum(f['size'] for f in pdf_files)
            
            return {
                'path': folder_path,
                'total_files': len(pdf_files),
                'total_size': total_size,
                'files': pdf_files
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения информации о папке {folder_path}: {e}")
            return {'path': folder_path, 'total_files': 0, 'total_size': 0, 'files': []}


def test_mega_client():
    """Тестирование Mega клиента"""
    try:
        client = MegaClient()
        
        # Тестируем получение списка файлов
        input_folder = client.config.input_folder
        print(f"🧪 Тестирование папки: {input_folder}")
        
        folder_info = client.get_folder_info(input_folder)
        print(f"📊 Файлов в папке: {folder_info['total_files']}")
        print(f"📊 Общий размер: {format_file_size(folder_info['total_size'])}")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")


if __name__ == "__main__":
    test_mega_client()
