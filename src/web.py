from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os
import sys

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

# Инициализация БД
from .dp import db, User, Comment

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
    # Получаем комментарии для страницы
    comments_list = Comment.query.filter_by(page='comments').order_by(Comment.created_at.desc()).all()
    return render_template('comments.html', comments=comments_list)


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

    # Проверяем, что пользователь - владелец комментария
    if comment.user_id != session['user_id']:
        flash('Вы не можете удалить этот комментарий', 'error')
        return redirect(url_for('comments'))

    try:
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

    session['user_id'] = user.id
    session['user_nickname'] = user.nickname
    session['user_avatar'] = user.avatar

    flash('Вы успешно вошли через VK!', 'success')
    return redirect(url_for('comments'))


@app.route('/auth/yandex')
def auth_yandex():
    # Mock авторизация через Яндекс
    user = User.query.filter_by(yandex_id='demo_yandex_user').first()
    if not user:
        user = User(
            nickname='Yandex_User',
            yandex_id='demo_yandex_user',
            email='yandex_user@example.com',
            avatar='default-avatar.png'
        )
        db.session.add(user)
        db.session.commit()

    session['user_id'] = user.id
    session['user_nickname'] = user.nickname
    session['user_avatar'] = user.avatar

    flash('Вы успешно вошли через Яндекс!', 'success')
    return redirect(url_for('comments'))


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


# API для получения комментариев
@app.route('/api/comments/<page>')
def get_comments(page):
    comments = Comment.query.filter_by(page=page).order_by(Comment.created_at.desc()).all()
    comments_list = []

    for comment in comments:
        user = User.query.get(comment.user_id)
        comments_list.append({
            'id': comment.id,
            'text': comment.text,
            'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
            'author': user.nickname if user else 'Аноним',
            'avatar': user.avatar if user else 'default-avatar.png',
            'can_delete': 'user_id' in session and comment.user_id == session['user_id']
        })

    return jsonify(comments_list)


# Временная замена обработчиков ошибок
@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404 - Страница не найдена</h1><p><a href='/'>На главную</a></p>", 404


@app.errorhandler(500)
def internal_server_error(e):
    return "<h1>500 - Внутренняя ошибка сервера</h1><p>Попробуйте позже</p>", 500