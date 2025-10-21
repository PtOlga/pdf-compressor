#!/usr/bin/env python3
"""
Детальный тест Mega API
"""

import os
import json
import hashlib
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

email = os.getenv('MEGA_EMAIL')
password = os.getenv('MEGA_PASSWORD')

print("=" * 70)
print("🔍 ДЕТАЛЬНЫЙ ТЕСТ MEGA API")
print("=" * 70)

print(f"\n🔐 Email: {email}")
print(f"🔐 Password: {password}")

# Функция для хеширования пароля (как в mega.py)
def prepare_key(password):
    """Подготовка ключа из пароля"""
    aes_key = [0x93, 0xC4, 0x67, 0xE3, 0x7D, 0xB0, 0xC7, 0xA4,
               0xD1, 0xBE, 0x3F, 0x81, 0x01, 0x52, 0xCB, 0x56]
    
    password_bytes = password.encode('utf-8')
    
    for i in range(0, len(password_bytes), 16):
        chunk = password_bytes[i:i+16]
        chunk = chunk + b'\x00' * (16 - len(chunk))
        
        for j in range(16):
            aes_key[j] ^= chunk[j]
    
    return aes_key

# Функция для вычисления user_hash (как в mega.py)
def compute_user_hash(email, password):
    """Вычисление user_hash"""
    aes_key = prepare_key(password)
    
    # Хешируем email
    email_bytes = email.encode('utf-8')
    
    # Используем SHA256
    import hashlib
    hash_obj = hashlib.sha256()
    hash_obj.update(email_bytes)
    
    # Берем первые 16 байт хеша
    hash_bytes = hash_obj.digest()[:16]
    
    # XOR с ключом
    user_hash = bytes(hash_bytes[i] ^ aes_key[i] for i in range(16))
    
    # Конвертируем в base64
    import base64
    user_hash_b64 = base64.b64encode(user_hash).decode('utf-8').rstrip('=')
    
    return user_hash_b64

print("\n🔐 Вычисление user_hash...")
try:
    user_hash = compute_user_hash(email, password)
    print(f"   ✅ user_hash: {user_hash}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    exit(1)

# Отправляем запрос к API
print("\n📡 Отправка запроса к Mega API...")
try:
    url = 'https://g.api.mega.co.nz/cs'
    payload = {
        'a': 'us',
        'user': email,
        'uh': user_hash
    }
    
    print(f"   URL: {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, timeout=10)
    
    print(f"\n   ✅ Статус: {response.status_code}")
    print(f"   Заголовки: {dict(response.headers)}")
    print(f"   Тело ответа: {response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"   JSON: {json.dumps(data, indent=2)}")
        except:
            print(f"   ⚠️ Не удалось распарсить JSON")
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)

