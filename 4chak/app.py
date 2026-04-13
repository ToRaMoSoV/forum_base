import os
import random
import string
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, abort, send_from_directory, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message

from utils import sanitize_html, sanitize_css
    
import json
import time
from flask import stream_with_context, Response
from admin import admin_required
from utils import (allowed_file, sanitize_profile_html, sanitize_post_content,
                   sanitize_css, check_age_restriction, clear_anonymous_board,
                   generate_unique_username)
from forms import (RegistrationForm, LoginForm, TwoFactorForm, EditProfileForm, ThemeSettingsForm,
                   NewThreadForm, ReplyForm, EditPostForm, NewPrivateThreadForm,
                   PrivateReplyForm, AvatarSettingsForm, BoardForm, UserEditForm)

from models import (db, User, Board, Thread, Post, Media, TwoFactorCode, FailedAttempt,
                    PrivateThread, PrivateThreadInvite, PrivateMessage, Notification)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'SUDA_KEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

# Настройки почты (для теста лучше использовать localhost:1025)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = '' 
app.config['MAIL_DEFAULT_SENDER'] = ''
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  #для постоянных сессий

mail = Mail(app)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

scheduler = BackgroundScheduler()
scheduler.add_job(func=clear_anonymous_board, trigger="interval", hours=24)
scheduler.start()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ---------- Вспомогательные функции ----------
def save_uploaded_file(file, user_id=None):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_name = f"{datetime.now(timezone.utc).timestamp()}_{name}{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(file_path)
        media = Media(
            filename=unique_name,
            original_name=filename,
            file_path=unique_name,
            user_id=user_id
        )
        db.session.add(media)
        db.session.commit()
        return media
    return None

def check_ban():
    if current_user.is_authenticated and current_user.is_banned:
        if current_user.banned_until and current_user.banned_until > datetime.now(timezone.utc):
            flash(f'Вы забанены до {current_user.banned_until}. Причина: {current_user.ban_reason}', 'danger')
            return True
        elif current_user.banned_until is None:
            flash(f'Вы забанены навсегда. Причина: {current_user.ban_reason}', 'danger')
            return True
    return False

def generate_6_digit_code():
    return ''.join(random.choices(string.digits, k=6))

def get_client_ip():
    """Получение IP клиента"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr
    return ip

def is_ip_blocked(ip):
    """Проверка, заблокирован ли IP (более 3 неудачных попыток за последние 24 часа)"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    attempts = FailedAttempt.query.filter(
        FailedAttempt.ip_address == ip,
        FailedAttempt.created_at >= cutoff
    ).count()
    return attempts >= 3

def record_failed_attempt(ip, attempt_type, user_id=None):
    """Записывает неудачную попытку (код или повторная отправка)"""
    attempt = FailedAttempt(
        ip_address=ip,
        attempt_type=attempt_type,
        user_id=user_id
    )
    db.session.add(attempt)
    db.session.commit()

def send_2fa_code(user):
    """Генерирует и отправляет код двухфакторной аутентификации на email пользователя"""
    code = generate_6_digit_code()
    # Удаляем старые неиспользованные коды для этого пользователя
    TwoFactorCode.query.filter_by(user_id=user.id, used=False).delete()
    two_factor = TwoFactorCode(user_id=user.id, code=code)
    db.session.add(two_factor)
    db.session.commit()

    subject = "Код двухфакторной аутентификации"
    body = f"""Здравствуйте, {user.display_name}!

Ваш код для входа на форум: {code}

Код действителен в течение 15 минут.

Если вы не пытались войти, проигнорируйте это письмо."""
    msg = Message(subject, recipients=[user.email])
    msg.body = body
    try:
        mail.send(msg)
    except Exception as e:
        # Если отправка не удалась, выводим код в консоль для отладки
        print(f"Не удалось отправить email: {e}")
        print(f"Код для {user.display_name}: {code}")

from zoneinfo import ZoneInfo

