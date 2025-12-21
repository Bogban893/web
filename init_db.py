#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных с новыми таблицами
"""
import os
import sys

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.web import app, db

if __name__ == '__main__':
    with app.app_context():
        print("[INFO] Создаю таблицы в БД...")
        db.create_all()
        print("[INFO] Таблицы успешно созданы!")
        
        # Показываем информацию о таблицах
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"[INFO] Существующие таблицы: {', '.join(tables)}")
