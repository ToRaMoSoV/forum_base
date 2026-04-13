from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from models import db, User, Board, Thread, Post, Media
from forms import UserEditForm, BoardForm
from werkzeug.security import generate_password_hash
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    users_count = User.query.count()
    boards_count = Board.query.count()
    threads_count = Thread.query.count()
    posts_count = Post.query.count()
    media_count = Media.query.count()
    return render_template('admin/dashboard.html',
                           users_count=users_count,
                           boards_count=boards_count,
                           threads_count=threads_count,
                           posts_count=posts_count,
                           media_count=media_count)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm()
    if form.validate_on_submit():
        user.email = form.email.data
        user.display_name = form.display_name.data
        user.unique_username = form.unique_username.data
        user.date_of_birth = form.date_of_birth.data
        user.is_admin = form.is_admin.data
        user.is_moderator = form.is_moderator.data
        user.is_banned = form.is_banned.data
        user.ban_reason = form.ban_reason.data
        if form.banned_until.data:
            try:
                user.banned_until = datetime.strptime(form.banned_until.data, '%Y-%m-%d %H:%M:%S')
            except:
                flash('Неверный формат даты (YYYY-MM-DD HH:MM:SS)', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user.id))
        else:
            user.banned_until = None
        db.session.commit()
        flash('Пользователь обновлён')
        return redirect(url_for('admin.users'))
    form.email.data = user.email
    form.display_name.data = user.display_name
    form.unique_username.data = user.unique_username
    form.date_of_birth.data = user.date_of_birth
    form.is_admin.data = user.is_admin
    form.is_moderator.data = user.is_moderator
    form.is_banned.data = user.is_banned
    form.ban_reason.data = user.ban_reason
    form.banned_until.data = user.banned_until.strftime('%Y-%m-%d %H:%M:%S') if user.banned_until else ''
    return render_template('admin/edit_user.html', form=form, user=user)

@admin_bp.route('/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя удалить самого себя')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удалён')
    return redirect(url_for('admin.users'))

@admin_bp.route('/boards')
@login_required
@admin_required
def boards():
    boards = Board.query.all()
    return render_template('admin/boards.html', boards=boards)

@admin_bp.route('/boards/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_board():
    form = BoardForm()
    form.moderator_id.choices = [(0, 'Нет')] + [(u.id, u.display_name) for u in User.query.all()]
    if form.validate_on_submit():
        board = Board(
            name=form.name.data,
            description=form.description.data,
            is_anonymous=form.is_anonymous.data,
            moderator_id=form.moderator_id.data if form.moderator_id.data != 0 else None,
            age_restriction=form.age_restriction.data
        )
        db.session.add(board)
        db.session.commit()
        flash('Доска создана')
        return redirect(url_for('admin.boards'))
    return render_template('admin/add_board.html', form=form)

@admin_bp.route('/boards/edit/<int:board_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_board(board_id):
    board = Board.query.get_or_404(board_id)
    form = BoardForm()
    form.moderator_id.choices = [(0, 'Нет')] + [(u.id, u.display_name) for u in User.query.all()]
    if form.validate_on_submit():
        board.name = form.name.data
        board.description = form.description.data
        board.is_anonymous = form.is_anonymous.data
        board.moderator_id = form.moderator_id.data if form.moderator_id.data != 0 else None
        board.age_restriction = form.age_restriction.data
        db.session.commit()
        flash('Доска обновлена')
        return redirect(url_for('admin.boards'))
    form.name.data = board.name
    form.description.data = board.description
    form.is_anonymous.data = board.is_anonymous
    form.moderator_id.data = board.moderator_id or 0
    form.age_restriction.data = board.age_restriction
    return render_template('admin/edit_board.html', form=form, board=board)

@admin_bp.route('/boards/delete/<int:board_id>')
@login_required
@admin_required
def delete_board(board_id):
    board = Board.query.get_or_404(board_id)
    db.session.delete(board)
    db.session.commit()
    flash('Доска удалена')
    return redirect(url_for('admin.boards'))

@admin_bp.route('/threads')
@login_required
@admin_required
def threads():
    threads = Thread.query.all()
    return render_template('admin/threads.html', threads=threads)

@admin_bp.route('/threads/delete/<int:thread_id>')
@login_required
@admin_required
def delete_thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    db.session.delete(thread)
    db.session.commit()
    flash('Тред удалён')
    return redirect(url_for('admin.threads'))

@admin_bp.route('/posts')
@login_required
@admin_required
def posts():
    posts = Post.query.all()
    return render_template('admin/posts.html', posts=posts)

@admin_bp.route('/posts/delete/<int:post_id>')
@login_required
@admin_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Пост удалён')
    return redirect(url_for('admin.posts'))

@admin_bp.route('/media')
@login_required
@admin_required
def media():
    media_list = Media.query.all()
    return render_template('admin/media.html', media=media_list)

@admin_bp.route('/media/delete/<int:media_id>')
@login_required
@admin_required
def delete_media(media_id):
    media = Media.query.get_or_404(media_id)
    import os
    from app import app
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], media.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(media)
    db.session.commit()
    flash('Медиа удалено')
    return redirect(url_for('admin.media'))
