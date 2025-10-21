#!/usr/bin/env python3
"""
Конфигурационный модуль PDF компрессора
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class Config:
    """Класс для управления конфигурацией приложения"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = Path(config_path)
        self._config_data: Dict[str, Any] = {}
        self._load_config()
        self._load_secrets()
    
    def _load_config(self):
        """Загрузка основной конфигурации из YAML файла"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Ошибка загрузки конфигурации: {e}")
    
    def _load_secrets(self):
        """Загрузка секретных данных из переменных окружения и GitHub Secrets"""
        secrets = {
            'mega': {
                'email': os.getenv('MEGA_EMAIL'),
                'password': os.getenv('MEGA_PASSWORD')
            },
            'telegram': {
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'chat_id': os.getenv('TELEGRAM_CHAT_ID')
            },
            'github': {
                'token': os.getenv('GITHUB_TOKEN'),
                'repo': os.getenv('GITHUB_REPOSITORY')
            }
        }
        
        # Добавляем секреты в конфигурацию
        self._config_data['secrets'] = secrets
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Получение значения по пути (например, 'compression.levels.medium.image_quality')
        """
        keys = path.split('.')
        value = self._config_data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, path: str, value: Any):
        """
        Установка значения по пути
        """
        keys = path.split('.')
        current = self._config_data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    # Свойства для быстрого доступа к часто используемым настройкам
    
    @property
    def folders(self) -> Dict[str, str]:
        """Настройки папок Mega"""
        return self.get('folders', {})
    
    @property
    def input_folder(self) -> str:
        """Папка входных файлов"""
        return self.get('folders.input', '/pdf/Input')
    
    @property
    def output_folder(self) -> str:
        """Папка выходных файлов"""
        return self.get('folders.output', '/pdf/Compressed')
    
    @property
    def backup_folder(self) -> str:
        """Папка резервных копий"""
        return self.get('folders.backup', '/pdf/Backup')
    
    @property
    def compression_levels(self) -> Dict[str, Dict[str, Any]]:
        """Уровни сжатия"""
        return self.get('compression.levels', {})
    
    @property
    def default_compression_level(self) -> str:
        """Уровень сжатия по умолчанию"""
        return self.get('compression.default_level', 'medium')
    
    def get_compression_settings(self, level: str) -> Dict[str, Any]:
        """Получение настроек сжатия для указанного уровня"""
        return self.get(f'compression.levels.{level}', {})
    
    @property
    def limits(self) -> Dict[str, Any]:
        """Лимиты обработки"""
        return self.get('limits', {})
    
    @property
    def max_files_per_run(self) -> int:
        """Максимальное количество файлов за один запуск"""
        return self.get('limits.max_files_per_run', 50)
    
    @property
    def max_file_size_mb(self) -> int:
        """Максимальный размер файла в МБ"""
        return self.get('limits.max_file_size_mb', 200)
    
    @property
    def min_file_size_kb(self) -> int:
        """Минимальный размер файла в КБ"""
        return self.get('limits.min_file_size_kb', 100)
    
    @property
    def filters(self) -> Dict[str, Any]:
        """Фильтры файлов"""
        return self.get('filters', {})
    
    @property
    def skip_patterns(self) -> list:
        """Паттерны файлов для пропуска"""
        return self.get('filters.skip_patterns', [])
    
    @property
    def min_compression_percent(self) -> float:
        """Минимальный процент сжатия для сохранения результата"""
        return self.get('filters.min_compression_percent', 5.0)
    
    # Секретные данные
    
    @property
    def mega_email(self) -> Optional[str]:
        """Email для Mega"""
        return self.get('secrets.mega.email')
    
    @property
    def mega_password(self) -> Optional[str]:
        """Пароль для Mega"""
        return self.get('secrets.mega.password')
    
    @property
    def telegram_bot_token(self) -> Optional[str]:
        """Токен Telegram бота"""
        return self.get('secrets.telegram.bot_token')
    
    @property
    def telegram_chat_id(self) -> Optional[str]:
        """ID чата Telegram"""
        return self.get('secrets.telegram.chat_id')
    
    @property
    def github_token(self) -> Optional[str]:
        """GitHub токен"""
        return self.get('secrets.github.token')
    
    @property
    def github_repo(self) -> Optional[str]:
        """GitHub репозиторий"""
        return self.get('secrets.github.repo')
    
    # Настройки уведомлений
    
    @property
    def telegram_enabled(self) -> bool:
        """Включены ли Telegram уведомления"""
        return (self.get('notifications.telegram.enabled', False) 
                and self.telegram_bot_token 
                and self.telegram_chat_id)
    
    @property
    def github_issues_enabled(self) -> bool:
        """Включено ли создание GitHub Issues при ошибках"""
        return (self.get('notifications.github.create_issues_on_error', False) 
                and self.github_token 
                and self.github_repo)
    
    # Настройки безопасности
    
    @property
    def create_backup(self) -> bool:
        """Создавать ли резервные копии"""
        return self.get('safety.create_backup', True)
    
    @property
    def verify_compression(self) -> bool:
        """Проверять ли целостность сжатых файлов"""
        return self.get('safety.verify_compression', True)
    
    @property
    def rollback_on_error(self) -> bool:
        """Восстанавливать ли оригинальный файл при ошибке"""
        return self.get('safety.rollback_on_error', True)
    
    # Настройки логирования
    
    @property
    def log_level(self) -> str:
        """Уровень логирования"""
        return self.get('logging.level', 'INFO')
    
    def validate(self) -> Dict[str, list]:
        """
        Валидация конфигурации
        Возвращает словарь с ошибками и предупреждениями
        """
        errors = []
        warnings = []
        
        # Проверка обязательных секций
        required_sections = ['folders', 'compression', 'limits']
        for section in required_sections:
            if not self.get(section):
                errors.append(f"Отсутствует обязательная секция: {section}")
        
        # Проверка настроек Mega
        if not self.mega_email or not self.mega_password:
            errors.append("Не настроены данные для Mega (MEGA_EMAIL, MEGA_PASSWORD)")
        
        # Проверка уровней сжатия
        if not self.compression_levels:
            errors.append("Не настроены уровни сжатия")
        
        default_level = self.default_compression_level
        if default_level not in self.compression_levels:
            warnings.append(f"Уровень сжатия по умолчанию '{default_level}' не найден")
        
        # Проверка лимитов
        if self.max_file_size_mb <= 0:
            warnings.append("Максимальный размер файла должен быть больше 0")
        
        if self.max_files_per_run <= 0:
            warnings.append("Максимальное количество файлов должно быть больше 0")
        
        # Проверка Telegram настроек
        # Пропускаем проверку, так как токены могут быть в GitHub Secrets
        # telegram_enabled = self.get('notifications.telegram.enabled', False)
        # if telegram_enabled and not self.telegram_enabled:
        #     warnings.append("Telegram уведомления включены, но не настроены токены")
        
        return {
            'errors': errors,
            'warnings': warnings
        }
    
    def print_summary(self):
        """Вывод краткой информации о конфигурации"""
        print("📋 Конфигурация PDF Компрессора:")
        print(f"   📁 Входная папка: {self.input_folder}")
        print(f"   📁 Выходная папка: {self.output_folder}")
        print(f"   🗜️  Уровень сжатия: {self.default_compression_level}")
        print(f"   📊 Макс. файлов за раз: {self.max_files_per_run}")
        print(f"   💾 Макс. размер файла: {self.max_file_size_mb} MB")
        print(f"   🔐 Mega аккаунт: {'✅' if self.mega_email else '❌'}")
        print(f"   📱 Telegram: {'✅' if self.telegram_enabled else '❌'}")
        print(f"   🔧 GitHub Issues: {'✅' if self.github_issues_enabled else '❌'}")
        
        validation = self.validate()
        if validation['errors']:
            print(f"   ❌ Ошибки: {len(validation['errors'])}")
            for error in validation['errors']:
                print(f"      • {error}")
        
        if validation['warnings']:
            print(f"   ⚠️  Предупреждения: {len(validation['warnings'])}")
            for warning in validation['warnings']:
                print(f"      • {warning}")
    
    def save_config(self, output_path: Optional[str] = None):
        """
        Сохранение текущей конфигурации в файл
        (без секретных данных)
        """
        if output_path is None:
            output_path = self.config_path
        
        # Создаем копию конфигурации без секретов
        safe_config = self._config_data.copy()
        safe_config.pop('secrets', None)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(safe_config, f, 
                     allow_unicode=True, 
                     default_flow_style=False,
                     sort_keys=False)


# Глобальный экземпляр конфигурации
_config_instance: Optional[Config] = None


def get_config(config_path: str = "config/settings.yaml") -> Config:
    """
    Получение глобального экземпляра конфигурации
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reload_config(config_path: str = "config/settings.yaml") -> Config:
    """
    Перезагрузка конфигурации
    """
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance


if __name__ == "__main__":
    # Тестирование конфигурации
    try:
        config = get_config()
        config.print_summary()
        
        # Тестирование доступа к настройкам
        print(f"\nТест настроек сжатия 'medium':")
        medium_settings = config.get_compression_settings('medium')
        for key, value in medium_settings.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"Ошибка при тестировании конфигурации: {e}")
