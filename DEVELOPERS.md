# Информация для разработчиков

## 🏗️ Архитектура приложения

### Структура проекта

```
web/
├── src/
│   ├── __init__.py          # Инициализация приложения
│   ├── web.py               # Основное Flask приложение (241 строк)
│   └── dp.py                # Модели БД (User, Comment)
├── templates/
│   ├── base.html            # Базовый шаблон
│   ├── index.html           # Главная страница с информацией
│   ├── comments.html        # Страница комментариев
│   ├── comments_section.html # Компонент комментариев
│   ├── social_login.html    # Страница авторизации
│   ├── login.html
│   ├── consent.html
│   └── 404.html, 500.html
├── static/
│   ├── css/
│   │   └── styles.css       # Основные стили
│   ├── images/
│   │   ├── github-logo.gif
│   │   ├── telegram.gif
│   │   ├── me.png
│   │   └── ...
│   └── favicon/
├── .env                     # Переменные окружения
├── .env.example             # Пример конфигурации
├── .gitignore               # Файлы для игнорирования Git
├── requirements.txt         # Зависимости Python
├── run.py                   # Точка входа приложения
├── site.db                  # SQLite БД
└── venv/                    # Виртуальное окружение

Documentation files:
├── README.md                # Основная документация
├── OAUTH_SETUP.md           # Руководство OAuth
├── DEPLOYMENT.md            # Развертывание
├── INTEGRATION_REPORT.md    # Отчет интеграции
├── QUICK_REFERENCE.md       # Краткая справка
└── CHANGELOG.md             # История изменений
```

## 🔍 Основные классы и функции

### Модели (src/dp.py)

#### Class User
```python
class User(db.Model):
    id: int                          # Primary key
    nickname: str                    # Имя пользователя
    avatar: str                      # URL аватара
    yandex_id: str (nullable)        # ID Яндекса
    vc_id: str (nullable)            # ID VK
    tg_id: str (nullable)            # ID Telegram
    email: str (nullable)            # Email
    created_at: datetime             # Время создания
    comments: relationship           # Связь с Comment
```

#### Class Comment
```python
class Comment(db.Model):
    id: int                          # Primary key
    text: str                        # Содержание
    created_at: datetime             # Время создания
    page: str                        # Страница (default: 'comments')
    user_id: int                     # FK на User
```

### Главные функции (src/web.py)

#### Авторизация
- `auth_yandex()` - инициирует OAuth поток
- `auth_yandex_callback()` - обрабатывает callback от Яндекса
- `logout()` - выход из системы

#### Комментарии
- `add_comment()` - добавляет новый комментарий
- `delete_comment(id)` - удаляет комментарий
- `get_comments(page)` - API получения комментариев

#### Страницы
- `index()` - главная страница
- `comments()` - страница комментариев
- `social_login()` - страница авторизации

#### Utilities
- `login_required()` - декоратор для защиты маршрутов
- `page_not_found(e)` - обработчик 404 ошибок
- `internal_server_error(e)` - обработчик 500 ошибок

## 🔐 OAuth поток в деталях

### 1. Инициация (`/auth/yandex`)

```python
@app.route('/auth/yandex')
def auth_yandex():
    params = {
        'response_type': 'code',
        'client_id': YANDEX_CLIENT_ID,
        'redirect_uri': YANDEX_REDIRECT_URI,
        'state': 'security_token'
    }
    return redirect(f"{YANDEX_OAUTH_AUTHORIZE_URL}?{urlencode(params)}")
```

**Flow:**
1. Генерируются параметры OAuth запроса
2. Пользователь перенаправляется на oauth.yandex.ru
3. Яндекс запрашивает разрешение доступа

### 2. Callback обработка (`/auth/yandex/callback`)

```python
@app.route('/auth/yandex/callback')
def auth_yandex_callback():
    # 1. Получить код авторизации
    code = request.args.get('code')
    
    # 2. Обменять код на access token
    token_response = requests.post(YANDEX_OAUTH_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': YANDEX_CLIENT_ID,
        'client_secret': YANDEX_CLIENT_SECRET
    })
    access_token = token_response.json().get('access_token')
    
    # 3. Получить информацию профиля
    user_response = requests.get(YANDEX_USER_INFO_URL, headers={
        'Authorization': f'OAuth {access_token}'
    })
    user_info = user_response.json()
    
    # 4. Создать/обновить пользователя
    user = User.query.filter_by(yandex_id=user_info.get('id')).first()
    if not user:
        user = User(
            nickname=user_info.get('display_name'),
            yandex_id=user_info.get('id'),
            email=user_info.get('default_email'),
            avatar=f"https://avatars.yandex.net/get-yapic/{user_info['default_avatar_id']}/islands-200"
        )
        db.session.add(user)
    else:
        user.nickname = user_info.get('display_name')
        user.email = user_info.get('default_email')
    db.session.commit()
    
    # 5. Установить сессию
    session['user_id'] = user.id
    session['user_nickname'] = user.nickname
    session['user_avatar'] = user.avatar
    
    return redirect(url_for('comments'))
```

## 🎨 Frontend структура

### Шаблоны (templates/)

#### base.html
- Наследуемый базовый шаблон
- Навигация сверху
- Блоки: navigation, auth_buttons, side_icons, content, scripts
- Стили подключены

#### index.html
- Главная страница
- Профильная карточка
- Раздел "Обо мне"
- Информация о проектах
- Список навыков
- JavaScript для анимации

#### comments.html
- Страница с комментариями
- Заголовок и описание
- Подключает компонент comments_section.html

#### comments_section.html
- Компонент для отображения комментариев
- Форма для добавления (если авторизован)
- Список комментариев с аватарами
- Кнопка удаления для своих комментариев
- CSS стили

