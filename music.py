import os,urllib.request,urllib.parse,json
from hashlib import md5
class YmdlError(Exception):
    pass
forbidden_sym={34: "''", 92: 45, 47: 45, 42: 95, 60: None, 62: None, 58: None, 124: None, 63: None}
def download_file(url,save_as):
    req=urllib.request.urlopen(url)
    with open(save_as,"wb") as f:
        f.write(req.read())
def info_loader(template,**kwargs):
    with urllib.request.urlopen(template.format(**kwargs),timeout=6) as r:
        return json.loads(r.read().decode())
def get_track_url(track):
    info=info_loader("https://storage.mds.yandex.net/download-info/{storageDir}/2?format=json",**track)
    info["path"]=info["path"].lstrip("/")
    h=md5("XGRlBW9FXlekgbPrRHuSiA{path}{s}".format_map(info).encode())
    info["md5"]=h.hexdigest()
    return "https://{host}/get-mp3/{md5}/{ts}/{path}".format_map(info)
def split_artists(all_artists):
    artists=[]
    composers=[]
    for a in all_artists:
        if a["composer"]:
            composers.append(a["name"])
        else:
            artists.append(a["name"])
    return ", ".join(artists or composers)
def download_track(track):
    global track_name
    track["artists"]=split_artists(track["artists"])
    name_mask="{} - {}".format(track["artists"],track["title"])
    track_name=name_mask.translate(forbidden_sym).rstrip(". ")
    track_name+=".mp3"
    if os.path.exists(track_name):
        return
    try:
        download_file(get_track_url(track),track_name)
    except:
        raise YmdlError
def parse_url(url):
    url_info=urllib.parse.urlsplit(url)
    if not (url_info.scheme in ("http","https") and url_info.netloc.startswith("music.yandex")):
        raise YmdlError
    pairs=url_info.path.strip("/").split("/")
    if len(pairs)%2!=0:
        what=pairs[-1]
        if what not in ["albums","tracks","similar"]:
            raise YmdlError
    else:
        what="albums"
    i=iter(pairs)
    info=dict(zip(i,i))
    info["what"]=what
    if what=="similar":
        raise YmdlError
    if "track" in info:
        download_track(info_loader("https://music.yandex.ru/handlers/track.jsx?track={track}",**info)["track"])
    else:
        raise YmdlError
def main(url):
    try:
        parse_url(url)
    except:
        return "YmdlWrongUrlError"
    else:
        return track_name
