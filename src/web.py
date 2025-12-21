from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os
import sys
import requests
from urllib.parse import urlencode, urlparse
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем путь к директории проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(project_root, 'templates'),
    static_folder=os.path.join(project_root, 'static')
)

# Конфигурация
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(project_root, "site.db")}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Конфигурация Яндекс OAuth
YANDEX_CLIENT_ID = os.getenv('YANDEX_CLIENT_ID')
YANDEX_CLIENT_SECRET = os.getenv('YANDEX_CLIENT_SECRET')
YANDEX_REDIRECT_URI = os.getenv('YANDEX_REDIRECT_URI', 'http://localhost:5000/auth/yandex/callback')
YANDEX_OAUTH_AUTHORIZE_URL = 'https://oauth.yandex.com/authorize'
YANDEX_OAUTH_TOKEN_URL = 'https://oauth.yandex.com/token'
YANDEX_USER_INFO_URL = 'https://login.yandex.ru/info'

# Инициализация БД
from .dp import db, User, Comment, Like

db.init_app(app)

# Инициализация базы данных при запуске
with app.app_context():
    # Создаем все таблицы
    db.create_all()

    # Создаем тестового пользователя, если нет пользователей
    if User.query.count() == 0:
        print("[INFO] Создаем тестового пользователя...")
        test_user = User(
            nickname='TestUser',
            email='test@example.com',
            avatar='default-avatar.png'
        )
        db.session.add(test_user)
        db.session.commit()
        print("[INFO] Тестовый пользователь создан")


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Для выполнения этого действия необходимо войти в систему', 'warning')
            return redirect(url_for('social_login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')


@app.route('/comments')
def comments():
    # Получаем только основные комментарии (не ответы)
    comments_list = Comment.query.filter_by(page='comments', parent_id=None).order_by(Comment.created_at.desc()).all()
    return render_template('comments_page.html', comments=comments_list)


@app.route('/social_login')
def social_login():
    return render_template('social_login.html')


@app.route('/consent')
def consent():
    return render_template('consent.html')


@app.route('/login')
def login():
    return render_template('login.html')


# Маршрут для добавления комментария
@app.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    text = request.form.get('text', '').strip()
    page = request.form.get('page', 'comments')

    if not text:
        flash('Комментарий не может быть пустым', 'error')
        return redirect(url_for('comments'))

    # Создаем комментарий
    comment = Comment(
        text=text,
        page=page,
        user_id=session['user_id']
    )

    try:
        db.session.add(comment)
        db.session.commit()
        flash('Комментарий успешно добавлен!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при добавлении комментария', 'error')
        app.logger.error(f"Error adding comment: {e}")

    return redirect(url_for('comments'))


# Маршрут для удаления комментария
@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    # Проверяем, что пользователь - владелец комментария или находится в режиме админа
    is_admin_mode = request.form.get('admin_mode', 'false').lower() == 'true'
    
    if comment.user_id != session['user_id'] and not is_admin_mode:
        flash('Вы не можете удалить этот комментарий', 'error')
        return redirect(url_for('comments'))

    try:
        # Если это основной комментарий (у которого нет parent_id), удаляем и все его ответы
        if comment.parent_id is None:
            # Удаляем все ответы на этот комментарий
            replies = Comment.query.filter_by(parent_id=comment_id).all()
            for reply in replies:
                db.session.delete(reply)
        
        # Удаляем сам комментарий
        db.session.delete(comment)
        db.session.commit()
        flash('Комментарий удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении комментария', 'error')
        app.logger.error(f"Error deleting comment: {e}")

    return redirect(url_for('comments'))


# Mock endpoints для социальной авторизации
@app.route('/auth/vk')
def auth_vk():
    # Здесь будет реальная логика OAuth для VK
    user = User.query.filter_by(vc_id='demo_vk_user').first()
    if not user:
        user = User(
            nickname='VK_User_Demo',
            vc_id='demo_vk_user',
            email='vk_user@example.com',
            avatar='default-avatar.png'
        )
        db.session.add(user)
        db.session.commit()

@app.route('/auth/yandex')
def auth_yandex():
    """Перенаправляет на Яндекс для авторизации.

    Сохраняем в сессии целевой URL (если он безопасен), чтобы после
    успешной авторизации вернуться на предыдущую страницу.
    """
    # Определяем куда вернуться после авторизации: сначала параметр next,
    # затем Referer (если он с того же хоста).
    next_url = request.args.get('next')
    if not next_url:
        ref = request.referrer
        if ref:
            parsed = urlparse(ref)
            if parsed.netloc == request.host:
                next_url = parsed.path or '/'
                if parsed.query:
                    next_url += '?' + parsed.query

    # Сохраняем только относительные пути (без протокола/хоста)
    if next_url and isinstance(next_url, str) and next_url.startswith('/'):
        session['after_auth_redirect'] = next_url

    params = {
        'response_type': 'code',
        'client_id': YANDEX_CLIENT_ID,
        'redirect_uri': YANDEX_REDIRECT_URI,
        'state': 'security_token',
        'login_hint': ''
    }
    authorization_url = f"{YANDEX_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    return redirect(authorization_url)


@app.route('/auth/yandex/callback')
def auth_yandex_callback():
    """Обработчик callback от Яндекса"""
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        flash('Ошибка авторизации: код не получен', 'error')
        return redirect(url_for('social_login'))

    try:
        # Получаем токен доступа
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': YANDEX_CLIENT_ID,
            'client_secret': YANDEX_CLIENT_SECRET,
        }
        
        token_response = requests.post(YANDEX_OAUTH_TOKEN_URL, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        access_token = token_json.get('access_token')

        if not access_token:
            flash('Ошибка получения токена доступа', 'error')
            return redirect(url_for('social_login'))

        # Получаем информацию о пользователе
        headers = {
            'Authorization': f'OAuth {access_token}',
            'Content-Type': 'application/json'
        }
        
        user_response = requests.get(YANDEX_USER_INFO_URL, headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()

        yandex_id = user_info.get('id')
        nickname = user_info.get('display_name') or user_info.get('login', 'Yandex User')
        email = user_info.get('default_email', f'{yandex_id}@yandex.ru')
        
        # Получаем аватар
        avatar_url = None
        if 'default_avatar_id' in user_info:
            avatar_url = f"https://avatars.yandex.net/get-yapic/{user_info['default_avatar_id']}/islands-200"

        # Проверяем есть ли уже такой пользователь
        user = User.query.filter_by(yandex_id=yandex_id).first()
        
        if not user:
            # Создаем нового пользователя
            user = User(
                nickname=nickname,
                yandex_id=yandex_id,
                email=email,
                avatar=avatar_url or 'default-avatar.png'
            )
            db.session.add(user)
            db.session.commit()
            print(f"[INFO] Создан новый пользователь Яндекса: {nickname}")
        else:
            # Обновляем информацию пользователя
            user.nickname = nickname
            user.email = email
            if avatar_url:
                user.avatar = avatar_url
            db.session.commit()
            print(f"[INFO] Обновлены данные пользователя Яндекса: {nickname}")

        # Устанавливаем сессию
        session['user_id'] = user.id
        session['user_nickname'] = user.nickname
        session['user_avatar'] = user.avatar
        session['user_email'] = user.email

        flash(f'Вы успешно вошли как {nickname}!', 'success')

        # Попытаемся перенаправить пользователя на сохранённую страницу
        next_url = session.pop('after_auth_redirect', None)
        if next_url and isinstance(next_url, str) and next_url.startswith('/'):
            return redirect(next_url)

        # По умолчанию возвращаем на главную
        return redirect(url_for('index'))

    except requests.RequestException as e:
        print(f"[ERROR] Ошибка при авторизации через Яндекс: {e}")
        flash('Ошибка при авторизации через Яндекс', 'error')
        return redirect(url_for('social_login'))
        db.session.commit()

    session['user_id'] = user.id
    session['user_nickname'] = user.nickname
    session['user_avatar'] = user.avatar

    flash('Вы успешно вошли через Яндекс!', 'success')

    next_url = session.pop('after_auth_redirect', None)
    if next_url and isinstance(next_url, str) and next_url.startswith('/'):
        return redirect(next_url)

    return redirect(url_for('index'))


@app.route('/auth/telegram')
def auth_telegram():
    # Mock авторизация через Telegram
    user = User.query.filter_by(tg_id='demo_tg_user').first()
    if not user:
        user = User(
            nickname='Telegram_User',
            tg_id='demo_tg_user',
            email='tg_user@example.com',
            avatar='default-avatar.png'
        )
        db.session.add(user)
        db.session.commit()

    session['user_id'] = user.id
    session['user_nickname'] = user.nickname
    session['user_avatar'] = user.avatar

    flash('Вы успешно вошли через Telegram!', 'success')
    return redirect(url_for('comments'))


# Выход из системы
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))


