#!/usr/bin/env python3
"""
Скрипт для добавления тестовых данных в БД
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.web import app, db
from src.dp import Comment, User, Like

with app.app_context():
    # Получаем тестового пользователя
    user = User.query.first()
    
    if not user:
        print("❌ Нет пользователя в БД")
        sys.exit(1)
    
    # Создаём несколько комментариев
    comments_text = [
        "Отлично! Система работает отлично 🚀",
        "Мне нравится новая функция лайков",
        "Ответы очень удобно скрывать и раскрывать"
    ]
    
    for i, text in enumerate(comments_text):
        # Проверяем нет ли уже такого комментария
        if not Comment.query.filter_by(text=text).first():
            comment = Comment(text=text, page="comments", user_id=user.id)
            db.session.add(comment)
    
    db.session.commit()
    
    # Получаем первый комментарий и добавляем ответ
    first_comment = Comment.query.filter_by(page="comments", parent_id=None).first()
    if first_comment:
        reply_text = "Спасибо! Я согласен 👍"
        if not Comment.query.filter_by(text=reply_text).first():
            reply = Comment(
                text=reply_text,
                page="comments",
                user_id=user.id,
                parent_id=first_comment.id
            )
            db.session.add(reply)
            db.session.commit()
            
            # Добавляем лайк к ответу
            if not Like.query.filter_by(comment_id=reply.id, user_id=user.id).first():
                like = Like(comment_id=reply.id, user_id=user.id)
                db.session.add(like)
                db.session.commit()
    
    # Получаем второй комментарий и добавляем лайки
    second_comment = Comment.query.filter_by(page="comments", parent_id=None).offset(1).first()
    if second_comment:
        if not Like.query.filter_by(comment_id=second_comment.id, user_id=user.id).first():
            like = Like(comment_id=second_comment.id, user_id=user.id)
            db.session.add(like)
            db.session.commit()
    
    print("✓ Тестовые данные успешно созданы:")
    print(f"  - Комментариев: {Comment.query.filter_by(parent_id=None).count()}")
    first = Comment.query.filter_by(page='comments', parent_id=None).first()
    if first:
        print(f"  - Ответов на первый: {Comment.query.filter_by(parent_id=first.id).count()}")
    print(f"  - Всего лайков: {Like.query.count()}")