def format_datetime(dt, tz_name='UTC'):
    """Преобразует UTC-время в локальное время пользователя"""
    if dt is None:
        return ''
    user_tz = ZoneInfo(tz_name)
    dt_utc = dt.replace(tzinfo=ZoneInfo('UTC'))
    local_dt = dt_utc.astimezone(user_tz)
    return local_dt.strftime('%Y-%m-%d %H:%M')

app.jinja_env.filters['datetime'] = format_datetime


# ---------- Роуты ----------
@app.route('/')
def index():
    boards = Board.query.filter_by(is_anonymous=False).all()
    anon_board = Board.query.filter_by(is_anonymous=True).first()
    return render_template('index.html', boards=boards, anon_board=anon_board)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(unique_username=form.unique_username.data).first():
            flash('Уникальное имя уже занято', 'danger')
            return redirect(url_for('register'))
        user = User(
            email=form.email.data,
            display_name=form.display_name.data,
            unique_username=form.unique_username.data,
            password_hash=generate_password_hash(form.password.data),
            date_of_birth=form.date_of_birth.data,
            two_factor_enabled=True
        )
        db.session.add(user)
        db.session.commit()
        # Сохраняем ID пользователя в сессии для 2FA
        session['2fa_user_id'] = user.id
        # Генерируем и отправляем код
        send_2fa_code(user)
        flash(f'Код отправлен на {user.email}. Введите его ниже.', 'info')
        return redirect(url_for('two_factor'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.login.data
        password = form.password.data
        user = User.query.filter((User.email == login_input) | (User.unique_username == login_input)).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active():
                flash('Ваш аккаунт забанен', 'danger')
                return redirect(url_for('login'))
            if user.two_factor_enabled:
                # Сохраняем ID пользователя в сессии, запрашиваем код
                session['2fa_user_id'] = user.id
                # Генерируем и отправляем код
                send_2fa_code(user)
                flash(f'Код отправлен на {user.email}. Введите его ниже.', 'info')
                return redirect(url_for('two_factor'))
            else:
                login_user(user)
                return redirect(url_for('index'))
        flash('Неверные данные', 'danger')
    return render_template('login.html', form=form)

@app.route('/two_factor', methods=['GET', 'POST'])
def two_factor():
    if '2fa_user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['2fa_user_id'])
    if not user:
        session.pop('2fa_user_id', None)
        return redirect(url_for('login'))

    ip = get_client_ip()
    if is_ip_blocked(ip):
        flash('Слишком много неудачных попыток. Попробуйте через 24 часа.', 'danger')
        return redirect(url_for('index'))

    form = TwoFactorForm()
    if form.validate_on_submit():
        code = form.code.data
        two_factor = TwoFactorCode.query.filter_by(user_id=user.id, code=code, used=False).first()
        if two_factor and (datetime.now(timezone.utc) - two_factor.created_at.replace(tzinfo=timezone.utc)).total_seconds() < 900:
            two_factor.used = True
            db.session.commit()
            login_user(user)
            session.pop('2fa_user_id', None)
            flash('Успешный вход!', 'success')
            return redirect(url_for('index'))
        else:
            record_failed_attempt(ip, 'code', user.id)
            flash('Неверный или просроченный код', 'danger')
            if is_ip_blocked(ip):
                flash('Слишком много неудачных попыток. Доступ заблокирован на 24 часа.', 'danger')
                return redirect(url_for('index'))
    return render_template('two_factor.html', form=form, email=user.email)

@app.route('/resend_code', methods=['POST'])
def resend_code():
    if '2fa_user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    user = db.session.get(User, session['2fa_user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    ip = get_client_ip()
    if is_ip_blocked(ip):
        return jsonify({'error': 'IP blocked'}), 429

    # Проверка таймера 60 секунд
    last_resend = FailedAttempt.query.filter(
        FailedAttempt.ip_address == ip,
        FailedAttempt.attempt_type == 'resend',
        FailedAttempt.created_at > datetime.now(timezone.utc) - timedelta(seconds=60)
    ).first()
    if last_resend:
        return jsonify({'error': 'Wait 60 seconds'}), 429

    send_2fa_code(user)
    record_failed_attempt(ip, 'resend', user.id)
    return jsonify({'success': True, 'message': 'Code resent'}), 200

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    return render_template('profile.html', user=user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.profile_html = sanitize_profile_html(form.profile_html.data)
        current_user.profile_css = sanitize_css(form.profile_css.data)
        db.session.commit()
        flash('Профиль обновлён', 'success')
        return redirect(url_for('profile', user_id=current_user.id))
    form.profile_html.data = current_user.profile_html
    form.profile_css.data = current_user.profile_css
    return render_template('edit_profile.html', form=form)



@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data
        current_user.bio = form.bio.data
        current_user.language = form.language.data
        current_user.timezone = form.timezone.data
        current_user.profile_html = sanitize_profile_html(form.profile_html.data)
        current_user.profile_css = sanitize_css(form.profile_css.data)
        db.session.commit()
        flash('Настройки профиля обновлены', 'success')
        return redirect(url_for('profile', user_id=current_user.id))
    form.display_name.data = current_user.display_name
    form.bio.data = current_user.bio
    form.language.data = current_user.language
    form.timezone.data = current_user.timezone
    form.profile_html.data = current_user.profile_html
    form.profile_css.data = current_user.profile_css
    return render_template('settings_profile.html', form=form)

@app.route('/settings/avatar', methods=['GET', 'POST'])
@login_required
def settings_avatar():
    form = AvatarSettingsForm()
    if form.validate_on_submit():
        if form.avatar_file.data:
            file = form.avatar_file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                name, ext = os.path.splitext(filename)
                unique_name = f"{datetime.now(timezone.utc).timestamp()}_{name}{ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(file_path)
                if current_user.avatar_filename:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                current_user.avatar_filename = unique_name
        current_user.avatar_html = sanitize_profile_html(form.avatar_html.data)
        current_user.avatar_css = sanitize_css(form.avatar_css.data)
        db.session.commit()
        flash('Настройки аватарки обновлены', 'success')
        return redirect(url_for('settings_avatar'))
    form.avatar_html.data = current_user.avatar_html
    form.avatar_css.data = current_user.avatar_css
    return render_template('settings_avatar.html', form=form)

@app.route('/avatar/<int:user_id>')
def avatar(user_id):
    user = db.session.get(User, user_id)
    if not user or not user.avatar_filename:
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], user.avatar_filename)

@app.route('/bootstrap-demo')
@login_required
@admin_required   # только для админов, чтобы обычные пользователи не видели
def bootstrap_demo():
    return render_template('bootstrap_demo.html')

@app.route('/settings/theme', methods=['GET', 'POST'])
@login_required
def settings_theme():
    form = ThemeSettingsForm()
    if request.method == 'POST':
        action = request.form.get('action')
        html = request.form.get('theme_html', '')
        css = request.form.get('theme_css', '')

        # Сохраняем кастомные тексты меню
        menu_dict = {}
        menu_fields = ['menu_index', 'menu_boards', 'menu_anon_board', 'menu_profile',
                       'menu_settings_profile', 'menu_settings_avatar', 'menu_settings_theme',
                       'menu_private_threads', 'menu_notifications', 'menu_logout',
                       'menu_login', 'menu_register', 'menu_admin']
        for f in menu_fields:
            val = request.form.get(f, '').strip()
            if val:
                menu_dict[f.replace('menu_', '')] = val
        current_user.menu_texts = menu_dict
        db.session.commit()

        # Далее сохранение темы (как было)
        if action == 'permanent':
            current_user.theme_html = sanitize_profile_html(html)
            current_user.theme_css = sanitize_css(css)
            db.session.commit()
            session.pop('temp_theme', None)
            flash('Личная тема обновлена', 'success')
        elif action == 'temporary':
            session['temp_theme'] = {
                'html': html,
                'css': css,
                'expires': datetime.now(timezone.utc) + timedelta(minutes=2)
            }
            return '', 200
        elif action is None:
            # Старый способ (без окна) – для совместимости
            current_user.theme_html = sanitize_profile_html(html)
            current_user.theme_css = sanitize_css(css)
            db.session.commit()
            flash('Личная тема обновлена', 'success')
            return redirect(url_for('settings_theme'))
        return redirect(url_for('settings_theme'))
    else:
        # GET – заполняем форму
        temp = session.get('temp_theme')
        if temp:
            form.theme_html.data = temp['html']
            form.theme_css.data = temp['css']
        else:
            form.theme_html.data = current_user.theme_html
            form.theme_css.data = current_user.theme_css

        # Заполняем поля меню из current_user.menu_texts
        for f in form:
            if f.name.startswith('menu_'):
                key = f.name.replace('menu_', '')
                f.data = current_user.menu_texts.get(key, f.default)

        return render_template('settings_theme.html', form=form)
        
        
@app.route('/boards')
def boards():
    boards = Board.query.filter_by(is_anonymous=False).all()
    return render_template('boards.html', boards=boards)

@app.route('/board/<int:board_id>')
def board(board_id):
    board = db.session.get(Board, board_id)
    if not board:
        abort(404)
    if board.is_anonymous:
        return redirect(url_for('anon_board'))
    user_age = current_user.age if current_user.is_authenticated else None
    if not check_age_restriction(user_age, board.age_restriction):
        flash('Эта доска имеет возрастное ограничение. Вы не соответствуете.', 'danger')
        return redirect(url_for('index'))
    threads = Thread.query.filter_by(board_id=board.id).order_by(Thread.is_pinned.desc(), Thread.created_at.desc()).all()
    if current_user.is_authenticated:
        threads = [t for t in threads if check_age_restriction(user_age, t.age_restriction)]
    else:
        threads = [t for t in threads if t.age_restriction == 0]
    return render_template('board.html', board=board, threads=threads)

@app.route('/board/<int:board_id>/new', methods=['GET', 'POST'])
@login_required
def new_thread(board_id):

    if check_ban():
        return redirect(url_for('index'))

    board = db.session.get(Board, board_id)

    if not board or board.is_anonymous:
        abort(403)

    form = NewThreadForm()

    if form.validate_on_submit():

        # HTML
        html = form.custom_html.data
        if html and len(html) > 5000:
            abort(400, "HTML too long")

        custom_html = sanitize_html(html)

        # CSS
        css = form.custom_css.data
        if css and len(css) > 2000:
            abort(400, "CSS too long")

        custom_css = sanitize_css(css)

        # создание треда
        thread = Thread(
            title=form.title.data,
            board_id=board.id,
            user_id=current_user.id,
            age_restriction=form.age_restriction.data,
            custom_html=custom_html,
            custom_css=custom_css
        )

        db.session.add(thread)
        db.session.commit()

        media = None
        if form.media.data:
            media = save_uploaded_file(form.media.data, current_user.id)

        post = Post(
            content=sanitize_post_content(form.content.data),
            thread_id=thread.id,
            user_id=current_user.id,
            media_id=media.id if media else None
        )

        db.session.add(post)
        db.session.commit()

        return redirect(url_for('thread', thread_id=thread.id))

    return render_template('new_thread.html', form=form, board=board)
    
@app.route('/thread/<int:thread_id>')
def thread(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    board = db.session.get(Board, thread.board_id)
    if board.is_anonymous:
        return redirect(url_for('anon_thread', thread_id=thread.id))
    user_age = current_user.age if current_user.is_authenticated else None
    if not check_age_restriction(user_age, board.age_restriction) or not check_age_restriction(user_age, thread.age_restriction):
        flash('Этот тред имеет возрастное ограничение.', 'danger')
        return redirect(url_for('board', board_id=board.id))
    posts = Post.query.filter_by(thread_id=thread.id).order_by(Post.created_at).all()
    form = ReplyForm()
    return render_template('thread.html', thread=thread, board=board, posts=posts, form=form)

@app.route('/thread/<int:thread_id>/reply', methods=['POST'])
@login_required
def reply(thread_id):
    if check_ban():
        return redirect(url_for('index'))
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    board = db.session.get(Board, thread.board_id)
    if board.is_anonymous:
        abort(403)
    if thread.is_locked:
        flash('Тред закрыт для ответов')
        return redirect(url_for('thread', thread_id=thread.id))
    form = ReplyForm()
    if form.validate_on_submit():
        media = None
        if form.media.data:
            media = save_uploaded_file(form.media.data, current_user.id)
        post = Post(
            content=sanitize_post_content(form.content.data),
            thread_id=thread.id,
            user_id=current_user.id,
            media_id=media.id if media else None
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('thread', thread_id=thread.id))
    flash('Ошибка при отправке')
    return redirect(url_for('thread', thread_id=thread.id))

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    thread = db.session.get(Thread, post.thread_id)
    board = db.session.get(Board, thread.board_id)
    if not (post.user_id == current_user.id or current_user.can_moderate(board)):
        abort(403)
    form = EditPostForm()
    if form.validate_on_submit():
        post.content = sanitize_post_content(form.content.data)
        post.edited_at = datetime.now(timezone.utc)
        db.session.commit()
        flash('Пост отредактирован')
        return redirect(url_for('thread', thread_id=thread.id))
    form.content.data = post.content
    return render_template('edit_post.html', form=form, post=post)

@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    thread = db.session.get(Thread, post.thread_id)
    board = db.session.get(Board, thread.board_id)
    if not current_user.can_moderate(board):
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Пост удалён')
    return redirect(url_for('thread', thread_id=thread.id))

@app.route('/stream/<int:thread_id>')
def stream_posts(thread_id):
    """Server‑Sent Events: отправляет новые посты в тред"""
    def generate():
        # Получаем последний ID, который есть у клиента
        last_id = request.args.get('last_id', 0, type=int)
        while True:
            # Ищем посты новее last_id
            new_posts = Post.query.filter(
                Post.thread_id == thread_id,
                Post.id > last_id
            ).order_by(Post.id).all()
            for post in new_posts:
                # Формируем данные для отправки
                data = {
                    'id': post.id,
                    'content': post.content,
                    'user': post.user.display_name if post.user else 'Аноним',
                    'created_at': post.created_at.isoformat(),
                    'user_id': post.user_id
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                last_id = post.id
            # Если нет новых – ждём 2 секунды
            time.sleep(2)

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/delete_thread/<int:thread_id>')
@login_required
def delete_thread(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    board = db.session.get(Board, thread.board_id)
    if not current_user.can_moderate(board):
        abort(403)
    db.session.delete(thread)
    db.session.commit()
    flash('Тред удалён')
    return redirect(url_for('board', board_id=board.id))

@app.route('/lock_thread/<int:thread_id>')
@login_required
def lock_thread(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    board = db.session.get(Board, thread.board_id)
    if not current_user.can_moderate(board):
        abort(403)
    thread.is_locked = not thread.is_locked
    db.session.commit()
    flash('Статус треда изменён')
    return redirect(url_for('thread', thread_id=thread.id))

@app.route('/pin_thread/<int:thread_id>')
@login_required
def pin_thread(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    board = db.session.get(Board, thread.board_id)
    if not current_user.can_moderate(board):
        abort(403)
    thread.is_pinned = not thread.is_pinned
    db.session.commit()
    flash('Статус треда изменён')
    return redirect(url_for('board', board_id=board.id))

# ---------- Анонимный раздел ----------
@app.route('/anon')
def anon_board():
    anon_board_obj = Board.query.filter_by(is_anonymous=True).first()
    if not anon_board_obj:
        anon_board_obj = Board(name="Анонимный раздел", description="Очищается каждые 24 часа", is_anonymous=True)
        db.session.add(anon_board_obj)
        db.session.commit()
    threads = Thread.query.filter_by(board_id=anon_board_obj.id).order_by(Thread.created_at.desc()).all()
    return render_template('anon_board.html', board=anon_board_obj, threads=threads)

@app.route('/anon/new', methods=['GET', 'POST'])
def anon_new_thread():
    anon_board_obj = Board.query.filter_by(is_anonymous=True).first()
    if not anon_board_obj:
        anon_board_obj = Board(name="Анонимный раздел", description="Очищается каждые 24 часа", is_anonymous=True)
        db.session.add(anon_board_obj)
        db.session.commit()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        if not title or not content:
            flash('Заполните заголовок и сообщение')
            return redirect(url_for('anon_new_thread'))
        thread = Thread(title=title, board_id=anon_board_obj.id, user_id=None)
        db.session.add(thread)
        db.session.commit()
        media = None
        if 'media' in request.files:
            file = request.files['media']
            if file and file.filename:
                media = save_uploaded_file(file, None)
        post = Post(
            content=sanitize_post_content(content),
            thread_id=thread.id,
            user_id=None,
            media_id=media.id if media else None
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('anon_thread', thread_id=thread.id))
    return render_template('new_thread_anon.html', board=anon_board_obj)

@app.route('/anon/thread/<int:thread_id>')
def anon_thread(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    board = db.session.get(Board, thread.board_id)
    if not board.is_anonymous:
        abort(404)
    posts = Post.query.filter_by(thread_id=thread.id).order_by(Post.created_at).all()
    return render_template('thread_anon.html', thread=thread, board=board, posts=posts)

@app.route('/anon/thread/<int:thread_id>/reply', methods=['POST'])
def anon_reply(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    board = db.session.get(Board, thread.board_id)
    if not board.is_anonymous:
        abort(403)
    content = request.form.get('content', '').strip()
    if not content:
        flash('Сообщение не может быть пустым')
        return redirect(url_for('anon_thread', thread_id=thread.id))
    media = None
    if 'media' in request.files:
        file = request.files['media']
        if file and file.filename:
            media = save_uploaded_file(file, None)
    post = Post(
        content=sanitize_post_content(content),
        thread_id=thread.id,
        user_id=None,
        media_id=media.id if media else None
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('anon_thread', thread_id=thread.id))
    
# app.py

@app.route('/api/thread/<int:thread_id>/updates')
def thread_updates(thread_id):
    after = request.args.get('after', type=int, default=0)  # timestamp или id
    # Получаем посты, созданные после указанного времени
    thread = Thread.query.get_or_404(thread_id)
    # Если after – это id последнего сообщения на клиенте
    posts = Post.query.filter(Post.thread_id == thread_id, Post.id > after).order_by(Post.created_at).all()
    # Формируем JSON с HTML-кодом каждого поста
    data = []
    for post in posts:
        html = render_template('_post.html', post=post, board=thread.board, thread=thread)
        data.append({'id': post.id, 'html': html})
    return jsonify(data)


@app.after_request
def security_headers(response):

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self';"
    )

    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response

# ---------- Приватные треды ----------
@app.route('/private')
@login_required
def private_threads():
    threads = PrivateThread.query.filter(
        (PrivateThread.creator_id == current_user.id) |
        (PrivateThreadInvite.query.filter_by(user_id=current_user.id, status='accepted').join(PrivateThreadInvite.thread).exists())
    ).all()
    return render_template('private_threads.html', threads=threads)

@app.route('/private/new', methods=['GET', 'POST'])
@login_required
def new_private_thread():
    form = NewPrivateThreadForm()
    if form.validate_on_submit():
        thread = PrivateThread(title=form.title.data, creator_id=current_user.id)
        db.session.add(thread)
        db.session.commit()

        invited_names = [name.strip() for name in form.invited_users.data.split(',') if name.strip()]
        for name in invited_names:
            user = User.query.filter_by(unique_username=name).first()
            if user and user.id != current_user.id:
                invite = PrivateThreadInvite(thread_id=thread.id, user_id=user.id, status='pending')
                db.session.add(invite)
                notif = Notification(
                    user_id=user.id,
                    content=f'Вас пригласили в приватный тред "{thread.title}"',
                    link=url_for('view_private_thread', thread_id=thread.id)
                )
                db.session.add(notif)

        invite_self = PrivateThreadInvite(thread_id=thread.id, user_id=current_user.id, status='accepted')
        db.session.add(invite_self)

        media = None
        if form.media.data:
            media = save_uploaded_file(form.media.data, current_user.id)
        msg = PrivateMessage(
            thread_id=thread.id,
            user_id=current_user.id,
            content=sanitize_post_content(form.content.data),
            media_id=media.id if media else None
        )
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('view_private_thread', thread_id=thread.id))
    return render_template('new_private_thread.html', form=form)

@app.route('/private/<int:thread_id>')
@login_required
def view_private_thread(thread_id):
    thread = db.session.get(PrivateThread, thread_id)
    if not thread:
        abort(404)
    invite = PrivateThreadInvite.query.filter_by(thread_id=thread.id, user_id=current_user.id).first()
    if not invite or invite.status != 'accepted':
        abort(403)
    messages = PrivateMessage.query.filter_by(thread_id=thread.id).order_by(PrivateMessage.created_at).all()
    form = PrivateReplyForm()
    return render_template('private_thread.html', thread=thread, messages=messages, form=form)

@app.route('/private/<int:thread_id>/reply', methods=['POST'])
@login_required
def private_reply(thread_id):
    thread = db.session.get(PrivateThread, thread_id)
    if not thread:
        abort(404)
    invite = PrivateThreadInvite.query.filter_by(thread_id=thread.id, user_id=current_user.id).first()
    if not invite or invite.status != 'accepted':
        abort(403)
    form = PrivateReplyForm()
    if form.validate_on_submit():
        media = None
        if form.media.data:
            media = save_uploaded_file(form.media.data, current_user.id)
        msg = PrivateMessage(
            thread_id=thread.id,
            user_id=current_user.id,
            content=sanitize_post_content(form.content.data),
            media_id=media.id if media else None
        )
        db.session.add(msg)
        db.session.commit()
        for inv in PrivateThreadInvite.query.filter_by(thread_id=thread.id, status='accepted').all():
            if inv.user_id != current_user.id:
                notif = Notification(
                    user_id=inv.user_id,
                    content=f'Новое сообщение в приватном треде "{thread.title}"',
                    link=url_for('view_private_thread', thread_id=thread.id)
                )
                db.session.add(notif)
        db.session.commit()
        return redirect(url_for('view_private_thread', thread_id=thread.id))
    flash('Ошибка при отправке')
    return redirect(url_for('view_private_thread', thread_id=thread.id))
    
@app.before_request
def apply_temporary_theme():
    if current_user.is_authenticated:
        temp = session.get('temp_theme')
        if temp:
            expiry = temp.get('expires')
            if expiry and datetime.now(timezone.utc) < expiry:
                current_user.theme_html = temp.get('html', '')
                current_user.theme_css = temp.get('css', '')
            else:
                session.pop('temp_theme', None)


@app.route('/reset_temp_theme', methods=['POST'])
@login_required
def reset_temp_theme():
    """Сброс временной темы (вызывается по таймеру)"""
    session.pop('temp_theme', None)
    return '', 204

@app.context_processor
def utility_processor():
    def get_menu_text(key, default):
        if current_user.is_authenticated and current_user.menu_texts:
            return current_user.menu_texts.get(key, default)
        return default
    return dict(get_menu_text=get_menu_text)



# ---------- Уведомления ----------
@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)

# ---------- Медиа ----------
@app.route('/media/<int:media_id>')
def media(media_id):
    media = db.session.get(Media, media_id)
    if not media:
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], media.filename)

# ---------- Админка ----------
from admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Board.query.first():
            sample_boards = [
                Board(name="Общий", description="Обсуждение всего", is_anonymous=False, age_restriction=0),
                Board(name="Технологии", description="IT и гаджеты", is_anonymous=False, age_restriction=0),
                Board(name="Аниме", description="Вайфу и прочее", is_anonymous=False, age_restriction=12)
            ]
            db.session.add_all(sample_boards)
            db.session.commit()
        if not User.query.first():
            admin = User(
                email="admin@example.com",
                display_name="Admin",
                unique_username="admin",
                password_hash=generate_password_hash("admin"),
                date_of_birth=datetime(1990, 1, 1).date(),
                is_admin=True,
                is_moderator=True,
                two_factor_enabled=False
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
