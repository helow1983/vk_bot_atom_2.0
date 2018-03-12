import logging,os,urllib.request,urllib.parse,json,mimetypes,time
from urllib.error import URLError
from mutagen import id3,mp3
from hashlib import md5
class YmdlError(Exception):
    pass
class YmdlWrongUrlError(YmdlError,ValueError):
    pass
class Args:
    album_name=None
    also=False
    batch_file=None
    cover_id3_size=300
    cover_size=700
    genre=False
    m3u=False
    out="."
    quiet=True
    track_name=None
    volume_prefix='CD'
LINE='='*79
YM_URL='https://music.yandex.ru'
YM_TRACK_SRC_INFO=('https://storage.mds.yandex.net/download-info/{storageDir}/2?format=json')
YM_TRACK_INFO=YM_URL+'/handlers/track.jsx?track={track}'
YM_ALBUM_INFO=YM_URL+'/handlers/album.jsx?album={album}'
YM_ARTIST_INFO=YM_URL+'/handlers/artist.jsx?artist={artist}&what={what}'
FLD_COMPOSERS='composers'
FLD_TRACKNUM='trackNum'
FLD_VOLUMENUM='volumeNum'
FMT_TITLE='%t'
FMT_ARTIST='%a'
FMT_ALBUM='%A'
FMT_TRACKN='%n'
FMT_NTRACKS='%N'
FMT_YEAR='%y'
FMT_LABEL='%l'
DTN_SINGLE='%a - %t'
COVER_SIZES=[30,40,50,75,80,100,150,160,200,300,400,460,600,700,1000]
def size_to_str(byte_size):
    size=byte_size/1024/1024
    for s in ('MB','GB','TB'):
        if size<1024:
            break
        size/=1024
    return '{:.2f} {}'.format(size,s)
def time_to_str(ms):
    minutes,ms=divmod(ms,60000)
    seconds=ms//1000
    return '{}:{:02}'.format(minutes,seconds)
_FNAME_TRANS={ord('"'): "''"}
_FNAME_TRANS.update(str.maketrans('\\/*','--_','<>:|?'))
def filename(s):
    return s.translate(_FNAME_TRANS).rstrip('. ')
