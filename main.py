import importlib.util
import threading
import random
import vk_api
import os
from vk_api.longpoll import VkLongPoll, VkEventType

if not os.path.exists("ffmpeg.exe"):
    print("Не найден ffmpeg.exe")
    input("Для выхода нажмите Enter...")
    os._exit(1)

try:
    spec = importlib.util.spec_from_file_location("settings", "settings.py")
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)
    vk_token = settings.vk_token
except FileNotFoundError:
    print("Не найден файл settings.py")
    input("Для выхода нажмите Enter...")
    os._exit(1)
except SyntaxError:
    print("Некорректно заполнен файл settings.py")
    input("Для выхода нажмите Enter...")
    os._exit(1)
else:
    from func import write, ya_music, virustotal, gtts, exchange, stop

vk = vk_api.VkApi(token=vk_token)
try:
    longpoll = VkLongPoll(vk)
except Exception as error:
    try:
        import socket
        socket.gethostbyaddr("vk.com")
    except Exception:
        print("Отсутствует подключение к интернету.")
        input("Для выхода нажмите Enter...")
        os._exit(1)
    else:
        if str(error) == "[15] Access denied: group messages are disabled":
            print("В настройках группы отключены сообщения.")
        else:
            print("Неправильный ключ доступа группы.")
        input("Для выхода нажмите Enter...")
        os._exit(1)
vk_counter = 0
vt_counter = 0
ex_counter = 0
ym_counter = 0
exit_number = "".join(str(random.randint(0, 9)) for _ in range(6))
print("Запущено получение сообщений.\nДля отключения бота отправьте /stop " + exit_number)
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        info = vk.method("users.get", {"user_id": event.user_id, "fields": "sex"})[0]
        text = event.text.replace("&amp;", "&").replace("&quot;", '"')
        try:
            print("{} {} написал{}: {}".format(info["first_name"], info["last_name"], "" if info["sex"] == 2 else "а", text if text != "" else "<сообщение без текста>"))
        except Exception:
            print("{} {} написал{}: {}".format(info["first_name"], info["last_name"], "" if info["sex"] == 2 else "а", "<неподдерживаемые символы>"))
        if text == "":
            t = threading.Thread(target=write, args=(event.user_id, "Запрещённое сообщение."))
        elif text == "/start":
            t = threading.Thread(target=write, args=(event.user_id, """Приветствую тебя, {} {}!
Я - бот, который может:
1. Озвучить твоё сообщение(напиши любой текст).
2. Отправить тебе песню с Яндекс.Музыки(ym ссылка на песню).
3. Написать текст справа налево(rv любой текст) или озвучить текст справа налево(rv_tts любой текст).
4. Проверить любую ссылку на вирусы(vt ссылка).
5. Сообщить курс валютной пары(ex валютная пара, например ex btc-usd)""".format(info["first_name"], info["last_name"])))
        elif text.startswith("/stop"):
            if text[6:] == exit_number:
                t = threading.Thread(target=write, args=(event.user_id, "Код верен, отключаюсь."))
                t.start()
                break
            else:
                t = threading.Thread(target=write, args=(event.user_id, "Неправильный код."))
        elif text[0:3].lower() == "ym ":
            ym_counter += 1
            t = threading.Thread(target=ya_music, args=(event.user_id, text[3:], ym_counter))
        elif text[0:3].lower() == "rv ":
            t = threading.Thread(target=write, args=(event.user_id, text[3:][::-1]))
        elif text[0:3].lower() == "vt ":
            vt_counter += 1
            t = threading.Thread(target=virustotal, args=(event.user_id, text))
        elif text[0:7].lower() == "rv_tts ":
            vk_counter += 1
            t = threading.Thread(target=gtts, args=(event.user_id, text[7:][::-1], vk_counter))
        elif text[0:3].lower() == "ex ":
            ex_counter += 1
            t = threading.Thread(target=exchange, args=(event.user_id, text[3:].lower()))
        else:
            vk_counter += 1
            t = threading.Thread(target=gtts, args=(event.user_id, text, vk_counter))
        t.start()
print("Остановка.\nГолосовых сообщений отправлено: " + str(vk_counter + ym_counter))
print("Команда vt была использована " + str(vt_counter) + " раз.")
print("Команда ex была использована " + str(ex_counter) + " раз.")
stop()
