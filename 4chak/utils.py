import bleach
import re
from urllib.parse import urlparse
from models import db, Board, Thread, Post, Media, User

# utils.py

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "mp4",
    "webm"
}

def allowed_file(filename):

    if "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()

    return ext in ALLOWED_EXTENSIONS
    
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'div', 'span', 'a', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
    'ul', 'ol', 'li', 'pre', 'code', 'blockquote', 'hr', 'sub', 'sup',
    'b', 'i', 'big', 'small', 'strike', 's', 'del', 'ins',
    'details', 'summary', 'figure', 'figcaption'
]
ALLOWED_ATTRS = {
    '*': ['class', 'id', 'title'],
    'a': ['href', 'target', 'rel', 'name'],
    'img': ['src', 'alt', 'width', 'height', 'title'],
    'table': ['border', 'cellpadding', 'cellspacing', 'width'],
    'td': ['colspan', 'rowspan', 'align', 'valign'],
    'th': ['colspan', 'rowspan', 'align', 'valign'],
    'div': ['align'],
    'p': ['align'],
    'h1': ['align'], 'h2': ['align'], 'h3': ['align'],
    'font': ['color', 'size', 'face'],  # legacy, разрешаем
}

# Для профиля добавляем style
PROFILE_EXTRA_ATTRS = {'*': ['style']}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_safe_url(url):
    """Проверяет, что URL имеет безопасную схему (http, https, относительный)"""
    if not url:
        return False
    # Разрешаем относительные URL
    if url.startswith('/') or url.startswith('#'):
        return True
    # Парсим схему
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https'):
        return True
    # Также разрешаем URL без схемы (//example.com)
    if parsed.scheme == '' and url.startswith('//'):
        return True
    return False

def sanitize_html(html, extra_tags=None, extra_attrs=None, allow_style=False):
    """
    Очистка HTML с белым списком тегов и атрибутов.
    allow_style=True разрешает атрибут style и дополнительные теги/атрибуты для профиля.
    """
    tags = ALLOWED_TAGS.copy()
    if extra_tags:
        tags.extend(extra_tags)

    attrs = ALLOWED_ATTRS.copy()
    if extra_attrs:
        for k, v in extra_attrs.items():
            if k in attrs:
                attrs[k].extend(v)
            else:
                attrs[k] = v

    if allow_style:
        attrs['*'] = attrs.get('*', []) + ['style']

    cleaned = bleach.clean(html, tags=tags, attributes=attrs, strip=True)

    # Очистка URL в href и src
    def clean_url_attr(match, attr_name):
        value = match.group(1)
        if not is_safe_url(value):
            return f'{attr_name}="#"'
        return match.group(0)

    cleaned = re.sub(r'href="([^"]+)"', lambda m: clean_url_attr(m, 'href'), cleaned)
    cleaned = re.sub(r'src="([^"]+)"', lambda m: clean_url_attr(m, 'src'), cleaned)

    # Если style разрешён, очищаем его от опасных конструкций
    if allow_style:
        def clean_style_attr(match):
            style = match.group(1)
            # Удаляем javascript: и expression
            style = re.sub(r'javascript:', '', style, flags=re.IGNORECASE)
            style = re.sub(r'expression\s*\([^)]*\)', '', style, flags=re.IGNORECASE)
            return f'style="{style}"'
        cleaned = re.sub(r'style="([^"]*)"', clean_style_attr, cleaned)

    return cleaned

def sanitize_profile_html(html):
    """Очистка HTML для профиля (разрешён style и дополнительные теги, например iframe)"""
    extra_tags = ['iframe', 'center', 'font']
    return sanitize_html(html, extra_tags=extra_tags, allow_style=True)

def sanitize_post_content(html):
    """Очистка HTML для сообщений (без style, без iframe, без опасных URL)"""
    return sanitize_html(html, allow_style=False)

def sanitize_css(css):
    """Очистка CSS (удаляем @import, javascript:, expression)"""
    css = re.sub(r'@import\s+[^;]+;', '', css)
    css = re.sub(r'javascript:', '', css, flags=re.IGNORECASE)
    css = re.sub(r'expression\s*\([^)]*\)', '', css, flags=re.IGNORECASE)
    return css
    
def check_age_restriction(user_age, restriction):
    if restriction == 0:
        return True
    if user_age is None:
        return False
    return user_age >= restriction

def clear_anonymous_board():
    with db.engine.begin() as conn:
        anon_board = Board.query.filter_by(is_anonymous=True).first()
        if anon_board:
            threads = Thread.query.filter_by(board_id=anon_board.id).all()
            for thread in threads:
                Post.query.filter_by(thread_id=thread.id).delete()
                db.session.delete(thread)
            orphan_media = Media.query.filter(~Media.post.any()).all()
            for m in orphan_media:
                db.session.delete(m)
            db.session.commit()

def generate_unique_username(display_name):
    base = re.sub(r'[^a-zA-Z0-9_]', '', display_name).lower()
    if not base:
        base = 'user'
    candidate = base
    counter = 1
    while User.query.filter_by(unique_username=candidate).first():
        candidate = f"{base}{counter}"
        counter += 1
    return candidate
