import logging,os,urllib.request,urllib.parse,json
from urllib.error import URLError
from mutagen import id3,mp3
from hashlib import md5
class YmdlError(Exception):
    pass
class YmdlWrongUrlError(YmdlError,ValueError):
    pass
class Args:
    genre=False
    out="."
    track_name=None
YM_URL="https://music.yandex.ru"
YM_TRACK_SRC_INFO=("https://storage.mds.yandex.net/download-info/{storageDir}/2?format=json")
YM_TRACK_INFO=YM_URL+"/handlers/track.jsx?track={track}"
YM_ARTIST_INFO=YM_URL+"/handlers/artist.jsx?artist={artist}&what={what}"
FLD_COMPOSERS="composers"
FLD_TRACKNUM="trackNum"
FLD_VOLUMENUM="volumeNum"
FMT_TITLE="%t"
FMT_ARTIST="%a"
FMT_ALBUM="%A"
FMT_TRACKN="%n"
FMT_NTRACKS="%N"
FMT_YEAR="%y"
FMT_LABEL="%l"
DTN_SINGLE="%a - %t"
_FNAME_TRANS={ord('"'): "''"}
_FNAME_TRANS.update(str.maketrans("\\/*","--_","<>:|?"))
def size_to_str(byte_size):
    size=byte_size/1024/1024
    for s in ("MB","GB","TB"):
        if size<1024:
            break
        size/=1024
    return "{:.2f} {}".format(size,s)
def filename(s):
    return s.translate(_FNAME_TRANS).rstrip(". ")
def make_extinf(track,file_path):
    return "#EXTINF:{},{} - {}\n{}\n".format(track["durationMs"]//1000,track["artists"],track["title"],file_path)
def write_id3(mp3_file,track,cover=None):
    t=mp3.Open(mp3_file)
    if not t.tags:
        t.add_tags()
    album=track["albums"][0]
    t_add=t.tags.add
    t_add(id3.TIT2(encoding=3,text=track["title"]))
    t_add(id3.TPE1(encoding=3,text=track["artists"]))
    t_add(id3.TCOM(encoding=3,text=track[FLD_COMPOSERS]))
    t_add(id3.TALB(encoding=3,text=album["title"]))
    if "labels" in album:
        t_add(id3.TPUB(encoding=3,text=",".join(l["name"] for l in album["labels"])))
    if FLD_TRACKNUM in track:
        tnum="{}/{}".format(track[FLD_TRACKNUM],album["trackCount"])
        t_add(id3.TRCK(encoding=3,text=tnum))
    if FLD_VOLUMENUM in album:
        t_add(id3.TPOS(encoding=3,text=str(album[FLD_VOLUMENUM])))
    if "year" in album:
        t_add(id3.TDRC(encoding=3,text=str(album["year"])))
    if Args.genre:
        t_add(id3.TCON(encoding=3,text=album["genre"].title()))
    if cover:
        t_add(id3.APIC(encoding=3,desc="",mime=cover.mime,type=3,data=cover.data))
    t.tags.update_to_v23()
    t.save(v1=id3.ID3v1SaveOptions.CREATE,v2_version=3)
def download_file(url,save_as):
    file_dir,file_name=os.path.split(save_as)
    if os.path.exists(save_as):
        raise FileExistsError("{} already exists".format(file_name))
    request=urllib.request.Request(url)
    response=urllib.request.urlopen(request)
    os.makedirs(file_dir,exist_ok=True)
    info=("\r[{:< 40 }] "
          "{:>6.1%} ({} / "+size_to_str(0)+")")
    with open(save_as,"wb") as f:
        while True:
            chunk=response.read()
            if not chunk:
                break
            f.write(chunk)
def _info_js(template):
    def info_loader(**kwargs):
        with urllib.request.urlopen(template.format(**kwargs),timeout=6) as r:
            return json.loads(r.read().decode())
    return info_loader
track_src_info=_info_js(YM_TRACK_SRC_INFO)
track_info=_info_js(YM_TRACK_INFO)
artist_info=_info_js(YM_ARTIST_INFO)
def get_track_url(track):
    info=track_src_info(**track)
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
    return ",".join(artists or composers),",".join(composers)
def download_track(track,save_path=Args.out,name_mask=None):
    global track_name
    track["artists"],track[FLD_COMPOSERS]=split_artists(track["artists"])
    if "version" in track:
        track["title"]="{title} ({version})".format_map(track)
    album=track["albums"][0]
    if "version" in album:
        album["title"]="{title} ({version})".format_map(album)
    if not name_mask:
        name_mask=Args.track_name or DTN_SINGLE
    fmt={}
    fmt[FMT_TITLE]=track["title"]
    fmt[FMT_ARTIST]=track["artists"]
    fmt[FMT_ALBUM]=album["title"]
    if FLD_TRACKNUM in track:
        fill=max(len(str(album["trackCount"])),2)
        trackn=str(track[FLD_TRACKNUM]).zfill(fill)
    else:
        trackn=""
    fmt[FMT_TRACKN]=trackn
    fmt[FMT_NTRACKS]=str(album["trackCount"])
    fmt[FMT_YEAR]=str(album.get("year",""))
    fmt[FMT_LABEL]=",".join(l["name"] for l in album.get("labels",[]))
    for f,t in fmt.items():
        name_mask=name_mask.replace(f,t)
    track_name=filename(name_mask)
    if not track_name.lower().endswith(".mp3"):
        track_name+=".mp3"
    track_path=os.path.join(save_path,track_name)
    try:
        download_file(get_track_url(track),track_path)
    except FileExistsError as e:
        logging.info(e)
    except URLError as e:
        logging.error("Can\'t download track: %s",e)
    else:
        try:
            write_id3(track_path,track)
        except OSError as e:
            logging.error("Can\'t write ID3: %s",e)
    return make_extinf(track,track_name)
def parse_url(url):
    url_info=urllib.parse.urlsplit(url)
    if not (url_info.scheme in ("http","https") and url_info.netloc.startswith("music.yandex")):
        raise YmdlWrongUrlError
    pairs=url_info.path.strip("/").split("/")
    if len(pairs)%2!=0:
        what=pairs[-1]
        if what not in ["albums","tracks","similar"]:
            raise YmdlWrongUrlError
    else:
        what="albums"
    i=iter(pairs)
    info=dict(zip(i,i))
    info["what"]=what
    if what=="similar":
        raise YmdlError((
            "URL {} points to artists similar to {}. "
            "Please select one and give appropriate URL.").format(url,artist_info(**info)["artist"]["name"]))
    if "track" in info:
        download_track(track_info(**info)["track"])
    else:
        raise YmdlWrongUrlError
def main(url):
    logging.basicConfig(level=logging.INFO,format="%(levelname)s: %(message)s")
    logging.disable(logging.CRITICAL)
    while True:
        try:
            parse_url(url)
        except:
            return "YmdlWrongUrlError"
        else:
            return track_name