def make_extinf(track,file_path):
    return '#EXTINF:{},{} - {}\n{}\n'.format(track['durationMs']//1000,track['artists'],track['title'],file_path)
def save_m3u(extinfs,save_path):
    if not extinfs:
        return
    os.makedirs(save_path,exist_ok=True)
    with open(os.path.join(save_path,'play.m3u8'),'w',encoding='utf-8-sig') as f:
        f.write('#EXTM3U\n')
        f.writelines(extinfs)
def write_id3(mp3_file,track,cover=None):
    t=mp3.Open(mp3_file)
    if not t.tags:
        t.add_tags()
    album=track['albums'][0]
    t_add=t.tags.add
    t_add(id3.TIT2(encoding=3,text=track['title']))
    t_add(id3.TPE1(encoding=3,text=track['artists']))
    t_add(id3.TCOM(encoding=3,text=track[FLD_COMPOSERS]))
    t_add(id3.TALB(encoding=3,text=album['title']))
    if 'labels' in album:
        t_add(id3.TPUB(encoding=3,text=','.join(l['name'] for l in album['labels'])))
    if FLD_TRACKNUM in track:
        tnum='{}/{}'.format(track[FLD_TRACKNUM],album['trackCount'])
        t_add(id3.TRCK(encoding=3,text=tnum))
    if FLD_VOLUMENUM in album:
        t_add(id3.TPOS(encoding=3,text=str(album[FLD_VOLUMENUM])))
    if 'year' in album:
        t_add(id3.TDRC(encoding=3,text=str(album['year'])))
    if Args.genre:
        t_add(id3.TCON(encoding=3,text=album['genre'].title()))
    if cover:
        t_add(id3.APIC(encoding=3,desc='',mime=cover.mime,type=3,data=cover.data))
    t.tags.update_to_v23()
    t.save(v1=id3.ID3v1SaveOptions.CREATE,v2_version=3)
_DL_CHUNK_SIZE=128*1024
_DL_BAR_SIZE=40
_DL_PART_EXT='.part'
def download_file(url,save_as):
    file_dir,file_name=os.path.split(save_as)
    if os.path.exists(save_as):
        raise FileExistsError('{} already exists'.format(file_name))
    request=urllib.request.Request(url)
    file_part=save_as+_DL_PART_EXT
    if os.path.isfile(file_part):
        file_part_size=os.path.getsize(file_part)
        mode='ab'
        request.add_header('Range','bytes={}-'.format(file_part_size))
    else:
        file_part_size=0
        mode='wb'
    response=urllib.request.urlopen(request)
    file_size=file_part_size + int(response.getheader('Content-Length'))
    os.makedirs(file_dir,exist_ok=True)
    info=('\r[{:<' + str(_DL_BAR_SIZE) + '}] '
          '{:>6.1%} ({} / '+size_to_str(file_size)+')')
    with open(file_part,mode) as f:
        while True:
            chunk=response.read(_DL_CHUNK_SIZE)
            if not chunk:
                if not Args.quiet:
                    print()
                break
            file_part_size+=len(chunk)
            percent=file_part_size/file_size
            progressbar='#'*round(_DL_BAR_SIZE*percent)
            if not Args.quiet:
                print(info.format(progressbar,percent,size_to_str(file_part_size)),end='')
            f.write(chunk)
    os.rename(file_part,save_as)
class AlbumCover:
    def __init__(self,url):
        with urllib.request.urlopen(url) as r:
            self.data=r.read()
            self.mime=r.getheader('Content-Type')
        if self.mime=='image/jpeg':
            self.extension='.jpg'
        else:
            self.extension=mimetypes.guess_extension(self.mime)
    @classmethod
    def download(cls,uri,size):
        if size<=0:
            return None
        for n in COVER_SIZES:
            if size<=n:
                break
        try:
            return cls('https://'+uri.replace('%%','{0}x{0}'.format(n)))
        except URLError as e:
            logging.error('Can\'t download cover: %s',e)
            return None
    def save(self,path):
        try:
            os.makedirs(path,exist_ok=True)
            with open(os.path.join(path,'cover' + self.extension),'wb') as f:
                f.write(self.data)
        except OSError as e:
            logging.error('Can\'t save cover: %s',e)
def _info_js(template):
    def info_loader(**kwargs):
        with urllib.request.urlopen(template.format(**kwargs),timeout=6) as r:
            return json.loads(r.read().decode())
    return info_loader
track_src_info=_info_js(YM_TRACK_SRC_INFO)
track_info=_info_js(YM_TRACK_INFO)
album_info=_info_js(YM_ALBUM_INFO)
artist_info=_info_js(YM_ARTIST_INFO)
def get_track_url(track):
    info=track_src_info(**track)
    info['path']=info['path'].lstrip('/')
    h=md5('XGRlBW9FXlekgbPrRHuSiA{path}{s}'.format_map(info).encode())
    info['md5']=h.hexdigest()
    return 'https://{host}/get-mp3/{md5}/{ts}/{path}'.format_map(info)
def split_artists(all_artists):
    artists=[]
    composers=[]
    for a in all_artists:
        if a['composer']:
            composers.append(a['name'])
        else:
            artists.append(a['name'])
    return ','.join(artists or composers),','.join(composers)
def print_track_info(track):
    info='{} ({})'.format(track['title'],time_to_str(track['durationMs']))
    if FLD_TRACKNUM in track:
        album=track['albums'][0]
        info='[{}/{}] {}'.format(
            track[FLD_TRACKNUM],album['trackCount'],info)
    print(info)
    print('by',track['artists'])
def download_track(track,num,save_path=Args.out,name_mask=None,cover_id3=None):
    global track_name
    track['artists'],track[FLD_COMPOSERS]=split_artists(track['artists'])
    if 'version' in track:
        track['title']='{title} ({version})'.format_map(track)
    album=track['albums'][0]
    if 'version' in album:
        album['title']='{title} ({version})'.format_map(album)
    if not name_mask:
        name_mask=Args.track_name or DTN_SINGLE
    fmt={}
    fmt[FMT_TITLE]=track['title']
    fmt[FMT_ARTIST]=track['artists']
    fmt[FMT_ALBUM]=album['title']
    if FLD_TRACKNUM in track:
        fill=max(len(str(album['trackCount'])),2)
        trackn=str(track[FLD_TRACKNUM]).zfill(fill)
    else:
        trackn=''
    fmt[FMT_TRACKN]=trackn
    fmt[FMT_NTRACKS]=str(album['trackCount'])
    fmt[FMT_YEAR]=str(album.get('year',''))
    fmt[FMT_LABEL]=','.join(l['name'] for l in album.get('labels',[]))
    for f,t in fmt.items():
        name_mask=name_mask.replace(f,t)
    track_name=str(num)+filename(name_mask)
    if not track_name.lower().endswith('.mp3'):
        track_name+='.mp3'
    track_path=os.path.join(save_path,track_name)
    if not Args.quiet:
        print_track_info(track)
    try:
        download_file(get_track_url(track),track_path,num)
    except FileExistsError as e:
        logging.info(e)
    except URLError as e:
        logging.error('Can\'t download track: %s',e)
    else:
        if not cover_id3 and 'coverUri' in album:
            cover_id3=AlbumCover.download(album['coverUri'],Args.cover_id3_size)
        try:
            write_id3(track_path,track,cover_id3)
        except OSError as e:
            logging.error('Can\'t write ID3: %s',e)
    return make_extinf(track,track_name)
def parse_url(url,num):
    url_info=urllib.parse.urlsplit(url)
    if not (url_info.scheme in ('http','https') and url_info.netloc.startswith('music.yandex')):
        raise YmdlWrongUrlError
    pairs=url_info.path.strip('/').split('/')
    if len(pairs)%2!=0:
        what=pairs[-1]
        if what not in ['albums','tracks','similar']:
            raise YmdlWrongUrlError
    else:
        what='albums'
    i=iter(pairs)
    info=dict(zip(i,i))
    info['what']=what
    if what=='similar':
        raise YmdlError((
            'URL {} points to artists similar to {}. '
            'Please select one and give appropriate URL.').format(url,artist_info(**info)['artist']['name']))
    if 'track' in info:
        download_track(track_info(**info)['track'])
    else:
        raise YmdlWrongUrlError
def main(url,num):
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    if Args.quiet:
        logging.disable(logging.CRITICAL)
    while True:
        try:
            parse_url(url,num)
        except Exception as a:
            print(a)
            return "YmdlWrongUrlError"
        else:
            return track_name
