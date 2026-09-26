import config
import core
import telebot
import random
import datetime
import markup
import sys
from telebot import apihelper

if config.PROXY_URL:
    apihelper.proxy = {'https': config.PROXY_URL}

bot = telebot.TeleBot(config.TOKEN, skip_pending=True)

# Инициализация базы данных при запуске
core.init_db()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, '👋🏻 Привет! Это бот для технической поддержки пользователей.\nЕсли у тебя есть какой-либо вопрос или проблема - нажми на кнопку <b>Написать запрос</b> и наши сотрудники в скором времени тебе ответят!', parse_mode='html', reply_markup=markup.markup_main())


@bot.message_handler(commands=['agent'])
def agent(message):
    user_id = message.from_user.id

    if core.check_agent_status(user_id) == True:
        bot.send_message(message.chat.id, '🔑 Вы авторизованы как Агент поддержки', parse_mode='html', reply_markup=markup.markup_agent())
    else:
        take_password_message = bot.send_message(message.chat.id, '⚠️ Тебя нет в базе. Отправь одноразовый пароль доступа.', reply_markup=markup.markup_cancel())
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_password_message, get_password_message)


@bot.message_handler(commands=['admin'])
def admin(message):
    user_id = message.from_user.id

    if str(user_id) == config.ADMIN_ID:
        bot.send_message(message.chat.id, '🔑 Вы авторизованы как Админ', reply_markup=markup.markup_admin())
    else:
        bot.send_message(message.chat.id, '🚫 Эта команда доступна только администратору.')


@bot.message_handler(content_types=['text'])
def send_text(message):
    user_id = message.from_user.id

    if message.text == '✏️ Написать запрос':
        take_new_request = bot.send_message(message.chat.id, 'Введите свой запрос и Агенты Поддержки скоро с вами свяжутся.', reply_markup=markup.markup_cancel())
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_new_request, get_new_request)

    elif message.text == '✉️ Мои запросы':
        markup_and_value = markup.markup_reqs(user_id, 'my_reqs', '1')
        markup_req = markup_and_value[0]
        value = markup_and_value[1]

        if value == 0:
            bot.send_message(message.chat.id, 'У вас пока ещё нет запросов.', reply_markup=markup.markup_main())
        else:
            bot.send_message(message.chat.id, 'Ваши запросы:', reply_markup=markup_req)

    else:
        bot.send_message(message.chat.id, 'Вы возвращены в главное меню.', parse_mode='html', reply_markup=markup.markup_main())


def get_password_message(message):
    password = message.text
    user_id = message.from_user.id

    if password == None:
        send_message = bot.send_message(message.chat.id, '⚠️ Вы отправляете не текст. Попробуйте еще раз.', reply_markup=markup.markup_cancel())
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(send_message, get_password_message)

    elif password.lower() == 'отмена':
        bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
        return

    elif core.valid_password(password) == True:
        core.delete_password(password)
        core.add_agent(user_id)
        bot.send_message(message.chat.id, '🔑 Вы авторизованы как Агент поддержки', parse_mode='html', reply_markup=markup.markup_main())
        bot.send_message(message.chat.id, 'Выберите раздел технической панели:', parse_mode='html', reply_markup=markup.markup_agent())

    else:
        send_message = bot.send_message(message.chat.id, '⚠️ Неверный пароль. Попробуй ещё раз.', reply_markup=markup.markup_cancel())
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(send_message, get_password_message)


def get_agent_id_message(message):
    agent_id = message.text

    if agent_id == None:
        take_agent_id_message = bot.send_message(message.chat.id, '⚠️ Вы отправляете не текст. Попробуйте еще раз.', reply_markup=markup.markup_cancel())
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_agent_id_message, get_agent_id_message)

    elif agent_id.lower() == 'отмена':
        bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
        return

    else:
        core.add_agent(agent_id)
        bot.send_message(message.chat.id, '✅ Агент успешно добавлен.', reply_markup=markup.markup_main())
        bot.send_message(message.chat.id, 'Выберите раздел админ панели:', reply_markup=markup.markup_admin())


