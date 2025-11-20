from flask import Flask, request, render_template_string, redirect, session, url_for
import json, os, csv, io
from bot import bot, DELIVERY_GROUP_ID
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # секрет для сессий

# Админы веб-панели (логин/пароль)
ADMINS_WEB = {
    os.getenv("ADMIN_LOGIN", "admin"): os.getenv("ADMIN_PASS", "123456")
}

TRACK_FILE = "track_codes.json"

def load_track_codes():
    try:
        with open(TRACK_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_track_codes(codes):
    with open(TRACK_FILE, "w") as f:
        json.dump(codes, f, indent=4)

# HTML шаблон
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel</title>
</head>
<body>
{% if 'username' in session %}
<h2>Привет, {{ session['username'] }}!</h2>
<a href="{{ url_for('logout') }}">Выйти</a>
<hr>

<h3>Добавить/обновить один трек-код</h3>
<form method="post">
    Трек-код: <input type="text" name="code" required><br><br>
    Статус: <input type="text" name="status" required><br><br>
    <button type="submit">Сохранить</button>
</form>

<hr>
<h3>Массовое добавление через CSV</h3>
<form method="post" enctype="multipart/form-data" action="{{ url_for('upload_csv') }}">
    Выберите CSV файл (код;статус): <input type="file" name="file" accept=".csv" required><br><br>
    <button type="submit">Загрузить CSV</button>
</form>

<hr>
<h3>Существующие трек-коды</h3>
<ul>
{% for code, status in codes.items() %}
    <li><b>{{ code }}</b>: {{ status }}</li>
{% endfor %}
</ul>
{% else %}
<h2>Вход в админ-панель</h2>
<form method="post" action="{{ url_for('login') }}">
    Логин: <input type="text" name="username" required><br><br>
    Пароль: <input type="password" name="password" required><br><br>
    <button type="submit">Войти</button>
</form>
{% endif %}
</body>
</html>
"""

# Главная страница
@app.route("/", methods=["GET", "POST"])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    codes = load_track_codes()
    if request.method == "POST":
        code = request.form["code"].strip().upper()
        status = request.form["status"].strip()
        codes[code] = status
        save_track_codes(codes)

        # Отправка уведомления в Telegram
        try:
            bot.send_message(DELIVERY_GROUP_ID, f"✅ Трек-код {code} добавлен/обновлен.\nСтатус: {status}")
        except:
            pass

        return redirect("/")
    return render_template_string(HTML_PAGE, codes=codes)

# Загрузка CSV
@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    if 'username' not in session:
        return redirect(url_for('login'))
    file = request.files.get("file")
    if not file:
        return "❌ Файл не выбран"
    
    codes = load_track_codes()
    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.reader(stream, delimiter=';')
    count = 0
    for row in reader:
        if len(row) >= 2:
            code = row[0].strip().upper()
            status = row[1].strip()
            codes[code] = status
            count += 1
            # Уведомление в Telegram
            try:
                bot.send_message(DELIVERY_GROUP_ID, f"✅ Трек-код {code} добавлен/обновлен.\nСтатус: {status}")
            except:
                pass
    save_track_codes(codes)
    return f"✅ Загружено {count} трек-кодов. <a href='/'>Вернуться</a>"

# Вход
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in ADMINS_WEB and ADMINS_WEB[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "❌ Неверный логин или пароль"
    return render_template_string(HTML_PAGE)

# Выход
@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
