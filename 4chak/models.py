from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    unique_username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_moderator = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.String(200), nullable=True)
    banned_until = db.Column(db.DateTime, nullable=True)
    menu_texts = db.Column(db.JSON, default=dict)

    bio = db.Column(db.Text, default='')
    language = db.Column(db.String(10), default='ru')
    timezone = db.Column(db.String(50), default='UTC')

    avatar_filename = db.Column(db.String(200), nullable=True)
    avatar_html = db.Column(db.Text, default='<div class="avatar">[Аватар]</div>')
    avatar_css = db.Column(db.Text, default='.avatar { color: #666; font-weight: bold; }')

    theme_html = db.Column(db.Text, default='')
    theme_css = db.Column(db.Text, default='')

    profile_html = db.Column(db.Text, default='<h1>Мой профиль</h1><p>Тут можно написать что-то.</p>')
    profile_css = db.Column(db.Text, default='body { background: #f0f0f0; }')

    two_factor_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def age(self):
        if self.date_of_birth:
            today = datetime.now(timezone.utc).date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

    def is_active(self):
        if self.is_banned:
            if self.banned_until and self.banned_until > datetime.now(timezone.utc):
                return False
            elif self.banned_until is None:
                return False
        return True

    def can_moderate(self, board):
        if self.is_admin:
            return True
        if self.is_moderator:
            return True
        return False

class TwoFactorCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    used = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='two_factor_codes')

class FailedAttempt(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    attempt_type = db.Column(db.String(20), default='code')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', foreign_keys=[user_id])

# ----- Остальные модели -----
class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_anonymous = db.Column(db.Boolean, default=False)
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    age_restriction = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    moderator = db.relationship('User', foreign_keys=[moderator_id])

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    age_restriction = db.Column(db.Integer, default=0)
    custom_html = db.Column(db.Text, nullable=True)
    custom_css = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    board = db.relationship('Board', backref='threads')
    user = db.relationship('User', backref='threads')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    edited_at = db.Column(db.DateTime, nullable=True)
    thread = db.relationship('Thread', backref='posts')
    user = db.relationship('User', backref='posts')
    media = db.relationship('Media', backref='post')

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200))
    file_path = db.Column(db.String(300), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref='media')

class PrivateThread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    creator = db.relationship('User', foreign_keys=[creator_id])

class PrivateThreadInvite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('private_thread.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    thread = db.relationship('PrivateThread', backref='invites')
    user = db.relationship('User', foreign_keys=[user_id])

class PrivateMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('private_thread.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    thread = db.relationship('PrivateThread', backref='messages')
    user = db.relationship('User', foreign_keys=[user_id])
    media = db.relationship('Media')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref='notifications')
