from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, TextAreaField, BooleanField, FileField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, ValidationError
import re
import zoneinfo

ALL_TIMEZONES = [(tz, tz) for tz in sorted(zoneinfo.available_timezones())]

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    display_name = StringField('Отображаемое имя', validators=[DataRequired(), Length(min=3, max=80)])
    unique_username = StringField('Уникальное имя (только латиница, цифры, _)', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    date_of_birth = DateField('Дата рождения', format='%Y-%m-%d', validators=[DataRequired()])

    def validate_unique_username(self, field):
        if not re.match(r'^[a-zA-Z0-9_]+$', field.data):
            raise ValidationError('Только латинские буквы, цифры и подчёркивание')
        from models import User
        if User.query.filter_by(unique_username=field.data).first():
            raise ValidationError('Это уникальное имя уже занято')

class LoginForm(FlaskForm):
    login = StringField('Email или уникальное имя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])

class TwoFactorForm(FlaskForm):
    code = StringField('Код из письма', validators=[DataRequired(), Length(min=6, max=6)])

class EditProfileForm(FlaskForm):
    display_name = StringField('Отображаемое имя', validators=[DataRequired(), Length(min=3, max=80)])
    bio = TextAreaField('О себе')
    language = SelectField('Язык', choices=[('ru','Русский'),('en','English')], default='ru')
    timezone = SelectField('Часовой пояс', choices=[('UTC','UTC'),('Europe/Moscow','Москва')], default='UTC')
    profile_html = TextAreaField('HTML профиля')
    profile_css = TextAreaField('CSS профиля')

class ThemeSettingsForm(FlaskForm):
    theme_html = TextAreaField('HTML для личной темы (вставляется в <head>)')
    theme_css = TextAreaField('CSS для личной темы')

    # Настройки текста меню
    menu_index = StringField('Главная', default='Главная')
    menu_boards = StringField('Доски', default='Доски')
    menu_anon_board = StringField('Анонимный раздел', default='Анонимный раздел')
    menu_profile = StringField('Профиль (имя пользователя)', default='')  # пустое означает отображать имя пользователя
    menu_settings_profile = StringField('Настройки профиля', default='Профиль')
    menu_settings_avatar = StringField('Аватар', default='Аватар')
    menu_settings_theme = StringField('Тема', default='Тема')
    menu_private_threads = StringField('Приватные', default='Приватные')
    menu_notifications = StringField('Уведомления', default='Уведомления')
    menu_logout = StringField('Выйти', default='Выйти')
    menu_login = StringField('Вход', default='Вход')
    menu_register = StringField('Регистрация', default='Регистрация')
    menu_admin = StringField('Админка', default='Админка')

class AvatarSettingsForm(FlaskForm):
    avatar_file = FileField('Файл аватара', validators=[Optional()])
    avatar_html = TextAreaField('HTML для левого блока (если нет файла)')
    avatar_css = TextAreaField('CSS для левого блока')

class NewThreadForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Сообщение', validators=[DataRequired()])
    media = FileField('Медиафайл (опционально)', validators=[Optional()])
    age_restriction = SelectField('Возрастное ограничение треда', choices=[(0,'Без ограничений'),(12,'12+'),(14,'14+'),(16,'16+'),(18,'18+')], coerce=int, default=0)
    custom_html = TextAreaField('Кастомный HTML для треда (опционально)')
    custom_css = TextAreaField('Кастомный CSS для треда (опционально)')

class ReplyForm(FlaskForm):
    content = TextAreaField('Сообщение', validators=[DataRequired()])
    media = FileField('Медиафайл (опционально)', validators=[Optional()])

class EditPostForm(FlaskForm):
    content = TextAreaField('Сообщение', validators=[DataRequired()])

class BoardForm(FlaskForm):
    name = StringField('Название доски', validators=[DataRequired(), Length(max=50)])
    description = StringField('Описание', validators=[Length(max=200)])
    is_anonymous = BooleanField('Анонимный раздел')
    moderator_id = SelectField('Модератор (ID)', coerce=int, validators=[Optional()])
    age_restriction = SelectField('Возрастное ограничение', choices=[(0,'Без ограничений'),(12,'12+'),(14,'14+'),(16,'16+'),(18,'18+')], coerce=int, default=0)

class UserEditForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    display_name = StringField('Отображаемое имя', validators=[DataRequired(), Length(min=3, max=80)])
    unique_username = StringField('Уникальное имя', validators=[DataRequired(), Length(min=3, max=80)])
    date_of_birth = DateField('Дата рождения', format='%Y-%m-%d', validators=[DataRequired()])
    is_admin = BooleanField('Администратор')
    is_moderator = BooleanField('Модератор')
    is_banned = BooleanField('Забанен')
    ban_reason = StringField('Причина бана')
    banned_until = StringField('Бан до (YYYY-MM-DD HH:MM:SS)')

class NewPrivateThreadForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(max=200)])
    invited_users = StringField('Пригласить пользователей (уникальные имена через запятую)')
    content = TextAreaField('Сообщение', validators=[DataRequired()])
    media = FileField('Медиафайл (опционально)', validators=[Optional()])

class PrivateReplyForm(FlaskForm):
    content = TextAreaField('Сообщение', validators=[DataRequired()])
    media = FileField('Медиафайл (опционально)', validators=[Optional()])


