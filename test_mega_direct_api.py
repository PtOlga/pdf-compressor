#!/usr/bin/env python3
"""
Тест прямого подключения к Mega API без mega.py
"""

import os
import json
import hashlib
import requests
import time

print("=" * 70)
print("🧪 Тест прямого подключения к Mega API")
print("=" * 70)

# Получаем учетные данные
email = os.getenv('MEGA_EMAIL')
password = os.getenv('MEGA_PASSWORD')

if not email or not password:
    print("❌ Ошибка: Не установлены MEGA_EMAIL и MEGA_PASSWORD")
    exit(1)

print(f"\n📧 Email: {email}")
print(f"🔑 Password: {'*' * len(password)}")

# Функция для хеширования пароля
def prepare_key(password):
    """Подготовка ключа из пароля"""
    aes_key = [0x93, 0xC4, 0x67, 0xE3, 0x7D, 0xB0, 0xC7, 0xA4,
               0xD1, 0xBE, 0x3F, 0x81, 0x01, 0x52, 0xCB, 0x56]
    
    password_bytes = password.encode('utf-8')
    
    for i in range(65536):
        for j in range(0, len(password_bytes), 16):
            chunk = password_bytes[j:j+16]
            chunk = chunk + b'\x00' * (16 - len(chunk))
            
            for k in range(16):
                aes_key[k] ^= chunk[k]
    
    return aes_key

# Функция для вычисления user_hash
def compute_user_hash(email, password_key):
    """Вычисление user_hash"""
    email_bytes = email.lower().encode('utf-8')
    
    # Используем SHA256 для хеширования
    hash_obj = hashlib.sha256()
    hash_obj.update(email_bytes)
    
    return hash_obj.hexdigest()[:16]

print("\n🔐 Попытка подключения к Mega API...")

try:
    # Подготавливаем ключ
    password_key = prepare_key(password)
    print("   ✅ Ключ подготовлен")
    
    # Вычисляем user_hash
    user_hash = compute_user_hash(email, password_key)
    print(f"   ✅ User hash вычислен: {user_hash}")
    
    # Отправляем запрос к API
    url = 'https://g.api.mega.co.nz/cs'
    
    payload = {
        'a': 'us',
        'user': email,
        'uh': user_hash
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Content-Type': 'application/json'
    }
    
    print(f"\n📡 Отправляю запрос к {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    for attempt in range(3):
        try:
            print(f"\n   Попытка {attempt + 1}/3...")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            print(f"   ✅ Статус: {response.status_code}")
            print(f"   📏 Размер ответа: {len(response.text)} байт")
            
            if response.text:
                print(f"   📝 Ответ: {response.text[:200]}")
                
                try:
                    data = response.json()
                    print(f"   ✅ JSON распарсен успешно!")
                    print(f"   📊 Данные: {json.dumps(data, indent=2)[:500]}")
                except json.JSONDecodeError as e:
                    print(f"   ❌ Ошибка парсинга JSON: {e}")
            else:
                print(f"   ⚠️ Пустой ответ от API!")
            
            break
            
        except requests.exceptions.Timeout:
            print(f"   ⏱️ Timeout! Жду 5 сек...")
            time.sleep(5)
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise

except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 70)
print("✅ Тест завершен!")
print("=" * 70)

