#!/usr/bin/env python3
"""
Скрипт для генерации отчетов о сжатии PDF файлов
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def parse_log_file(log_path: str) -> Dict[str, Any]:
    """Парсинг лог-файла для извлечения статистики"""
    
    log_file = Path(log_path)
    if not log_file.exists():
        return {'error': f'Log file not found: {log_path}'}
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Инициализируем статистику
        stats = {
            'processed_files': 0,
            'failed_files': 0,
            'total_size_before': 0,
            'total_size_after': 0,
            'total_bytes_saved': 0,
            'files': [],
            'errors': [],
            'duration': '0',
            'compression_level': 'unknown',
            'start_time': '',
            'end_time': ''
        }
        
        # Регулярные выражения для извлечения данных
        patterns = {
            'file_start': r'📄 \[(\d+)/(\d+)\] (.+)',
            'file_size': r'📊 Размер: (.+)',
            'compression_result': r'💾 Экономия: (.+) \((.+)%\)',
            'error': r'❌ (.+)',
            'duration': r'⏱️ Время работы: (.+)',
            'processed': r'✅ Обработано файлов: (\d+)',
            'failed': r'❌ Ошибок: (\d+)',
            'total_before': r'📊 Размер до сжатия: (.+)',
            'total_after': r'📊 Размер после сжатия: (.+)',
            'total_saved': r'💾 Общая экономия: (.+)',
            'compression_level': r'🗜️ Уровень сжатия: (\w+)',
            'start_time': r'⏰ Время запуска: (.+)',
        }
        
        lines = content.split('\n')
        current_file = None
        
        for line in lines:
            # Обрабатываем каждую строку
            for pattern_name, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    if pattern_name == 'file_start':
                        current_file = {
                            'name': match.group(3),
                            'index': int(match.group(1)),
                            'total': int(match.group(2))
                        }
                    elif pattern_name == 'file_size' and current_file:
                        current_file['original_size_str'] = match.group(1)
                    elif pattern_name == 'compression_result' and current_file:
                        current_file['savings'] = match.group(1)
                        current_file['percent_saved'] = float(match.group(2))
                        stats['files'].append(current_file)
                        current_file = None
                    elif pattern_name == 'error':
                        stats['errors'].append(match.group(1))
                    elif pattern_name == 'duration':
                        stats['duration'] = match.group(1)
                    elif pattern_name == 'processed':
                        stats['processed_files'] = int(match.group(1))
                    elif pattern_name == 'failed':
                        stats['failed_files'] = int(match.group(1))
                    elif pattern_name == 'total_before':
                        stats['total_size_before_str'] = match.group(1)
                    elif pattern_name == 'total_after':
                        stats['total_size_after_str'] = match.group(1)
                    elif pattern_name == 'total_saved':
                        stats['total_saved_str'] = match.group(1)
                    elif pattern_name == 'compression_level':
                        stats['compression_level'] = match.group(1)
                    elif pattern_name == 'start_time':
                        stats['start_time'] = match.group(1)
        
        return stats
        
    except Exception as e:
        return {'error': f'Error parsing log file: {str(e)}'}


def load_json_stats(stats_path: str = 'temp/logs/stats.json') -> Dict[str, Any]:
    """Загрузка JSON статистики если доступна"""
    
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
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def generate_report(log_path: str, stats_path: str = None) -> str:
    """Генерация отчета о сжатии"""
    
    # Загружаем данные из лога
    log_stats = parse_log_file(log_path)
    
    # Загружаем JSON статистику если доступна
    json_stats = {}
    if stats_path:
        json_stats = load_json_stats(stats_path)
    
    # Объединяем статистику (приоритет JSON)
    stats = {**log_stats, **json_stats}
    
    if 'error' in stats:
        return f"# ❌ Error generating report\n\n{stats['error']}"
    
    # Генерируем отчет
    report = []
    
    # Заголовок
    report.append("# 📊 PDF Compression Report")
    report.append("")
    
    # Общая информация
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    report.append(f"**Generated:** {timestamp}")
    report.append(f"**Compression Level:** {stats.get('compression_level', 'unknown')}")
    report.append(f"**Duration:** {stats.get('duration', 'unknown')}")
    report.append("")
    
    # Основная статистика
    report.append("## 📈 Summary")
    report.append("")
    
    processed = stats.get('processed_files', 0)
    failed = stats.get('failed_files', 0)
    total = processed + failed
    
    if total > 0:
        success_rate = (processed / total) * 100
        report.append(f"- ✅ **Successfully processed:** {processed} files ({success_rate:.1f}%)")
        
        if failed > 0:
            report.append(f"- ❌ **Failed:** {failed} files")
        
        # Экономия места
        if 'total_bytes_saved' in stats and stats['total_bytes_saved'] > 0:
            total_saved = format_file_size(stats['total_bytes_saved'])
            percent_saved = stats.get('total_percent_saved', 0)
            
            report.append(f"- 💾 **Space saved:** {total_saved} ({percent_saved:.1f}%)")
            
            if 'total_size_before' in stats:
                size_before = format_file_size(stats['total_size_before'])
                size_after = format_file_size(stats.get('total_size_after', 0))
                report.append(f"  - Before: {size_before}")
                report.append(f"  - After: {size_after}")
        
        # Информация из лога (если JSON недоступен)
        elif 'total_saved_str' in stats:
            report.append(f"- 💾 **Space saved:** {stats['total_saved_str']}")
            if 'total_size_before_str' in stats:
                report.append(f"  - Before: {stats['total_size_before_str']}")
                report.append(f"  - After: {stats.get('total_size_after_str', 'unknown')}")
    else:
        report.append("- ℹ️ **No files processed**")
    
    report.append("")
    
    # Детали по файлам
    files = stats.get('files', [])
    if files and len(files) <= 10:  # Показываем детали только если файлов немного
        report.append("## 📄 Processed Files")
        report.append("")
        
        for file_info in files:
            if isinstance(file_info, dict):
                name = file_info.get('name', 'unknown')
                
                # Из JSON статистики
                if 'percent_saved' in file_info:
                    savings = f"{file_info['percent_saved']:.1f}%"
                    if 'bytes_saved' in file_info:
                        bytes_saved = format_file_size(file_info['bytes_saved'])
                        savings = f"{bytes_saved} ({savings})"
                # Из лога
                elif 'savings' in file_info:
                    savings = f"{file_info['savings']} ({file_info.get('percent_saved', 0):.1f}%)"
                else:
                    savings = "unknown"
                
                report.append(f"- **{name}:** {savings}")
        
        report.append("")
    
    elif len(files) > 10:
        report.append(f"## 📄 Files Summary")
        report.append("")
        report.append(f"Processed {len(files)} files. Top performers:")
        report.append("")
        
        # Сортируем по проценту экономии и показываем топ-5
        sorted_files = sorted(files, 
                            key=lambda x: x.get('percent_saved', 0), 
                            reverse=True)
        
        for file_info in sorted_files[:5]:
            if isinstance(file_info, dict):
                name = file_info.get('name', 'unknown')
                percent = file_info.get('percent_saved', 0)
                report.append(f"- **{name}:** {percent:.1f}% saved")
        
        report.append("")
    
    # Ошибки
    errors = stats.get('errors', [])
    if errors:
        report.append("## ❌ Errors")
        report.append("")
        
        for error in errors[:5]:  # Показываем первые 5 ошибок
            if isinstance(error, dict):
                file_name = error.get('file', 'unknown')
                error_msg = error.get('error', 'unknown error')
                report.append(f"- **{file_name}:** {error_msg}")
            elif isinstance(error, str):
                report.append(f"- {error}")
        
        if len(errors) > 5:
            report.append(f"- ... and {len(errors) - 5} more errors")
        
        report.append("")
    
    # Статус
    if processed > 0 and failed == 0:
        status_emoji = "✅"
        status_text = "All files processed successfully"
    elif processed > 0 and failed > 0:
        status_emoji = "⚠️"
        status_text = f"Partially successful ({failed} failures)"
    elif failed > 0:
        status_emoji = "❌"
        status_text = "Processing failed"
    else:
        status_emoji = "ℹ️"
        status_text = "No files to process"
    
    report.append(f"## {status_emoji} Status")
    report.append("")
    report.append(f"**{status_text}**")
    report.append("")
    
    # Техническая информация
    if json_stats:
        report.append("---")
        report.append("*Report generated from JSON statistics*")
    else:
        report.append("---")
        report.append("*Report generated from log file parsing*")
    
    return "\n".join(report)


def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Usage: python generate_report.py <log_file> [stats_file]")
        sys.exit(1)
    
    log_file = sys.argv[1]
    stats_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    report = generate_report(log_file, stats_file)
    print(report)


if __name__ == "__main__":
    main()
