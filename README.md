# 🗜️ PDF Batch Compressor for Mega

Автоматический пакетный компрессор PDF файлов с интеграцией Mega облачного хранилища и GitHub Actions.

[![Compress PDFs](https://github.com/username/pdf-compressor/actions/workflows/compress-pdfs.yml/badge.svg)](https://github.com/username/pdf-compressor/actions/workflows/compress-pdfs.yml)
[![Manual Compression](https://github.com/username/pdf-compressor/actions/workflows/manual-trigger.yml/badge.svg)](https://github.com/username/pdf-compressor/actions/workflows/manual-trigger.yml)

## ✨ Возможности

- 🚀 **Автоматическое сжатие** PDF файлов по расписанию
- 🗂️ **Интеграция с Mega** - прямая работа с облачным хранилищем
- 🤖 **GitHub Actions** - полностью бесплатная автоматизация
- 🎯 **Умное сжатие** - выбор оптимального алгоритма для каждого файла
- 📊 **Детальная статистика** - отчеты об экономии места и времени
- 📱 **Telegram уведомления** - получайте результаты на телефон
- 🛡️ **Безопасность** - резервное копирование и проверка целостности
- ⚙️ **Гибкая настройка** - варианты параметров сжатия

## 📋 Алгоритмы сжатия

Проект использует несколько методов сжатия для оптимальных результатов:

| Инструмент | Лучше для | Типичная экономия |
|------------|-----------|-------------------|
| **Ghostscript** | Файлы с изображениями, сканы | 60-90% |
| **QPDF** | Универсальное сжатие | 70-85% |
| **Pikepdf** | Файлы с формами, безопасное сжатие | 70-85% |
| **PyPDF** | Простые PDF файлы | 80-95% |

### Уровни сжатия

- **🟢 Low**: Минимальные потери качества (принтер-качество)
- **🟡 Medium**: Баланс размера и качества (электронные книги)
- **🔴 High**: Максимальное сжатие (веб-использование)

## 🚀 Быстрый старт

### 1. Настройка репозитория

1. **Fork этого репозитория** или создайте новый
2. **Добавьте GitHub Secrets** в настройках репозитория:

```bash
MEGA_EMAIL=your-mega-email@example.com
MEGA_PASSWORD=your-mega-password
TELEGRAM_BOT_TOKEN=your-telegram-bot-token  # (опционально)
TELEGRAM_CHAT_ID=your-telegram-chat-id      # (опционально)
```

### 2. Настройка папок в Mega

Создайте следующие папки в вашем Mega аккаунте:

```
/PDF/
├── Input/          # Исходные файлы для сжатия
├── Compressed/     # Сжатые файлы
├── Backup/         # Резервные копии (опционально)
└── Processed/      # Архив обработанных файлов
```

### 3. Настройка конфигурации

Отредактируйте `config/settings.yaml` под свои нужды:

```yaml
folders:
  input: "/PDF/Input"
  output: "/PDF/Compressed"
  backup: "/PDF/Backup"

compression:
  default_level: "medium"
  
limits:
  max_files_per_run: 50
  max_file_size_mb: 200
```

### 4. Запуск

После настройки система работает автоматически:

- **Автоматически**: каждый день в 2:00 и 14:00 UTC
- **Вручную**: через вкладку "Actions" → "Manual PDF Compression" → "Run workflow"

## 📖 Использование

### Автоматическое сжатие

Просто поместите PDF файлы в папку `/PDF/Input` в вашем Mega аккаунте. Система автоматически:

1. Найдет новые PDF файлы
2. Скачает их для обработки
3. Применит оптимальный алгоритм сжатия
4. Загрузит сжатые файлы в папку `/PDF/Compressed`
5. Удалит оригинальные файлы (с резервным копированием)
6. Отправит отчет в Telegram

### Ручной запуск

Для ручного запуска перейдите в Actions → Manual PDF Compression и укажите параметры:

- **Source folder**: исходная папка (например, `/PDF/Input`)
- **Target folder**: папка для сжатых файлов 
- **Compression level**: уровень сжатия (low/medium/high)
- **Max files**: максимальное количество файлов за раз
- **Dry run**: тестовый режим без изменений

### Мониторинг

- **GitHub Actions**: просматривайте логи выполнения
- **Artifacts**: скачивайте детальные отчеты
- **Telegram**: получайте краткие уведомления
- **Issues**: автоматическое создание при ошибках

## 📊 Статистика

Система ведет подробную статистику:

```json
{
  "processed_files": 25,
  "failed_files": 2,
  "total_size_before": 150000000,
  "total_size_after": 45000000,
  "total_bytes_saved": 105000000,
  "total_percent_saved": 70.0,
  "duration": 245.6,
  "compression_level": "medium"
}
```

## ⚙️ Конфигурация

### Основные настройки

**config/settings.yaml**:

```yaml
# Папки в Mega
folders:
  input: "/PDF/Input"
  output: "/PDF/Compressed"
  backup: "/PDF/Backup"

# Уровни сжатия
compression:
  default_level: "medium"
  levels:
    low:
      ghostscript_preset: "printer"
      image_quality: 85
      image_resolution: 150
    medium:
      ghostscript_preset: "ebook"
      image_quality: 75
      image_resolution: 120
    high:
      ghostscript_preset: "screen"
      image_quality: 60
      image_resolution: 96

# Лимиты
limits:
  max_files_per_run: 50
  max_file_size_mb: 200
  min_file_size_kb: 100
  timeout_minutes: 60

# Фильтры файлов
filters:
  skip_patterns:
    - "*compressed*"
    - "*_comp.pdf"
    - "*optimized*"
  min_compression_percent: 5

# Безопасность
safety:
  create_backup: true
  verify_compression: true
  rollback_on_error: true

# Уведомления
notifications:
  telegram:
    enabled: true
    on_success: true
    on_error: true
```

### GitHub Secrets

| Секрет | Обязательный | Описание |
|--------|--------------|----------|
| `MEGA_EMAIL` | ✅ | Email вашего Mega аккаунта |
| `MEGA_PASSWORD` | ✅ | Пароль Mega аккаунта |
| `TELEGRAM_BOT_TOKEN` | ❌ | Токен Telegram бота для уведомлений |
| `TELEGRAM_CHAT_ID` | ❌ | ID чата для уведомлений |

### Настройка Telegram уведомлений

1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите токен бота
3. Узнайте свой Chat ID через [@userinfobot](https://t.me/userinfobot)
4. Добавьте токены в GitHub Secrets

## 🛠️ Локальная разработка

### Установка

```bash
git clone https://github.com/username/pdf-compressor.git
cd pdf-compressor

# Установка зависимостей
pip install -r requirements.txt

# Системные зависимости (Ubuntu/Debian)
sudo apt-get install ghostscript qpdf poppler-utils

# Создание .env файла
cp .env.example .env
# Отредактируйте .env с вашими данными
```

### Запуск

```bash
# Тестовый запуск
python src/main.py --dry-run

# Обычный запуск
python src/main.py \
  --source "/PDF/Input" \
  --target "/PDF/Compressed" \
  --level medium \
  --max-files 10

# С настройками логирования
python src/main.py \
  --log-file logs/compression.log \
  --log-level DEBUG
```

### Тестирование

```bash
# Тестирование компрессора
python src/compressor.py

# Тестирование Mega клиента
python src/mega_client.py

# Тестирование конфигурации
python src/config.py
```

## 📁 Структура проекта

```
pdf-compressor/
├── .github/workflows/       # GitHub Actions
│   ├── compress-pdfs.yml   # Основной workflow
│   └── manual-trigger.yml  # Ручной запуск
├── src/                     # Исходный код
│   ├── main.py             # Основной скрипт
│   ├── compressor.py       # Логика сжатия PDF
│   ├── mega_client.py      # Клиент Mega
│   ├── config.py           # Управление конфигурацией
│   └── utils.py            # Утилиты
├── scripts/                 # Вспомогательные скрипты
│   ├── generate_report.py  # Генерация отчетов
│   └── send_notification.py # Telegram уведомления
├── config/                  # Конфигурация
│   └── settings.yaml       # Основные настройки
├── requirements.txt         # Python зависимости
└── README.md               # Документация
```

## 🔧 Расширенные возможности

### Фильтрация файлов

Настройте какие файлы обрабатывать:

```yaml
filters:
  # Пропускать файлы по паттернам
  skip_patterns:
    - "*compressed*"
    - "*_small.pdf"
    - "temp_*"
  
  # Размеры файлов
  min_file_size_kb: 100
  max_file_size_mb: 200
  
  # Минимальный процент сжатия для сохранения
  min_compression_percent: 5
```

### Множественные папки

Обрабатывайте несколько папок:

```bash
# Через параметры workflow
python src/main.py --source "/PDF/Documents" --target "/PDF/Documents/Compressed"
python src/main.py --source "/PDF/Scans" --target "/PDF/Scans/Compressed"
```

### Настройка расписания

Измените расписание в `.github/workflows/compress-pdfs.yml`:

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Каждые 6 часов
    - cron: '0 2 * * 1'    # Каждый понедельник в 2:00
```

## 🐛 Диагностика проблем

### Типичные ошибки

**1. Ошибка подключения к Mega**
```
❌ Ошибка подключения к Mega: Login failed
```
**Решение**: Проверьте правильность `MEGA_EMAIL` и `MEGA_PASSWORD`

**2. Превышение лимитов GitHub Actions**
```
❌ Job was cancelled due to timeout
```
**Решение**: Уменьшите `max_files_per_run` или увеличьте `timeout-minutes`

**3. Ошибка сжатия**
```
❌ Все методы сжатия не удались
```
**Решение**: Файл может быть поврежден или зашифрован

### Отладка

Включите подробное логирование:

```yaml
# В workflow
--log-level DEBUG
```

Проверьте артефакты workflow для детальных логов.

## 🤝 Вклад в проект

Приветствуются улучшения! Пожалуйста:

1. Fork репозитория
2. Создайте ветку для изменений
3. Добавьте тесты если нужно
4. Создайте Pull Request

## 📄 Лицензия

MIT License. См. [LICENSE](LICENSE) для подробностей.

## 🙏 Благодарности

- [mega.py](https://github.com/richardpenman/mega.py) - Python клиент для Mega
- [pikepdf](https://github.com/pikepdf/pikepdf) - Работа с PDF на Python
- [Ghostscript](https://www.ghostscript.com/) - Профессиональное сжатие PDF
- [QPDF](https://github.com/qpdf/qpdf) - Инструменты для PDF

---

<div align="center">
  
**🗜️ Экономьте место в облаке автоматически!**

[🐛 Сообщить об ошибке](https://github.com/username/pdf-compressor/issues) • [💡 Предложить улучшение](https://github.com/username/pdf-compressor/issues) • [📚 Wiki](https://github.com/username/pdf-compressor/wiki)

</div>
