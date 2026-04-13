# 4chak - Шаблон форума / Forum Template

4chak — это шаблон форума с акцентом на гибкую кастомизацию внешнего вида. Основная особенность: каждый пользователь может настроить оформление форума под себя с помощью произвольного HTML и CSS. Поддерживаются обычные доски, анонимный раздел (очищается каждые 24 часа), приватные треды с приглашениями, двухфакторная аутентификация, загрузка медиафайлов, возрастные ограничения, панель администратора, API для получения новых постов и обновления в реальном времени.

Программа предназначена для развёртывания на локальной машине или хостинге.

Turn a web application into a fully customizable forum with support for user‑defined themes, profiles and threads.  
Designed for deployment on a local machine or hosting.

## Использование / How to use

**Основные элементы интерфейса / Main interface elements**

* **Главная** – список обычных досок и ссылка на анонимный раздел.  
  *Home – list of regular boards and a link to the anonymous section.*

* **Доски** – список всех неанонимных досок.  
  *Boards – list of all non‑anonymous boards.*

* **Анонимный раздел** – полностью анонимные треды, очищается каждые 24 часа.  
  *Anonymous board – fully anonymous threads, cleared every 24 hours.*

* **Профиль** – страница пользователя с настраиваемым HTML/CSS.  
  *Profile – user page with customizable HTML/CSS.*

* **Настройки** – изменение отображаемого имени, биографии, часового пояса, языка, HTML/CSS профиля, аватарки, личной темы форума, текстов пунктов меню.  
  *Settings – change display name, bio, timezone, language, profile HTML/CSS, avatar, personal forum theme, menu labels.*

* **Приватные треды** – создание тредов с приглашениями, только для участников.  
  *Private threads – create invite‑only threads.*

* **Уведомления** – оповещения о приглашениях и новых сообщениях в приватных тредах.  
  *Notifications – alerts for invites and new private messages.*

* **Админка** – управление пользователями, досками, тредами, постами, медиа. Доступ только для администраторов.  
  *Admin panel – manage users, boards, threads, posts, media. Accessible only to admins.*

*После запуска программы перейдите в браузер по адресу `http://127.0.0.1:5000`. Зарегистрируйтесь или войдите под администратором.*  
*After starting the program, open `http://127.0.0.1:5000` in your browser. Register or log in as admin.*

## Системные требования и установка / System requirements & installation

**Требования / Requirements**

- Windows / Linux / macOS
- Python 3.7 или выше / Python 3.7 or higher
- Учётная запись электронной почты (для двухфакторной аутентификации, необязательно)  
  *Email account (for two‑factor authentication, optional)*

**Установка / Installation**

1. Установите Python с официального сайта (если ещё не установлен).  
   *Install Python from the official website (if not already installed).*

2. Скачайте или скопируйте файлы проекта в отдельную папку:  
   *Download or copy the project files into a separate folder:*
   - `app.py`
   - `models.py`
   - `forms.py`
   - `utils.py`
   - `admin.py`
   - `requirements.txt`
   - папка `templates/`
   - папка `static/`

3. Установите необходимые библиотеки Python:  
   *Install the required Python libraries:*
   ```bash
   pip install -r requirements.txt
   ```

4. Запустите программу:  
   *Run the program:*
   ```bash
   python app.py
   ```
   Или дважды кликните `app.py` (на Windows).  
   *Or double‑click `app.py` (on Windows).*

5. Откройте браузер и перейдите по адресу: `http://127.0.0.1:5000`  
   *Open your browser and go to: `http://127.0.0.1:5000`*

**Учётные данные по умолчанию / Default credentials**

- Администратор / Administrator:  
  Email: `admin@example.com`  
  Пароль / Password: `admin`  
  (двухфакторная аутентификация отключена / two‑factor authentication disabled)

- Для входа в панель администратора используйте те же учётные данные.  
  *Use the same credentials to log into the admin panel.*

## Устранение возможных проблем / Troubleshooting

### Ошибка `ModuleNotFoundError` / Missing module
- Убедитесь, что все зависимости установлены: `pip install -r requirements.txt`.  
  *Make sure all dependencies are installed: `pip install -r requirements.txt`.*
- Если ошибка остаётся, установите недостающий модуль вручную: `pip install <module_name>`.  
  *If the error persists, install the missing module manually: `pip install <module_name>`.*

### Ошибка при запуске: `sqlalchemy.exc.OperationalError` / Database error
- Закройте программу.  
  *Close the program.*
- Удалите файл `forum.db` в папке проекта.  
  *Delete the `forum.db` file in the project folder.*
- Запустите `app.py` снова – база данных создастся автоматически.  
  *Run `app.py` again – the database will be recreated automatically.*

### Страница не открывается / Page does not open
- Убедитесь, что порт 5000 не занят другим приложением.  
  *Make sure port 5000 is not occupied by another application.*
- В последней строке `app.py` измените порт: `app.run(port=8080)` и откройте `http://127.0.0.1:8080`.  
  *In the last line of `app.py`, change the port: `app.run(port=8080)` and open `http://127.0.0.1:8080`.*

### Не приходит код двухфакторной аутентификации / 2FA code not received
- Проверьте настройки почты в `app.py` (переменные `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`).  
  *Check email settings in `app.py` (`MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`).*
- Если почта не настроена, код выводится в консоль (окно, где запущена программа).  
  *If email is not configured, the code is printed to the console (the window where the program is running).*

### Медиафайлы не загружаются / Media files not uploading
- Убедитесь, что папка `static/uploads` существует и доступна для записи.  
  *Make sure the `static/uploads` folder exists and is writable.*
- Разрешённые форматы: png, jpg, jpeg, gif, webp, mp4, webm.  
  *Allowed formats: png, jpg, jpeg, gif, webp, mp4, webm.*

Если ни один из способов не помог, создайте issue на GitHub с описанием проблемы и логами из консоли.  
*If none of the above helps, please open an issue on GitHub with a description of the problem and console logs.*

## Автор / Author

Created by Nill|981