#### social_login.html
- Кнопки авторизации (Яндекс, Telegram)
- Ссылка на политику конфиденциальности
- Информационный текст

### Стили (static/css/)

#### styles.css
- Темная тема (dark mode)
- Адаптивный дизайн
- Анимации
- Grid и Flexbox
- Custom scrollbars

## 🔄 Обработка ошибок

### Error handlers в Flask

```python
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
```

### Обработка OAuth ошибок

```python
try:
    # OAuth логика
except requests.RequestException as e:
    flash('Ошибка при авторизации через Яндекс', 'error')
    return redirect(url_for('social_login'))
```

### Валидация данных

```python
# Проверка пустого комментария
if not text:
    flash('Комментарий не может быть пустым', 'error')
    return redirect(url_for('comments'))

# Проверка прав удаления
if comment.user_id != session['user_id']:
    flash('Вы не можете удалить этот комментарий', 'error')
    return redirect(url_for('comments'))
```

## 🔧 Расширение функционала

### Добавление новой социальной сети

1. **Добавить поле в модель User:**
```python
# src/dp.py
google_id = db.Column(db.String(100), nullable=True)
```

2. **Создать маршруты авторизации:**
```python
# src/web.py
@app.route('/auth/google')
def auth_google():
    # OAuth логика
    pass

@app.route('/auth/google/callback')
def auth_google_callback():
    # Callback логика
    pass
```

3. **Добавить кнопку в шаблон:**
```html
<!-- templates/social_login.html -->
<a href="{{ url_for('auth_google') }}" class="social-btn google">
    <i class="fab fa-google"></i>
    Войти через Google
</a>
```

### Добавление новой модели

```python
# src/dp.py
class Like(db.Model):
    __tablename__ = 'like'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Добавление нового маршрута

```python
# src/web.py
@app.route('/new-feature', methods=['GET', 'POST'])
@login_required  # Если требуется авторизация
def new_feature():
    if request.method == 'POST':
        # Обработка POST запроса
        return redirect(url_for('index'))
    return render_template('new_feature.html')
```

## 📊 Переменные окружения

```env
# Основное
SECRET_KEY                      # Ключ для сессий

# Яндекс OAuth
YANDEX_CLIENT_ID               # Client ID от Яндекса
YANDEX_CLIENT_SECRET           # Client Secret от Яндекса
YANDEX_REDIRECT_URI            # Callback URL

# БД (опционально)
DATABASE_URL                   # Строка подключения БД
```

## 🧪 Тестирование

### Unit tests структура

```python
# tests/test_auth.py
import unittest
from src.web import app, db
from src.dp import User

class TestAuth(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def test_login_page(self):
        response = self.client.get('/social_login')
        self.assertEqual(response.status_code, 200)
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

if __name__ == '__main__':
    unittest.main()
```

### Запуск тестов

```bash
python -m pytest tests/
python -m unittest discover
```

## 📈 Мониторинг и логирование

### Логирование в production

```python
# src/web.py
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler(
        '/var/log/portfolio/flask.log',
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    app.logger.addHandler(file_handler)
```

### Просмотр логов

```bash
# Development
# Логи в консоль при запуске python3 run.py

# Production
tail -f /var/log/portfolio/flask.log
sudo journalctl -u portfolio -f
```

## 🚀 Оптимизация

### Оптимизация БД

```python
# Индексы для быстрого поиска
class Comment(db.Model):
    __table_args__ = (
        db.Index('idx_comment_page_created', 'page', 'created_at'),
        db.Index('idx_comment_user_id', 'user_id'),
    )
```

### Кэширование

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/comments/<page>')
@cache.cached(timeout=60)
def get_comments(page):
    # ...
```

### Оптимизация шаблонов

- Минификация CSS/JS
- Lazy loading изображений
- CDN для статических ресурсов

## 📝 Code standards

### Стиль кода

Следуем PEP 8:
```python
# ✅ Хорошо
user_name = "John Doe"
def get_user_comments(user_id):
    pass

# ❌ Плохо
userName = "John Doe"
def getusrcommnts(uid):
    pass
```

### Документирование

```python
def auth_yandex_callback():
    """
    Обработчик callback от Яндекс OAuth.
    
    Получает код авторизации, обменивает на access token,
    загружает информацию профиля и создает/обновляет пользователя.
    
    Returns:
        Редирект на /comments при успехе
        Редирект на /social_login при ошибке
    """
    pass
```

## 🐛 Debugging

### Flask debug mode

```bash
export FLASK_DEBUG=1
python3 run.py
```

### Использование debugger

```python
from flask import debugged

@app.route('/debug')
def debug_page():
    debugged()  # Точка останова
    return 'OK'
```

### Логирование в коде

```python
app.logger.info(f"User {user.id} logged in")
app.logger.error(f"Error: {e}")
app.logger.warning(f"Warning: {msg}")
```

## 📚 Полезные ссылки

- Flask документация: https://flask.palletsprojects.com/
- SQLAlchemy документация: https://docs.sqlalchemy.org/
- Яндекс OAuth API: https://yandex.ru/dev/oauth/
- Bootstrap документация: https://getbootstrap.com/
- Font Awesome иконки: https://fontawesome.com/

## 🎓 Для начинающих

1. Прочитайте README.md
2. Изучите структуру файлов
3. Запустите приложение локально
4. Пройдитесь по коду в src/web.py
5. Добавьте простую функцию (например, health check)
6. Напишите юнит тест
7. Сделайте Pull Request

---

**Версия:** 1.0.0
**Последнее обновление:** 20.12.2025
**Статус:** Production Ready ✅
