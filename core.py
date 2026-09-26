import config
import datetime
import random
import psycopg2
import os
from psycopg2 import pool

# Пул соединений (чтобы не открывать новое подключение каждый раз)
DATABASE_URL = os.environ.get('DATABASE_URL')
connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)


def get_conn():
    return connection_pool.getconn()


def release_conn(conn):
    connection_pool.putconn(conn)


# Добавить агента
def add_agent(agent_id):
    con = get_conn()
    cur = con.cursor()
    cur.execute("INSERT INTO agents (agent_id) VALUES (%s)", (agent_id,))
    con.commit()
    cur.close()
    release_conn(con)


# Добавить файл
def add_file(req_id, file_id, file_name, type):
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO files (req_id, file_id, file_name, type) VALUES (%s, %s, %s, %s)",
        (req_id, file_id, file_name, type)
    )
    con.commit()
    cur.close()
    release_conn(con)


# Создать запрос
def new_req(user_id, request):
    con = get_conn()
    cur = con.cursor()
    cur.execute("INSERT INTO requests (user_id, req_status) VALUES (%s, 'waiting') RETURNING req_id", (user_id,))
    req_id = cur.fetchone()[0]

    dt = datetime.datetime.now()
    date_now = dt.strftime('%d.%m.%Y %H:%M:%S')

    cur.execute(
        "INSERT INTO messages (req_id, message, user_status, date) VALUES (%s, %s, 'user', %s)",
        (req_id, request, date_now)
    )
    con.commit()
    cur.close()
    release_conn(con)
    return req_id


# Добавить сообщение
def add_message(req_id, message, user_status):
    req_status = 'waiting' if user_status == 'user' else 'answered'
    dt = datetime.datetime.now()
    date_now = dt.strftime('%d.%m.%Y %H:%M:%S')

    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO messages (req_id, message, user_status, date) VALUES (%s, %s, %s, %s)",
        (req_id, message, user_status, date_now)
    )
    cur.execute("UPDATE requests SET req_status = %s WHERE req_id = %s", (req_status, req_id))
    con.commit()
    cur.close()
    release_conn(con)


# Добавить пароли
def add_passwords(passwords):
    con = get_conn()
    cur = con.cursor()
    for password in passwords:
        cur.execute("INSERT INTO passwords (password) VALUES (%s)", (password,))
    con.commit()
    cur.close()
    release_conn(con)


# Проверить статус агента
def check_agent_status(user_id):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM agents WHERE agent_id = %s", (user_id,))
    agent = cur.fetchone()
    cur.close()
    release_conn(con)
    return agent is not None


# Проверить валидность пароля
def valid_password(password):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM passwords WHERE password = %s", (password,))
    row = cur.fetchone()
    cur.close()
    release_conn(con)
    return row is not None


# Проверить, отправляет ли пользователь файл
def get_file(message):
    types = ['document', 'video', 'audio', 'voice']
    dt = datetime.datetime.now()
    date_now = dt.strftime('%d.%m.%Y %H:%M:%S')

    try:
        return {'file_id': message.json['photo'][-1]['file_id'], 'file_name': date_now, 'type': 'photo', 'text': str(message.caption)}
    except:
        for type in types:
            try:
                if type in ('document', 'video'):
                    file_name = message.json[type]['file_name']
                else:
                    file_name = date_now
                return {'file_id': message.json[type]['file_id'], 'file_name': file_name, 'type': type, 'text': str(message.caption)}
            except:
                pass
        return None


# Получить иконку статуса запроса
def get_icon_from_status(req_status, user_status):
    if req_status == 'confirm':
        return '✅'
    elif req_status == 'waiting':
        return '⏳' if user_status == 'user' else '❗️'
    elif req_status == 'answered':
        return '❗️' if user_status == 'user' else '⏳'


# Получить текст для кнопки с файлом
def get_file_text(file_name, type):
    if type == 'photo':
        return f'📷 | Фото {file_name}'
    elif type == 'document':
        return f'📄 | Документ {file_name}'
    elif type == 'video':
        return f'🎥 | Видео {file_name}'
    elif type == 'audio':
        return f'🎵 | Аудио {file_name}'
    elif type == 'voice':
        return f'🎧 | Голосовое сообщение {file_name}'


