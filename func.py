import importlib.util
import requests
import vk_api
import music
import time
import os
from gtts import gTTS

spec = importlib.util.spec_from_file_location("settings", "settings.py")
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)
vk_token = settings.vk_token
virustotal_key = settings.virustotal_key
yandex_key = settings.yandex_key
self_group_id = settings.self_group_id
vk = vk_api.VkApi(token=vk_token)
upload = vk_api.VkUpload(vk)
files_to_rm = []


def append_rm(name):
    if name not in files_to_rm:
        files_to_rm.append(name)


def write(user_id, body):
    vk.method("messages.setActivity", {"user_id": user_id, "type": "typing"})
    time.sleep(0.5)
    vk.method("messages.send", {"user_id": user_id, "message": body})


def virustotal(user_id, body):
    response = requests.post("https://www.virustotal.com/vtapi/v2/url/scan", data={"apikey": virustotal_key, "url": body[3:]})
    try:
        write(user_id, "Вот ссылка для проверки результата: " + response.json()["permalink"])
    except KeyError:
        write(user_id, "Неправильный url")
    except Exception:
        print("Неправильный ключ доступа Virustotal.")
        stop()


def file_send(user_id, name, counter, music=False):
    if music is True:
        append_rm(name)
        new_name = str(counter) + name.replace(".mp3", ".ogg")
        os.system('ffmpeg -n -loglevel quiet -i "' + name + '" -ac 1 "' + new_name + '"')
        try:
            save = upload.audio_message(new_name, group_id=self_group_id)[0]
        except Exception as error:
            if str(error) == "[15] Access denied: User can't upload docs to this group":
                print("Невозможно загрузить файл в ВК. Возомжно, в настройках группы -> разделы отключены документы.")
                stop()
            else:
                print("Непредвиденная ошибка при отправке сообщения.")
            append_rm(new_name)
    else:
        if os.path.getsize(name) == 0:
            write(user_id, "Запрещённое сообщение.")
            os.remove(name)
            return
        else:
            try:
                save = upload.audio_message(name, group_id=self_group_id)[0]
            except Exception as error:
                if str(error) == "[15] Access denied: User can't upload docs to this group":
                    print("Невозможно загрузить файл в ВК. Возможно, в настройках группы -> разделы отключены документы.")
                    os.remove(name)
                    stop()
                else:
                    print("Непредвиденная ошибка при отправке аудиосообщения.")
                    os.remove(name)
                    return

    owner_id = str(save["owner_id"])
    v_id = str(save["id"])
    if save["size"] == 288:
        write(user_id, "Запрещённое сообщение.")
        os.remove(name)
    else:
        vk.method("messages.setActivity", {"user_id": user_id, "type": "typing"})
        time.sleep(0.5)
        vk.method("messages.send", {"attachment": "doc" + owner_id + "_" + v_id, "user_id": user_id})
        if music is True:
            os.remove(new_name)
        if music is False:
            os.remove(name)


def gtts(user_id, body, num):
    json = requests.get("https://translate.yandex.net/api/v1.5/tr.json/detect?key=" + yandex_key + "&text=" + str(body))
    if json.json()["code"] == 401:
        if json.json()["message"] == "API key is invalid":
            print("Неправильный ключ доступа к API Яндекс переводчика.")
            stop()
    try:
        lang = json.json()["lang"]
    except KeyError:
        lang = "ru"
    try:
        tts = gTTS(body, lang=lang)
    except Exception:
        lang = "ru"
        tts = gTTS(body, lang=lang)
    vk_file = str(num) + "vk.mp3"
    tts.save(vk_file)
    file_send(user_id, vk_file, num)


def ya_music(user_id, body, counter):
    track = music.main(body)
    if track == "YmdlWrongUrlError":
        write(user_id, "Неправильный url.")
    else:
        file_send(user_id, track, counter, music=True)


def exchange(user_id, body):
    try:
        body = body.lower().replace("rub", "rur")
        ticker = requests.get("https://api.cryptonator.com/api/ticker/" + body).json()["ticker"]
        write(user_id, ticker["base"] + " стоит " + ticker["price"] + " " + ticker["target"])
    except Exception:
        write(user_id, "Неправильная валютная пара или ошибка на сервере Cryptonator.")


def stop():
    for f in files_to_rm:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
        except PermissionError:
            print("Не удалось удалить " + f)
    input("Для выхода нажмите Enter...")
