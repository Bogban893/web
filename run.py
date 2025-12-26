#!/usr/bin/env python3
"""
Точка входа для запуска Flask приложения
"""

import os
import sys

# Добавляем src в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.web import app

if __name__ == '__main__':
    print(f"[INFO] База данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("[INFO] Запуск Flask приложения...")

    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    )