def get_new_request(message):
    request = message.text
    user_id = message.from_user.id
    check_file = core.get_file(message)

    if check_file != None:
        file_id = check_file['file_id']
        file_name = check_file['file_name']
        type = check_file['type']
        request = check_file['text']

        if str(request) == 'None':
            take_new_request = bot.send_message(message.chat.id, '⚠️ Вы не ввели ваш запрос. Попробуйте ещё раз, отправив текст вместе с файлом.', reply_markup=markup.markup_cancel())
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.register_next_step_handler(take_new_request, get_new_request)

        else:
            req_id = core.new_req(user_id, request)
            core.add_file(req_id, file_id, file_name, type)
            bot.send_message(message.chat.id, f'✅ Ваш запрос под ID {req_id} создан. Посмотреть текущие запросы можно нажав кнопку <b>Мои текущие запросы</b>', parse_mode='html', reply_markup=markup.markup_main())

    else:
        if request == None:
            take_new_request = bot.send_message(message.chat.id, '⚠️ Отправляемый вами тип данных не поддерживается в боте. Попробуйте еще раз отправить ваш запрос, использовав один из доступных типов данных (текст, файлы, фото, видео, аудио, голосовые сообщения)', reply_markup=markup.markup_cancel())
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.register_next_step_handler(take_new_request, get_new_request)

        elif request.lower() == 'отмена':
            bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
            return

        else:
            req_id = core.new_req(user_id, request)
            bot.send_message(message.chat.id, f'✅ Ваш запрос под ID {req_id} создан. Посмотреть текущие запросы можно нажав кнопку <b>Мои текущие запросы</b>', parse_mode='html', reply_markup=markup.markup_main())


