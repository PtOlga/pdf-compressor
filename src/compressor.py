#!/usr/bin/env python3
"""
PDF Компрессор с поддержкой различных алгоритмов сжатия и fallback-логикой
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import shutil

# PDF библиотеки
from pypdf import PdfReader, PdfWriter
import pikepdf

# Наши модули
from config import get_config
from utils import calculate_savings, format_file_size


class PDFCompressor:
    """Класс для сжатия PDF файлов с fallback-поддержкой"""
    
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
        
        # Анализируем файл и логируем тип содержимого
        analysis = self._analyze_pdf(input_path)
        self.logger.info(
            "🔎 Анализ: pages=%s, images=%s, forms=%s, annots=%s, encrypted=%s",
            analysis.get('pages', 0),
            analysis.get('has_images', False),
            analysis.get('has_forms', False),
            analysis.get('has_annotations', False),
            analysis.get('encrypted', False),
        )
        # Определяем тип содержимого
        if analysis.get('has_images') and not (analysis.get('has_forms') or analysis.get('has_annotations')):
            content_type = 'image-heavy/scanned'
        elif analysis.get('has_forms') or analysis.get('has_annotations'):
            content_type = 'interactive/forms/annotations'
        else:
            content_type = 'text-based/standard'
        self.logger.info(f"🧭 Тип содержимого: {content_type}")

        # Выбираем предпочтительный метод
        preferred_method = self._choose_compression_method(input_path, original_size, analysis=analysis)
        self.logger.info(f"📊 Предпочтительный метод: {preferred_method}")

        try:
            # Применяем сжатие с fallback
            result = self._apply_compression(input_path, output_path, preferred_method)

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
                    f"Сжато методом {result.get('method', 'unknown')}"
                )
            else:
                return result
                
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при сжатии: {str(e)}")
            return self._error_result(f"Неожиданная ошибка: {str(e)}")
    
    def _choose_compression_method(self, input_path: str, file_size: int, analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        Выбор предпочтительного метода сжатия на основе анализа файла
        """
        try:
            analysis = analysis or self._analyze_pdf(input_path)

            # Большие файлы с изображениями → Ghostscript
            if (file_size > 10 * 1024 * 1024 and
                analysis.get('has_images') and
                self.available_tools.get('ghostscript')):
                return 'ghostscript'

            # Файлы с формами/аннотациями → Pikepdf
            if analysis.get('has_forms') or analysis.get('has_annotations'):
                return 'pikepdf'

            # QPDF — универсальный выбор, если доступен
            if self.available_tools.get('qpdf'):
                return 'qpdf'

            # Иначе Ghostscript, если есть
            if self.available_tools.get('ghostscript'):
                return 'ghostscript'

            return 'pikepdf'

        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка анализа файла: {e}")
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
                analysis['encrypted'] = False
                
                for page in pdf.pages[:min(5, len(pdf.pages))]:
                    if '/XObject' in page.get('/Resources', {}):
                        xobjects = page['/Resources']['/XObject']
                        for obj in xobjects.values():
                            if obj.get('/Subtype') == '/Image':
                                analysis['has_images'] = True
                                break
                    
                    if '/Annots' in page:
                        analysis['has_annotations'] = True
                
                if '/AcroForm' in pdf.Root:
                    analysis['has_forms'] = True
                    
        except Exception as e:
            self.logger.debug(f"Ошибка анализа с pikepdf: {e}")
            try:
                reader = PdfReader(input_path)
                analysis['pages'] = len(reader.pages)
                analysis['encrypted'] = reader.is_encrypted
                for page in reader.pages[:min(3, len(reader.pages))]:
                    if '/XObject' in page.get('/Resources', {}):
                        analysis['has_images'] = True
                        break
            except Exception as e2:
                self.logger.debug(f"Ошибка анализа с pypdf: {e2}")
        
        return analysis
    
    def _apply_compression(self, input_path: str, output_path: str, preferred_method: str) -> Dict[str, Any]:
        """
        Применяет сжатие с fallback-цепочкой: сначала preferred_method,
        затем остальные доступные методы по приоритету. Если экономия 0% или меньше,
        пробуем следующий метод.
        """
        all_methods = ['ghostscript', 'qpdf', 'pikepdf', 'pypdf']
        available_methods = [
            m for m in all_methods
            if self.available_tools.get(m, True)
        ]

        if preferred_method in available_methods:
            methods_to_try = [preferred_method] + [m for m in available_methods if m != preferred_method]
        else:
            methods_to_try = available_methods

        self.logger.debug(f"Планирую попробовать методы в порядке: {methods_to_try}")

        last_error = None
        original_size = Path(input_path).stat().st_size if Path(input_path).exists() else 0

        for idx, method in enumerate(methods_to_try):
            self.logger.info(f"🔄 Пробую метод сжатия: {method}")
            try:
                if method == 'ghostscript':
                    result = self._compress_with_ghostscript(input_path, output_path)
                elif method == 'qpdf':
                    result = self._compress_with_qpdf(input_path, output_path)
                elif method == 'pikepdf':
                    result = self._compress_with_pikepdf(input_path, output_path)
                elif method == 'pypdf':
                    result = self._compress_with_pypdf(input_path, output_path)
                else:
                    result = self._error_result(f"Неизвестный метод: {method}")
                    continue

                if result['success']:
                    # Оцениваем экономию
                    try:
                        if Path(output_path).exists() and original_size > 0:
                            out_size = Path(output_path).stat().st_size
                            savings = calculate_savings(original_size, out_size)
                            self.logger.info(
                                "   → %s: %s (%s → %s)",
                                method,
                                savings['size_reduction'],
                                format_file_size(original_size),
                                format_file_size(out_size)
                            )
                            # Если нет экономии и есть ещё методы — пробуем следующий
                            if savings['percent_saved'] <= 0 and idx < len(methods_to_try) - 1:
                                self.logger.info("📉 Выигрыш 0%%, пробую следующий метод...")
                                try:
                                    Path(output_path).unlink(missing_ok=True)
                                except Exception:
                                    pass
                                continue
                    except Exception as e:
                        self.logger.debug(f"⚠️ Не удалось оценить экономию: {e}")

                    result['method'] = method
                    return result
                else:
                    error_msg = result.get('error') or "Неизвестная ошибка"
                    self.logger.warning(f"Метод {method} завершился неудачей: {error_msg}")
                    last_error = error_msg

            except Exception as e:
                error_msg = f"Исключение в {method}: {str(e)}"
                self.logger.error(error_msg)
                last_error = error_msg
                continue

        final_error = f"Все методы сжатия завершились неудачей. Последняя ошибка: {last_error}"
        self.logger.error(final_error)
        return self._error_result(final_error)

    def _compress_with_ghostscript(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Сжатие с помощью Ghostscript"""
        preset = self.compression_settings.get('ghostscript_preset', 'ebook')
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
            cmd = cmd[:-2] + additional_params + cmd[-2:]
        
        try:
            self.logger.debug(f"Ghostscript команда: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return {'success': True, 'error': None}
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
            '--linearize',
            '--compress-streams=y',
            '--recompress-flate',
            '--compression-level=9',
            input_path,
            output_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                return {'success': True, 'error': None}
            elif result.returncode == 3 or "operation succeeded with warnings" in result.stderr:
                self.logger.debug(f"QPDF warning (non-critical): {result.stderr}")
                return {"success": True, "error": None}
            else:
                error_msg = result.stderr or f"QPDF завершился с кодом {result.returncode}"
                return self._error_result(f"QPDF ошибка: {error_msg}")
        except subprocess.TimeoutExpired:
            return self._error_result("QPDF превысил время ожидания")
        except Exception as e:
            return self._error_result(f"Ошибка запуска QPDF: {str(e)}")
    
    def _compress_with_pikepdf(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Сжатие с помощью Pikepdf с устойчивостью к ошибкам потоков"""
        try:
            with pikepdf.open(input_path) as pdf:
                for page in pdf.pages:
                    try:
                        page.compress_content_streams()
                    except Exception as e:
                        self.logger.debug(f"⚠️ Не удалось сжать потоки на странице: {e}. Пропускаем.")
                    if self.level == 'high':
                        self._optimize_page_images(page)
                pdf.remove_unreferenced_resources()
                pdf.save(
                    output_path,
                    compress_streams=True,
                    stream_decode_level=pikepdf.StreamDecodeLevel.all,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate
                )
                return {'success': True, 'error': None}
        except Exception as e:
            return self._error_result(f"Pikepdf ошибка: {str(e)}")
    
    def _compress_with_pypdf(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Сжатие с помощью PyPDF (базовый метод)"""
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            for page in reader.pages:
                try:
                    page.compress_content_streams()
                except Exception as e:
                    self.logger.debug(f"⚠️ PyPDF не смог сжать потоки: {e}")
                writer.add_page(page)
            # writer.remove_duplicates()  # removed: not available in pypdf 4.x
            with open(output_path, 'wb') as f:
                writer.write(f)
            return {'success': True, 'error': None}
        except Exception as e:
            return self._error_result(f"PyPDF ошибка: {str(e)}")
    
    def _optimize_page_images(self, page):
        """Заглушка для будущей оптимизации изображений"""
        pass
    
    def _success_result(self, input_path: str, output_path: str, 
                       size_before: int, size_after: int, message: str = "") -> Dict[str, Any]:
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
            with pikepdf.open(file_path):
                pass
            reader = PdfReader(file_path)
            len(reader.pages)
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
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as test_input:
        c = canvas.Canvas(test_input.name, pagesize=letter)
        width, height = letter
        for i in range(100):
            c.drawString(100, height - 50 - i*10, f"Тестовая строка номер {i} " * 10)
        c.save()
        test_input_path = test_input.name

    compressor = PDFCompressor(level="medium")
    print(f"📊 Доступные инструменты: {compressor.available_tools}")

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
    
    Path(test_input_path).unlink(missing_ok=True)
    Path(test_output_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_compressor()