# Сгенерировать пароли
def generate_passwords(number, lenght):
    chars = 'abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
    passsords = []
    for _ in range(number):
        password = ''
        for _ in range(lenght):
            password += random.choice(chars)
        passsords.append(password)
    return passsords


# Получить user_id создателя запроса
def get_user_id_of_req(req_id):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT user_id FROM requests WHERE req_id = %s", (req_id,))
    user_id = cur.fetchone()[0]
    cur.close()
    release_conn(con)
    return user_id


# Получить file_id по id записи в БД
def get_file_id(id):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT file_id FROM files WHERE id = %s", (id,))
    file_id = cur.fetchone()[0]
    cur.close()
    release_conn(con)
    return file_id


# Получить статус запроса
def get_req_status(req_id):
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT req_status FROM requests WHERE req_id = %s", (req_id,))
    req_status = cur.fetchone()[0]
    cur.close()
    release_conn(con)
    return req_status


# Удалить пароль
def delete_password(password):
    con = get_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM passwords WHERE password = %s", (password,))
    con.commit()
    cur.close()
    release_conn(con)


# Удалить агента
def delete_agent(agent_id):
    con = get_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM agents WHERE agent_id = %s", (agent_id,))
    con.commit()
    cur.close()
    release_conn(con)


# Завершить запрос
def confirm_req(req_id):
    con = get_conn()
    cur = con.cursor()
    cur.execute("UPDATE requests SET req_status = 'confirm' WHERE req_id = %s", (req_id,))
    con.commit()
    cur.close()
    release_conn(con)


# Получить пароли с лимитом
def get_passwords(number):
    limit = (int(number) * 10) - 10
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT password FROM passwords LIMIT 10 OFFSET %s", (limit,))
    passwords = cur.fetchall()
    cur.close()
    release_conn(con)
    return passwords


# Получить агентов с лимитом
def get_agents(number):
    limit = (int(number) * 10) - 10
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT agent_id FROM agents LIMIT 10 OFFSET %s", (limit,))
    agents = cur.fetchall()
    cur.close()
    release_conn(con)
    return agents


# Получить мои запросы с лимитом
def my_reqs(number, user_id):
    limit = (int(number) * 10) - 10
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "SELECT req_id, req_status FROM requests WHERE user_id = %s ORDER BY req_id DESC LIMIT 10 OFFSET %s",
        (user_id, limit)
    )
    reqs = cur.fetchall()
    cur.close()
    release_conn(con)
    return reqs


# Получить запросы по статусу с лимитом
def get_reqs(number, callback):
    limit = (int(number) * 10) - 10
    req_status = callback.replace('_reqs', '')
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "SELECT req_id, req_status FROM requests WHERE req_status = %s ORDER BY req_id DESC LIMIT 10 OFFSET %s",
        (req_status, limit)
    )
    reqs = cur.fetchall()
    cur.close()
    release_conn(con)
    return reqs


# Получить файлы по запросу с лимитом
def get_files(number, req_id):
    limit = (int(number) * 10) - 10
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "SELECT id, file_name, type FROM files WHERE req_id = %s ORDER BY id DESC LIMIT 10 OFFSET %s",
        (req_id, limit)
    )
    files = cur.fetchall()
    cur.close()
    release_conn(con)
    return files


# Получить историю запроса
def get_request_data(req_id, callback):
    get_dialog_user_status = 'user' if 'my_reqs' in callback else 'agent'

    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT message, user_status, date FROM messages WHERE req_id = %s", (req_id,))
    messages = cur.fetchall()
    cur.close()
    release_conn(con)

    data = []
    text = ''
    i = 1

    for message in messages:
        message_value = message[0]
        user_status = message[1]
        date = message[2]

        if user_status == 'user':
            text_status = '👤 Ваше сообщение' if get_dialog_user_status == 'user' else '👤 Сообщение пользователя'
        else:
            text_status = '🧑‍💻 Агент поддержки'

        backup_text = text
        text += f'{text_status}\n{date}\n{message_value}\n\n'

        if len(text) >= 4096:
            data.append(backup_text)
            text = f'{text_status}\n{date}\n{message_value}\n\n'

        if len(messages) == i:
            if len(text) >= 4096:
                data.append(backup_text)
                text = f'{text_status}\n{date}\n{message_value}\n\n'
            data.append(text)

        i += 1

    return data