def get_additional_message(message, req_id, status):
    additional_message = message.text
    check_file = core.get_file(message)
    type = None

    if check_file != None:
        file_id = check_file['file_id']
        file_name = check_file['file_name']
        type = check_file['type']
        additional_message = check_file['text']
        core.add_file(req_id, file_id, file_name, type)

    if additional_message == None:
        take_additional_message = bot.send_message(chat_id=message.chat.id, text='⚠️ Отправляемый вами тип данных не поддерживается в боте. Попробуйте еще раз отправить ваше сообщение, использовав один из доступных типов данных (текст, файлы, фото, видео, аудио, голосовые сообщения).', reply_markup=markup.markup_cancel())
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.register_next_step_handler(take_additional_message, get_additional_message, req_id, status)

    elif additional_message.lower() == 'отмена':
        bot.send_message(message.chat.id, 'Отменено.', reply_markup=markup.markup_main())
        return

    else:
        if additional_message != 'None':
            core.add_message(req_id, additional_message, status)

        if check_file != None:
            text = '✅ Ваш файл и сообщение успешно отправлены!' if additional_message != 'None' else '✅ Ваш файл успешно отправлен!'
        else:
            text = '✅ Ваше сообщение успешно отправлено!'

        bot.send_message(message.chat.id, text, reply_markup=markup.markup_main())

        if status == 'agent':
            user_id = core.get_user_id_of_req(req_id)
            try:
                if additional_message == 'None':
                    additional_message = ''

                bot.send_message(user_id, f'⚠️ Получен новый ответ на ваш запрос ID {req_id}!\n\n🧑‍💻 Ответ агента поддержки:\n{additional_message}', reply_markup=markup.markup_main())

                if type == 'photo':
                    bot.send_photo(user_id, photo=file_id, reply_markup=markup.markup_main())
                elif type == 'document':
                    bot.send_document(user_id, data=file_id, reply_markup=markup.markup_main())
                elif type == 'video':
                    bot.send_video(user_id, data=file_id, reply_markup=markup.markup_main())
                elif type == 'audio':
                    bot.send_audio(user_id, audio=file_id, reply_markup=markup.markup_main())
                elif type == 'voice':
                    bot.send_voice(user_id, voice=file_id, reply_markup=markup.markup_main())
                else:
                    bot.send_message(user_id, additional_message, reply_markup=markup.markup_main())
            except:
                pass


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.message.chat.id

    if call.message:
        if ('my_reqs:' in call.data) or ('waiting_reqs:' in call.data) or ('answered_reqs:' in call.data) or ('confirm_reqs:' in call.data):
            parts = call.data.split(':')
            callback = parts[0]
            number = parts[1]
            markup_and_value = markup.markup_reqs(user_id, callback, number)
            markup_req = markup_and_value[0]
            value = markup_and_value[1]

            if value == 0:
                bot.send_message(chat_id=call.message.chat.id, text='⚠️ Запросы не обнаружены.', reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)
                return

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Нажмите на запрос, чтобы посмотреть историю переписки, либо добавить сообщение:', reply_markup=markup_req)
            except:
                bot.send_message(chat_id=call.message.chat.id, text='Ваши запросы:', reply_markup=markup_req)

            bot.answer_callback_query(call.id)

        elif 'open_req:' in call.data:
            parts = call.data.split(':')
            req_id = parts[1]
            callback = parts[2]

            req_status = core.get_req_status(req_id)
            request_data = core.get_request_data(req_id, callback)
            len_req_data = len(request_data)

            i = 1
            for data in request_data:
                if i == len_req_data:
                    markup_req = markup.markup_request_action(req_id, req_status, callback)
                else:
                    markup_req = None

                bot.send_message(chat_id=call.message.chat.id, text=data, parse_mode='html', reply_markup=markup_req)
                i += 1

            bot.answer_callback_query(call.id)

        elif 'add_message:' in call.data:
            parts = call.data.split(':')
            req_id = parts[1]
            status_user = parts[2]

            take_additional_message = bot.send_message(chat_id=call.message.chat.id, text='Отправьте ваше сообщение, использовав один из доступных типов данных (текст, файлы, фото, видео, аудио, голосовые сообщения)', reply_markup=markup.markup_cancel())
            bot.register_next_step_handler(take_additional_message, get_additional_message, req_id, status_user)
            bot.answer_callback_query(call.id)

        elif 'confirm_req:' in call.data:
            parts = call.data.split(':')
            confirm_status = parts[1]
            req_id = parts[2]

            if core.get_req_status(req_id) == 'confirm':
                bot.send_message(chat_id=call.message.chat.id, text="⚠️ Этот запрос уже завершен.", reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)
                return

            if confirm_status == 'wait':
                bot.send_message(chat_id=call.message.chat.id, text="Для завершения запроса - нажмите кнопку <b>Подтвердить</b>", parse_mode='html', reply_markup=markup.markup_confirm_req(req_id))

            elif confirm_status == 'true':
                core.confirm_req(req_id)

                try:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Запрос успешно завершён.", reply_markup=markup.markup_main())
                except:
                    bot.send_message(chat_id=call.message.chat.id, text="✅ Запрос успешно завершён.", reply_markup=markup.markup_main())

                bot.answer_callback_query(call.id)

        elif 'req_files:' in call.data:
            parts = call.data.split(':')
            req_id = parts[1]
            callback = parts[2]
            number = parts[3]

            markup_and_value = markup.markup_files(number, req_id, callback)
            markup_files = markup_and_value[0]
            value = markup_and_value[1]

            if value == 0:
                bot.send_message(chat_id=call.message.chat.id, text='⚠️ Файлы не обнаружены.', reply_markup=markup.markup_main())
                bot.answer_callback_query(call.id)
                return

            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Нажмите на файл, чтобы получить его.', reply_markup=markup_files)
            except:
                bot.send_message(chat_id=call.message.chat.id, text='Нажмите на файл, чтобы получить его.', reply_markup=markup_files)

            bot.answer_callback_query(call.id)

        elif 'send_file:' in call.data:
            parts = call.data.split(':')
            id = parts[1]
            type = parts[2]

            file_id = core.get_file_id(id)

            if type == 'photo':
                bot.send_photo(call.message.chat.id, photo=file_id, reply_markup=markup.markup_main())
            elif type == 'document':
                bot.send_document(call.message.chat.id, data=file_id, reply_markup=markup.markup_main())
            elif type == 'video':
                bot.send_video(call.message.chat.id, data=file_id, reply_markup=markup.markup_main())
            elif type == 'audio':
                bot.send_audio(call.message.chat.id, audio=file_id, reply_markup=markup.markup_main())
            elif type == 'voice':
                bot.send_voice(call.message.chat.id, voice=file_id, reply_markup=markup.markup_main())

            bot.answer_callback_query(call.id)

        elif call.data == 'back_agent':
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='🔑 Вы авторизованы как Агент поддержки', parse_mode='html', reply_markup=markup.markup_agent())
            except:
                bot.send_message(call.message.chat.id, '🔑 Вы авторизованы как Агент поддержки', parse_mode='html', reply_markup=markup.markup_agent())

            bot.answer_callback_query(call.id)

        elif call.data == 'back_admin':
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='🔑 Вы авторизованы как Админ', parse_mode='html', reply_markup=markup.markup_admin())
            except:
                bot.send_message(call.message.chat.id, '🔑 Вы авторизованы как Админ', parse_mode='html', reply_markup=markup.markup_admin())

            bot.answer_callback_query(call.id)

        elif call.data == 'add_agent':
            take_agent_id_message = bot.send_message(chat_id=call.message.chat.id, text='Чтобы добавить агента поддержки - введите его ID Telegram.', reply_markup=markup.markup_cancel())
            bot.register_next_step_handler(take_agent_id_message, get_agent_id_message)

        elif 'all_agents:' in call.data:
            number = call.data.split(':')[1]