# Переключение аккаунта: очищаем сессию и перенаправляем на страницу входа
@app.route('/switch_account')
def switch_account():
    session.clear()
    return redirect(url_for('social_login'))


# API для получения комментариев
@app.route('/api/comments/<page>')
def get_comments(page):
    comments = Comment.query.filter_by(page=page).order_by(Comment.created_at.desc()).all()
    comments_list = []

    for comment in comments:
        user = User.query.get(comment.user_id)
        # Считаем лайки и проверяем, лайкнул ли текущий пользователь
        likes_count = Like.query.filter_by(comment_id=comment.id).count()
        user_liked = False
        if 'user_id' in session:
            user_liked = Like.query.filter_by(comment_id=comment.id, user_id=session['user_id']).first() is not None

        comments_list.append({
            'id': comment.id,
            'text': comment.text,
            'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
            'author': user.nickname if user else 'Аноним',
            'avatar': user.avatar if user else 'default-avatar.png',
            'can_delete': 'user_id' in session and comment.user_id == session['user_id'],
            'likes_count': likes_count,
            'user_liked': user_liked
        })

    return jsonify(comments_list)


# Лайк на комментарий
@app.route('/api/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    user_id = session['user_id']
    # Запрещаем ставить лайки на ответы (комментарии с parent_id)
    if comment.parent_id is not None:
        return jsonify({
            'success': False,
            'error': 'Likes on replies are disabled'
        }), 403
    
    # Проверяем, уже ли пользователь лайкнул этот комментарий
    existing_like = Like.query.filter_by(comment_id=comment_id, user_id=user_id).first()
    
    if existing_like:
        # Удаляем лайк (дизлайк)
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        # Добавляем лайк
        like = Like(comment_id=comment_id, user_id=user_id)
        db.session.add(like)
        db.session.commit()
        liked = True
    
    # Возвращаем количество лайков
    likes_count = Like.query.filter_by(comment_id=comment_id).count()
    
    return jsonify({
        'success': True,
        'liked': liked,
        'likes_count': likes_count
    })


# Добавление ответа на комментарий
@app.route('/add_reply/<int:parent_id>', methods=['POST'])
@login_required
def add_reply(parent_id):
    parent_comment = Comment.query.get_or_404(parent_id)
    text = request.form.get('text', '').strip()
    page = request.form.get('page', 'comments')
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'Ответ не может быть пустым'
        }), 400
    
    # Создаем ответ
    reply = Comment(
        text=text,
        page=page,
        user_id=session['user_id'],
        parent_id=parent_id
    )
    
    try:
        db.session.add(reply)
        db.session.commit()
        
        # Возвращаем JSON с данными ответа
        user = User.query.get(reply.user_id)
        return jsonify({
            'success': True,
            'reply': {
                'id': reply.id,
                'text': reply.text,
                'created_at': reply.created_at.strftime('%d.%m.%Y %H:%M'),
                'author': user.nickname if user else 'Аноним',
                'avatar': user.avatar if user else 'default-avatar.png',
                'can_delete': True,
                'likes_count': 0,
                'user_liked': False
            },
            'message': 'Ответ успешно добавлен!'
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding reply: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка при добавлении ответа'
        }), 500


