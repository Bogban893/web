from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nickname = db.Column(db.String(100), default='Mario', nullable=False)
    avatar = db.Column(db.String(200), default='default-avatar.png', nullable=False)
    vc_id = db.Column(db.String(100), nullable=True)
    tg_id = db.Column(db.String(100), nullable=True)
    yandex_id = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с комментариями
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')


class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    page = db.Column(db.String(50), default='comments')  # для определения страницы
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def init_db(app):
    """Инициализация базы данных"""
    with app.app_context():
        # Создаем все таблицы, если они не существуют
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

        print("[INFO] База данных инициализирована")