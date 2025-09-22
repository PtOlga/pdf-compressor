#!/bin/bash
# Скрипт быстрой установки PDF Batch Compressor

set -e

echo "🗜️ PDF Batch Compressor - Установка"
echo "====================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION найден"

# Проверка pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 не найден. Установите pip"
    exit 1
fi

echo "✅ pip найден"

# Установка системных зависимостей
echo ""
echo "📦 Проверка системных зависимостей..."

if command -v apt-get &> /dev/null; then
    echo "🔧 Обнаружен APT package manager"
    echo "Для установки системных зависимостей выполните:"
    echo "sudo apt-get update"
    echo "sudo apt-get install -y ghostscript qpdf poppler-utils"
elif command -v yum &> /dev/null; then
    echo "🔧 Обнаружен YUM package manager"
    echo "Для установки системных зависимостей выполните:"
    echo "sudo yum install -y ghostscript qpdf poppler-utils"
elif command -v brew &> /dev/null; then
    echo "🔧 Обнаружен Homebrew"
    echo "Для установки системных зависимостей выполните:"
    echo "brew install ghostscript qpdf poppler"
else
    echo "⚠️ Не удалось определить package manager"
    echo "Установите вручную: ghostscript, qpdf, poppler-utils"
fi

# Проверка наличия инструментов
echo ""
echo "🔍 Проверка инструментов сжатия..."

if command -v gs &> /dev/null; then
    GS_VERSION=$(gs --version 2>/dev/null || echo "unknown")
    echo "✅ Ghostscript $GS_VERSION найден"
else
    echo "⚠️ Ghostscript не найден (рекомендуется для лучшего сжатия)"
fi

if command -v qpdf &> /dev/null; then
    QPDF_VERSION=$(qpdf --version 2>/dev/null | head -1 || echo "unknown")
    echo "✅ QPDF $QPDF_VERSION найден"
else
    echo "⚠️ QPDF не найден (рекомендуется)"
fi

# Установка Python зависимостей
echo ""
echo "🐍 Установка Python зависимостей..."

if [[ -f "requirements.txt" ]]; then
    pip3 install --user -r requirements.txt
    echo "✅ Python зависимости установлены"
else
    echo "❌ Файл requirements.txt не найден"
    echo "Убедитесь, что вы находитесь в директории проекта"
    exit 1
fi

# Создание директорий
echo ""
echo "📁 Создание рабочих директорий..."
mkdir -p temp/{input,output,logs,backup}
mkdir -p logs
echo "✅ Директории созданы"

# Копирование примера конфигурации
echo ""
echo "⚙️ Настройка конфигурации..."
if [[ -f ".env.example" ]] && [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo "✅ Создан файл .env из примера"
    echo "📝 Отредактируйте .env файл с вашими данными Mega"
else
    echo "ℹ️ Файл .env уже существует или .env.example не найден"
fi

# Тестирование установки
echo ""
echo "🧪 Тестирование установки..."

if python3 src/config.py &> /dev/null; then
    echo "✅ Конфигурация загружается корректно"
else
    echo "⚠️ Проблемы с конфигурацией (возможно, не настроены секреты)"
fi

if python3 -c "import sys; sys.path.insert(0, 'src'); from compressor import PDFCompressor; PDFCompressor()" &> /dev/null; then
    echo "✅ PDF компрессор инициализируется"
else
    echo "❌ Проблемы с инициализацией компрессора"
fi

# Финальные инструкции
echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте .env файл с вашими данными Mega:"
echo "   nano .env"
echo ""
echo "2. Настройте config/settings.yaml под ваши нужды"
echo ""
echo "3. Тестовый запуск:"
echo "   python3 src/main.py --dry-run --source '/PDF/Input' --target '/PDF/Output'"
echo ""
echo "4. Для использования с GitHub Actions:"
echo "   - Добавьте секреты в настройки репозитория"
echo "   - Закоммитьте и запуште код"
echo "   - Используйте Actions для автоматизации"
echo ""
echo "📚 Полная документация в README.md"
echo ""
echo "🔗 GitHub репозиторий: https://github.com/username/pdf-compressor"
echo ""
echo "Удачи в сжатии PDF файлов! 🗜️"
