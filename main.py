import vk_api,threading,os,importlib.util
from vk_api.longpoll import VkLongPoll,VkEventType
if not os.path.exists("ffmpeg.exe"):
    print("Не найден ffmpeg.exe")
    input("Для выхода нажмите Enter...")
    os._exit(1)
try:
    spec=importlib.util.spec_from_file_location("settings","settings.py")
    settings=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)
    vk_token=settings.vk_token
    self_id=settings.self_id
except FileNotFoundError:
    print("Не найден файл settings.py")
    input("Для выхода нажмите Enter...")
    os._exit(1)
except SyntaxError:
    print("Некорректно заполнен файл settings.py")
    input("Для выхода нажмите Enter...")
    os._exit(1)
from func import *
vk=vk_api.VkApi(token=vk_token)
try:
    longpoll=VkLongPoll(vk)
except Exception as error:
    try:
        import socket
        socket.gethostbyaddr("vk.com")
    except:
        print("Отсутствует подключение к интернету.")
        input("Для выхода нажмите Enter...")
        os._exit(1)
    else:
        if str(error)=="[15] Access denied: group messages are disabled":
            print("В настройках группы отключены сообщения.")
        else:
            print("Неправильный ключ доступа группы.")
        input("Для выхода нажмите Enter...")
        os._exit(1)
vk_counter=0
yandex_counter=0
print("Запущено получение сообщений.\n")
for event in longpoll.listen():
    if event.type==VkEventType.MESSAGE_NEW and event.to_me:
        info=vk.method("users.get",{"user_id":event.user_id,"fields":"sex"})[0]
        text=event.text.replace("&amp;","&").replace("&quot;",'"')
        try:
            print("{} {} написал{}: {}".format(info["first_name"],info["last_name"],"" if info["sex"]==2 else "а",text if text!="" else "<сообщение без текста>"))
        except:
            print("{} {} написал{}: {}".format(info["first_name"],info["last_name"],"" if info["sex"]==2 else "а","<неподдерживаемые символы>"))
        if text=="":
            t=threading.Thread(target=write,args=(event.user_id,"Запрещённое сообщение."))
        elif text=="/stop" and event.user_id==self_id:
            print("Остановка.\nГолосовых сообщений отправлено: "+str(vk_counter+yandex_counter))
            stop()
        elif text=="/stop" and event.user_id!=self_id:
            t=threading.Thread(target=write,args=(event.user_id,"Недостаточно прав для выполнения данной команды."))
        elif text[0:3].lower()=="ym ":
            yandex_counter+=1
            t=threading.Thread(target=ya_music,args=(event.user_id,text[3:]))
        elif text[0:3].lower()=="rv ":
            t=threading.Thread(target=write,args=(event.user_id,text[3:][::-1]))
        elif text[0:3].lower()=="vt ":
            t=threading.Thread(target=virustotal,args=(event.user_id,text))
        elif text[0:7].lower()=="rv_tts ":
            vk_counter+=1
            t=threading.Thread(target=gtts,args=(event.user_id,text[7:][::-1],vk_counter))
        elif text[0:3].lower()=="ex ":
            t=threading.Thread(target=exchange,args=(event.user_id,text[3:].lower()))
        else:
            vk_counter+=1
            t=threading.Thread(target=gtts,args=(event.user_id,text,vk_counter))
        t.start()
