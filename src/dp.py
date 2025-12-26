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
    google_id = db.Column(db.String(100), nullable=True)
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
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)  # для ответов
    
    # Отношения
    likes = db.relationship('Like', backref='comment', lazy=True, cascade='all, delete-orphan')
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)


class Like(db.Model):
    __tablename__ = 'like'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Уникальность: один пользователь может лайкнуть комментарий только один раз
    __table_args__ = (db.UniqueConstraint('comment_id', 'user_id', name='unique_like'),)


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