#!/usr/bin/env python3
"""
PDF Компрессор с поддержкой различных алгоритмов сжатия
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import tempfile
import shutil

# PDF библиотеки
from pypdf import PdfReader, PdfWriter
import pikepdf
from PIL import Image

# Наши модули
from config import get_config
from utils import calculate_savings, format_file_size


class PDFCompressor:
    """Класс для сжатия PDF файлов"""
    
    def __init__(self, level: str = "medium"):
        self.config = get_config()
        self.level = level
        self.compression_settings = self.config.get_compression_settings(level)
        self.logger = logging.getLogger(__name__)
        
        # Проверяем доступность инструментов
        self.available_tools = self._check_available_tools()
        
        if not self.available_tools:
            self.logger.warning("⚠️ Не найдено ни одного инструмента для сжатия PDF")
    
    def _check_available_tools(self) -> Dict[str, bool]:
        """Проверка доступности инструментов сжатия"""
        tools = {}
        
        # Ghostscript
        try:
            result = subprocess.run(['gs', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            tools['ghostscript'] = result.returncode == 0
            if tools['ghostscript']:
                self.logger.info(f"✅ Ghostscript найден: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError):
            tools['ghostscript'] = False
            self.logger.warning("⚠️ Ghostscript не найден")
        
        # QPDF
        try:
            result = subprocess.run(['qpdf', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            tools['qpdf'] = result.returncode == 0
            if tools['qpdf']:
                self.logger.info(f"✅ QPDF найден: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError):
            tools['qpdf'] = False
            self.logger.warning("⚠️ QPDF не найден")
        
        # Python библиотеки всегда доступны
        tools['pikepdf'] = True
        tools['pypdf'] = True
        
        return tools
    
    def compress(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Основной метод сжатия PDF файла
        
        Args:
            input_path: путь к входному файлу
            output_path: путь к выходному файлу
            
        Returns:
            словарь с результатами сжатия
        """
        input_file = Path(input_path)
        output_file = Path(output_path)
        
        if not input_file.exists():
            return self._error_result(f"Входной файл не найден: {input_path}")
        
        # Создаем директорию для выходного файла
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        original_size = input_file.stat().st_size
        
        # Проверяем размер файла
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
        if original_size > max_size_bytes:
            return self._error_result(
                f"Файл слишком большой: {format_file_size(original_size)} > "
                f"{self.config.max_file_size_mb} MB"
            )
        
        min_size_bytes = self.config.min_file_size_kb * 1024
        if original_size < min_size_bytes:
            return self._success_result(
                input_path, output_path, original_size, original_size,
                "Файл слишком маленький для сжатия - скопирован без изменений"
            )
        
        self.logger.info(f"🗜️ Начинаю сжатие {input_file.name} "
                        f"({format_file_size(original_size)}) уровень: {self.level}")
        
        # Выбираем лучший алгоритм сжатия
        compression_method = self._choose_compression_method(input_path, original_size)
        self.logger.info(f"📊 Выбран метод: {compression_method}")
        
        try:
            # Применяем сжатие
            result = self._apply_compression(input_path, output_path, compression_method)
            
            if result['success'] and output_file.exists():
                compressed_size = output_file.stat().st_size
                savings = calculate_savings(original_size, compressed_size)
                
                # Проверяем минимальный процент сжатия
                if savings['percent_saved'] < self.config.min_compression_percent:
                    self.logger.info(f"📊 Сжатие незначительно ({savings['size_reduction']}), "
                                   f"копирую оригинал")
                    shutil.copy2(input_path, output_path)
                    compressed_size = original_size
                
                return self._success_result(
                    input_path, output_path, original_size, compressed_size,
                    f"Сжато методом {compression_method}"
                )
            else:
                return result
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка при сжатии: {str(e)}")
            return self._error_result(f"Ошибка сжатия: {str(e)}")
    
    def _choose_compression_method(self, input_path: str, file_size: int) -> str:
        """
        Выбор оптимального метода сжатия на основе анализа файла
        """
        try:
            # Анализируем PDF файл
            analysis = self._analyze_pdf(input_path)
            
            # Большие файлы с изображениями - Ghostscript
            if (file_size > 10 * 1024 * 1024 and 
                analysis['has_images'] and 
                self.available_tools.get('ghostscript')):
                return 'ghostscript'
            
            # Файлы с формами и аннотациями - Pikepdf (безопаснее)
            if analysis['has_forms'] or analysis['has_annotations']:
                return 'pikepdf'
            
            # Если доступен QPDF - используем его для универсального сжатия
            if self.available_tools.get('qpdf'):
                return 'qpdf'
            
            # Если доступен Ghostscript - используем его
            if self.available_tools.get('ghostscript'):
                return 'ghostscript'
            
            # Fallback на Pikepdf
            return 'pikepdf'
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка анализа файла: {e}")
            # При ошибке анализа используем консервативный метод
            return 'pikepdf'
    
    def _analyze_pdf(self, input_path: str) -> Dict[str, Any]:
        """Анализ PDF файла для выбора оптимального алгоритма сжатия"""
        analysis = {
            'pages': 0,
            'has_images': False,
            'has_forms': False,
            'has_annotations': False,
            'encrypted': False,
            'file_size': Path(input_path).stat().st_size
        }
        
        try:
            with pikepdf.open(input_path) as pdf:
                analysis['pages'] = len(pdf.pages)
                analysis['encrypted'] = False  # если открылся, то не зашифрован
                
                # Проверяем наличие изображений (упрощенно)
                for page in pdf.pages[:min(5, len(pdf.pages))]:  # проверяем первые 5 страниц
                    if '/XObject' in page.get('/Resources', {}):
                        xobjects = page['/Resources']['/XObject']
                        for obj in xobjects.values():
                            if obj.get('/Subtype') == '/Image':
                                analysis['has_images'] = True
                                break
                    
                    # Проверяем аннотации
                    if '/Annots' in page:
                        analysis['has_annotations'] = True
                
                # Проверяем формы (AcroForm)
                if '/AcroForm' in pdf.Root:
                    analysis['has_forms'] = True
                    
        except Exception as e:
            self.logger.debug(f"Ошибка анализа с pikepdf: {e}")
            # Пробуем pypdf
            try:
                reader = PdfReader(input_path)
                analysis['pages'] = len(reader.pages)
                analysis['encrypted'] = reader.is_encrypted
                
                # Простая проверка на наличие изображений
                for page in reader.pages[:min(3, len(reader.pages))]:
                    if '/XObject' in page.get('/Resources', {}):
                        analysis['has_images'] = True
                        break
                        
            except Exception as e2:
                self.logger.debug(f"Ошибка анализа с pypdf: {e2}")
        
        return analysis
    
    def _apply_compression(self, input_path: str, output_path: str, method: str) -> Dict[str, Any]:
        """Применение выбранного метода сжатия"""
        
        try:
            if method == 'ghostscript' and self.available_tools.get('ghostscript'):
                return self._compress_with_ghostscript(input_path, output_path)
            elif method == 'qpdf' and self.available_tools.get('qpdf'):
                return self._compress_with_qpdf(input_path, output_path)
            elif method == 'pikepdf':
                return self._compress_with_pikepdf(input_path, output_path)
            else:
                # Fallback на pypdf
                return self._compress_with_pypdf(input_path, output_path)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка в методе {method}: {e}")
            
            # Пробуем запасной метод
            if method != 'pikepdf':
                self.logger.info("🔄 Пробую запасной метод: pikepdf")
                return self._compress_with_pikepdf(input_path, output_path)
            else:
                return self._error_result(f"Все методы сжатия не удались: {str(e)}")
    
    def _compress_with_ghostscript(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Сжатие с помощью Ghostscript"""
        preset = self.compression_settings.get('ghostscript_preset', 'ebook')
        
        # Команда Ghostscript
        cmd = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/' + preset,
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={output_path}',
            input_path
        ]
        
        # Дополнительные настройки для более агрессивного сжатия
        if self.level in ['medium', 'high']:
            image_quality = self.compression_settings.get('image_quality', 75)
            image_resolution = self.compression_settings.get('image_resolution', 150)
            
            additional_params = [
                f'-dColorImageResolution={image_resolution}',
                f'-dGrayImageResolution={image_resolution}',
                f'-dMonoImageResolution={image_resolution}',
                '-dColorImageDownsampleType=/Bicubic',
                '-dGrayImageDownsampleType=/Bicubic',
                '-dMonoImageDownsampleType=/Bicubic',
                f'-dColorImageDownsampleThreshold=1.0',
                f'-dGrayImageDownsampleThreshold=1.0',
                '-dOptimize=true',
                '-dEmbedAllFonts=true'
            ]
            
            # Добавляем параметры перед последними двумя аргументами
            cmd = cmd[:-2] + additional_params + cmd[-2:]
        
        try:
            self.logger.debug(f"Ghostscript команда: {' '.join(cmd)}")
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=300)  # 5 минут таймаут
            
            if result.returncode == 0:
                return {'success': True, 'method': 'ghostscript', 'error': None}
            else:
                error_msg = result.stderr or f"Ghostscript завершился с кодом {result.returncode}"
                return self._error_result(f"Ghostscript ошибка: {error_msg}")
                
        except subprocess.TimeoutExpired:
            return self._error_result("Ghostscript превысил время ожидания (5 мин)")
        except Exception as e:
            return self._error_result(f"Ошибка запуска Ghostscript: {str(e)}")
    
    def _compress_with_qpdf(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Сжатие с помощью QPDF"""
        cmd = [
            'qpdf', 
            '--linearize',  # Оптимизация для веб
            '--compress-streams=y',
            '--recompress-flate',
            '--compression-level=9',
            input_path, 
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=180)  # 3 минуты
            
            if result.returncode == 0:
                return {'success': True, 'method': 'qpdf', 'error': None}
            elif result.returncode == 3 or "operation succeeded with warnings" in result.stderr:
                # Warnings are OK - file was processed successfully
                self.logger.debug(f"QPDF warning (non-critical): {result.stderr}")
                return {"success": True, "method": "qpdf", "error": None}
            else:
                error_msg = result.stderr or f"QPDF завершился с кодом {result.returncode}"
                return self._error_result(f"QPDF ошибка: {error_msg}")
                
        except subprocess.TimeoutExpired:
            return self._error_result("QPDF превысил время ожидания")
        except Exception as e:
            return self._error_result(f"Ошибка запуска QPDF: {str(e)}")
    
    def _compress_with_pikepdf(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Сжатие с помощью Pikepdf"""
        try:
            with pikepdf.open(input_path) as pdf:
                # Применяем различные оптимизации
                for page in pdf.pages:
                    # Сжимаем содержимое страниц
                    page.compress_content_streams()
                    
                    # Оптимизируем изображения (если уровень high)
                    if self.level == 'high':
                        self._optimize_page_images(page)
                
                # Удаляем неиспользуемые объекты
                pdf.remove_unreferenced_resources()
                
                # Сохраняем с максимальным сжатием
                pdf.save(output_path, 
                        compress_streams=True,
                        stream_decode_level=pikepdf.StreamDecodeLevel.all,
                        object_stream_mode=pikepdf.ObjectStreamMode.generate,
                        minimize_size=True)
                
                return {'success': True, 'method': 'pikepdf', 'error': None}
                
        except Exception as e:
            return self._error_result(f"Pikepdf ошибка: {str(e)}")
    
    def _compress_with_pypdf(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Сжатие с помощью PyPDF (базовый метод)"""
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Копируем все страницы с компрессией
            for page in reader.pages:
                page.compress_content_streams()  # Сжимаем потоки содержимого
                writer.add_page(page)
            
            # Удаляем дубликаты объектов
            writer.remove_duplicates()
            
            # Сохраняем
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
                
            return {'success': True, 'method': 'pypdf', 'error': None}
            
        except Exception as e:
            return self._error_result(f"PyPDF ошибка: {str(e)}")
    
    def _optimize_page_images(self, page):
        """Оптимизация изображений на странице (экспериментальная функция)"""
        try:
            # Этот метод требует более сложной реализации
            # Пока оставляем заглушку
            pass
        except Exception as e:
            self.logger.debug(f"Ошибка оптимизации изображений: {e}")
    
    def _success_result(self, input_path: str, output_path: str, 
                       size_before: int, size_after: int, message: str = "") -> Dict[str, Any]:
        """Формирование результата успешного сжатия"""
        savings = calculate_savings(size_before, size_after)
        
        return {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'size_before': size_before,
            'size_after': size_after,
            'bytes_saved': savings['bytes_saved'],
            'percent_saved': savings['percent_saved'],
            'compression_ratio': savings['compression_ratio'],
            'message': message,
            'error': None
        }
    
    def _error_result(self, error_message: str) -> Dict[str, Any]:
        """Формирование результата ошибки"""
        return {
            'success': False,
            'input_path': None,
            'output_path': None,
            'size_before': 0,
            'size_after': 0,
            'bytes_saved': 0,
            'percent_saved': 0,
            'compression_ratio': 0,
            'message': "",
            'error': error_message
        }
    
    def verify_compressed_file(self, file_path: str) -> bool:
        """Проверка целостности сжатого PDF файла"""
        try:
            # Проверяем с помощью pikepdf
            with pikepdf.open(file_path):
                pass
            
            # Проверяем с помощью pypdf
            reader = PdfReader(file_path)
            len(reader.pages)  # Пытаемся прочитать количество страниц
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Проверка файла {file_path} не удалась: {e}")
            return False
    
    def get_compression_info(self) -> Dict[str, Any]:
        """Информация о текущих настройках компрессора"""
        return {
            'level': self.level,
            'settings': self.compression_settings,
            'available_tools': self.available_tools,
            'max_file_size_mb': self.config.max_file_size_mb,
            'min_file_size_kb': self.config.min_file_size_kb,
            'min_compression_percent': self.config.min_compression_percent
        }


def test_compressor():
    """Тестирование компрессора"""
    import tempfile
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    print("🧪 Тестирование PDF компрессора...")
    
    # Создаем тестовый PDF файл
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as test_input:
        c = canvas.Canvas(test_input.name, pagesize=letter)
        width, height = letter
        
        # Добавляем много текста для увеличения размера
        for i in range(100):
            c.drawString(100, height - 50 - i*10, f"Тестовая строка номер {i} " * 10)
        
        c.save()
        test_input_path = test_input.name
    
    # Создаем компрессор
    compressor = PDFCompressor(level="medium")
    print(f"📊 Доступные инструменты: {compressor.available_tools}")
    
    # Тестируем сжатие
    with tempfile.NamedTemporaryFile(suffix='_compressed.pdf', delete=False) as test_output:
        test_output_path = test_output.name
    
    result = compressor.compress(test_input_path, test_output_path)
    
    if result['success']:
        print(f"✅ Сжатие успешно!")
        print(f"   📄 Размер до: {format_file_size(result['size_before'])}")
        print(f"   📄 Размер после: {format_file_size(result['size_after'])}")
        print(f"   💾 Экономия: {result['percent_saved']:.1f}%")
        print(f"   🔧 Метод: {result.get('method', 'неизвестно')}")
    else:
        print(f"❌ Ошибка сжатия: {result['error']}")
    
    # Очистка
    Path(test_input_path).unlink(missing_ok=True)
    Path(test_output_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_compressor()
