#!/usr/bin/env python3
"""
Скрипт для обновления статистики в README файле
"""

import json
import re
from pathlib import Path
from datetime import datetime


def load_stats(stats_path: str = 'temp/logs/stats.json') -> dict:
    """Загрузка статистики из JSON файла"""
    stats_file = Path(stats_path)
    if not stats_file.exists():
        return {}
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def format_file_size(bytes_size: int) -> str:
    """Форматирование размера файла"""
    if bytes_size == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def update_readme_stats():
    """Обновление статистики в README файле"""
    readme_file = Path('README.md')
    if not readme_file.exists():
        print("❌ README.md not found")
        return
    
    # Загружаем текущую статистику
    stats = load_stats()
    if not stats:
        print("ℹ️ No stats to update")
        return
    
    # Читаем README
    with open(readme_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Подготавливаем данные для обновления
    processed_files = stats.get('processed_files', 0)
    total_saved = stats.get('total_bytes_saved', 0)
    percent_saved = stats.get('total_percent_saved', 0)
    last_run = stats.get('timestamp', datetime.now().isoformat())
    
    # Парсим дату
    try:
        last_run_date = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
        last_run_str = last_run_date.strftime('%Y-%m-%d')
    except:
        last_run_str = datetime.now().strftime('%Y-%m-%d')
    
    # Создаем статистику блок
    stats_block = f"""
## 📊 Recent Statistics

- **Last run:** {last_run_str}
- **Files processed:** {processed_files}
- **Space saved:** {format_file_size(total_saved)} ({percent_saved:.1f}%)
- **Compression level:** {stats.get('compression_level', 'medium')}

*Statistics updated automatically after each compression job.*

"""
    
    # Ищем существующий блок статистики или место для вставки
    stats_pattern = r'## 📊 Recent Statistics.*?(?=\n##|\n---|\Z)'
    
    if re.search(stats_pattern, content, re.DOTALL):
        # Заменяем существующий блок
        content = re.sub(stats_pattern, stats_block.strip(), content, flags=re.DOTALL)
    else:
        # Вставляем после основного описания
        insertion_point = content.find('## 📖 Использование')
        if insertion_point == -1:
            insertion_point = content.find('## 🚀 Быстрый старт')
        
        if insertion_point != -1:
            content = content[:insertion_point] + stats_block + '\n' + content[insertion_point:]
        else:
            # Добавляем в конец
            content += '\n' + stats_block
    
    # Сохраняем обновленный README
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ README.md updated with stats:")
    print(f"   📄 Files processed: {processed_files}")
    print(f"   💾 Space saved: {format_file_size(total_saved)}")
    print(f"   📅 Last run: {last_run_str}")


if __name__ == "__main__":
    update_readme_stats()