# API для получения ответов на комментарий
@app.route('/api/comment/<int:comment_id>/replies')
def get_comment_replies(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    replies = Comment.query.filter_by(parent_id=comment_id).order_by(Comment.created_at.asc()).all()
    
    replies_list = []
    for reply in replies:
        user = User.query.get(reply.user_id)
        likes_count = Like.query.filter_by(comment_id=reply.id).count()
        user_liked = False
        if 'user_id' in session:
            user_liked = Like.query.filter_by(comment_id=reply.id, user_id=session['user_id']).first() is not None
        
        replies_list.append({
            'id': reply.id,
            'text': reply.text,
            'created_at': reply.created_at.strftime('%d.%m.%Y %H:%M'),
            'author': user.nickname if user else 'Аноним',
            'avatar': user.avatar if user else 'default-avatar.png',
            'can_delete': 'user_id' in session and reply.user_id == session['user_id'],
            'likes_count': likes_count,
            'user_liked': user_liked
        })
    
    return jsonify(replies_list)


# Временная замена обработчиков ошибок
# Контекст процессор для передачи функций в шаблоны
@app.context_processor
def inject_user():
    def get_user(user_id):
        if user_id:
            return User.query.get(user_id)
        return None
    return dict(get_user=get_user)

@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404 - Страница не найдена</h1><p><a href='/'>На главную</a></p>", 404


@app.errorhandler(500)
def internal_server_error(e):
    return "<h1>500 - Внутренняя ошибка сервера</h1><p>Попробуйте позже</p>", 500