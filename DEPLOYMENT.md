# Инструкция по развертыванию на Production

## Предварительная подготовка

### 1. Сервер и домен
- [ ] Зарегистрирован домен
- [ ] Есть VPS/хостинг с SSH доступом
- [ ] Python 3.8+ установлен на сервере
- [ ] Есть SSL сертификат (Let's Encrypt)

### 2. Яндекс настройки
- [ ] Зарегистрировано приложение на https://oauth.yandex.ru/client/my
- [ ] Добавлен redirect URI: `https://yourdomain.com/auth/yandex/callback`
- [ ] Скопированы Client ID и Client Secret

## Развертывание

### Шаг 1: Клонирование кода на сервер

```bash
# Подключиться к серверу
ssh user@yourdomain.com

# Создать директорию проекта
mkdir -p /var/www/portfolio
cd /var/www/portfolio

# Клонировать репозиторий
git clone <your-repo-url> .
```

### Шаг 2: Подготовка Python окружения

```bash
# Обновить pip
python3 -m pip install --upgrade pip

# Создать виртуальное окружение
python3 -m venv venv

# Активировать окружение
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Создать .env файл
cp .env.example .env
```

### Шаг 3: Конфигурация .env

```bash
# Отредактировать .env файл
nano .env
```

Заполнить следующие значения:

```env
SECRET_KEY=your-secure-random-key-change-this
YANDEX_CLIENT_ID=<ваш-client-id>
YANDEX_CLIENT_SECRET=<ваш-client-secret>
YANDEX_REDIRECT_URI=https://yourdomain.com/auth/yandex/callback
```

**Генерация безопасного SECRET_KEY:**
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Шаг 4: Инициализация БД

```bash
# Активировать окружение если не активировано
source venv/bin/activate

# Инициализировать БД
python3 -c "from src.web import app, db; app.app_context().push(); db.create_all()"
```

### Шаг 5: Установка WSGI сервера

```bash
# Установить gunicorn
pip install gunicorn

# Добавить в requirements.txt
echo "gunicorn==21.2.0" >> requirements.txt
```

### Шаг 6: Настройка systemd сервиса

Создать файл `/etc/systemd/system/portfolio.service`:

```bash
sudo nano /etc/systemd/system/portfolio.service
```

Содержимое:

```ini
[Unit]
Description=Portfolio Flask Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/portfolio
ExecStart=/var/www/portfolio/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активировать сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable portfolio
sudo systemctl start portfolio
sudo systemctl status portfolio
```

### Шаг 7: Настройка Nginx

Создать конфиг файл `/etc/nginx/sites-available/portfolio`:

```bash
sudo nano /etc/nginx/sites-available/portfolio
```

Содержимое:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL сертификаты (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL конфигурация
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Размер загружаемых файлов
    client_max_body_size 20M;
    
    # Статические файлы
    location /static/ {
        alias /var/www/portfolio/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Проксирование на Flask
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout настройки
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Включить сайт:

```bash
sudo ln -s /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/
sudo nginx -t  # Проверить конфиг
sudo systemctl restart nginx
```

### Шаг 8: Установка SSL сертификата (Let's Encrypt)

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

### Шаг 9: Настройка логирования

Создать файл для логов:

```bash
sudo mkdir -p /var/log/portfolio
sudo touch /var/log/portfolio/flask.log
sudo touch /var/log/portfolio/gunicorn.log
sudo chown www-data:www-data /var/log/portfolio -R
sudo chmod 755 /var/log/portfolio
```

Обновить код Flask для логирования в `src/web.py`:

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('/var/log/portfolio/flask.log', 
                                       maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
```

## Автоматическое обновление SSL сертификата

Добавить cron задачу:

```bash
sudo crontab -e
```

Добавить строку:

```
0 3 * * * /usr/bin/certbot renew --quiet
```

## Мониторинг

### Проверка статуса приложения

```bash
# Статус сервиса
sudo systemctl status portfolio

# Логи сервиса
sudo journalctl -u portfolio -f

# Логи Flask приложения
tail -f /var/log/portfolio/flask.log

# Проверка портов
sudo netstat -tlnp | grep 8000
sudo netstat -tlnp | grep 80
sudo netstat -tlnp | grep 443
```

### Health check

Добавить endpoint для проверки здоровья в `src/web.py`:

```python
@app.route('/health')
def health_check():
    return {'status': 'ok'}, 200
```

Использовать для мониторинга:

```bash
curl https://yourdomain.com/health
```

## Обновление приложения

### Обновление кода

```bash
cd /var/www/portfolio
source venv/bin/activate

# Получить обновления
git pull origin main

# Установить новые зависимости
pip install -r requirements.txt

# Перезагрузить приложение
sudo systemctl restart portfolio
```

### Обновление зависимостей

```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
```

## Резервное копирование

### Резервная копия БД

```bash
# Ручное резервное копирование
cp /var/www/portfolio/site.db /var/backups/portfolio/site.db.$(date +%Y%m%d_%H%M%S)

# Автоматическое резервное копирование
0 2 * * * cp /var/www/portfolio/site.db /var/backups/portfolio/site.db.$(date +\%Y\%m\%d) && find /var/backups/portfolio -name "site.db.*" -mtime +30 -delete
```

## Возможные проблемы

### 1. 502 Bad Gateway

```bash
# Проверить статус gunicorn
sudo systemctl status portfolio

# Проверить логи
sudo journalctl -u portfolio -n 50

# Перезагрузить
sudo systemctl restart portfolio
```

### 2. Permission Denied

```bash
# Проверить права доступа
ls -la /var/www/portfolio
ls -la /var/log/portfolio

# Исправить права
sudo chown www-data:www-data /var/www/portfolio -R
sudo chmod 755 /var/www/portfolio
```

### 3. SSL ошибка

```bash
# Проверить сертификат
sudo certbot certificates

# Обновить сертификат вручную
sudo certbot renew --force-renewal
```

### 4. Из-за проблемы с Яндекс OAuth

```bash
# Проверить логи ошибок
tail -f /var/log/portfolio/flask.log

# Убедиться что REDIRECT_URI правильно указан в .env и в Яндекс консоли
cat /var/www/portfolio/.env | grep YANDEX
```

## Проверка безопасности

- [ ] SECRET_KEY в .env (не в коде)
- [ ] HTTPS включен (смотреть на зеленый замок)
- [ ] CORS настроен если требуется
- [ ] Rate limiting включен
- [ ] SQL инъекции защищены (SQLAlchemy ORM)
- [ ] CSRF защита включена
- [ ] Логирование ошибок включено
- [ ] Backup база данных
- [ ] Firewall настроен

## Заключение

Приложение готово к production развертыванию. Убедитесь что:

1. ✅ Все переменные окружения установлены
2. ✅ SSL сертификат работает
3. ✅ Яндекс OAuth настроен с правильным REDIRECT_URI
4. ✅ Логирование работает
5. ✅ Резервное копирование настроено
6. ✅ Мониторинг включен
7. ✅ Firewall правильно настроен

После развертывания протестируйте авторизацию на production сервере.
