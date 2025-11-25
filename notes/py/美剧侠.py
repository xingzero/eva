# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。

from Crypto.Cipher import AES
from base.spider import Spider
from Crypto.Util.Padding import unpad
import re,sys,time,json,urllib3,hashlib,binascii
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.append('..')

class Spider(Spider):
    headers,host,versionCode = {
        'User-Agent': "okhttp/3.14.9",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip"
    }, 'http://122.114.11.127:8808','1030'

    def homeContent(self, filter):
        if not self.host: return None
        payload = self.payload('App.Vod.Main_type')
        response = self.post(self.host, data=payload, headers=self.headers, verify=False).json()
        classes = []
        for i in response['data']:
            if isinstance(i,dict):
                classes.append({'type_id': i['list_id'], 'type_name': i['list_name']})
        return {'class': classes}

    def homeVideoContent(self):
        payload = self.payload('App.Vod.HomeVideos')
        response = self.post(self.host, data=payload, headers=self.headers, verify=False).json()
        data = self.decrypt(response['data'])
        videos = self.videos(data)
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        payload = self.payload({
            'service': "App.Vod.Videos",
            'list_id': tid,
            'type': "全部",
            'year': "全部",
            'area': "全部",
            'language': "全部",
            'order': "time",
            'page': pg,
            'perpage': "24",
        })
        response = self.post(self.host, data=payload, headers=self.headers, verify=False).json()
        data = self.decrypt(response['data'])
        videos = self.videos(data)
        return {'list': videos, 'page': pg}

    def searchContent(self, key, quick, pg='1'):
        payload = self.payload({
            'service': "App.Vod.Search",
            'search': key,
            'page': pg,
            'perpage': "24"
        })
        response = self.post(self.host, data=payload, headers=self.headers, verify=False).json()
        data = self.decrypt(response['data'])
        videos = self.videos(data)
        return {'list': videos, 'page': pg}

    def detailContent(self, ids):
        payload = self.payload({
            'service': "App.Vod.Video",
            'id': ids[0]
        })
        response = self.post(self.host, data=payload, headers=self.headers, verify=False).json()
        player_vod = {}
        for i in response['data']:
            if isinstance(i, dict) and i['type'] == 'player':
                player_vod = i['player_vod']
        if not player_vod: return None
        play_from, play_urls = [], []
        for j in player_vod['vod_play']:
            play_from.append(j['title'])
            play_url = []
            for k in j.get('players', []):
                play_url.append(f"{k['title']}${k['url']}")
            play_url.reverse()
            play_urls.append('#'.join(play_url))
        video = {
            'vod_id': player_vod['vod_id'],
            'vod_name': player_vod['vod_name'],
            'vod_pic': player_vod['vod_pic'],
            'vod_remarks': player_vod['vod_title'],
            'vod_actor': player_vod['vod_actor'],
            'vod_content': player_vod['vod_content'],
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_urls)
        }
        return {'list': [video]}

    def playerContent(self, flag, id, vipflags):
        jx, parse, noparse, ua, url = 0, 0, 0, 'com.jubaotaige.jubaotaigeapp/2.3.2 (Linux;Android 12) ExoPlayerLib/2.14.2', ''
        if 'nkvod.com' in id:
            noparse = 1
        elif 'url=' in id:
            try:
                response = self.fetch(id, headers=self.headers, verify=False).json()
                url = response.get('url', '')
                if not url.startswith('http'):
                    noparse = 1
            except Exception as e:
                print(f"请求异常: {e}")
                noparse = 1
        else:
            url = id
        if noparse == 1:
            ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
            if 'url=' in id:
                url = id.split('url=', 1)[1]
            else:
                url = id
            if re.match(r'https?:\/\/.*\.(iqiyi|youku|v.qq|mgtv)\.com', url):
                jx = 1
            elif 'nkvod.com' in url:
                parse = 1
        return {'jx': jx, 'parse': parse, 'url': url, 'header': {'User-Agent': ua}}

    def payload(self, data):
        timestamp = int(time.time() * 1000)
        md5 = self.md5(8 * timestamp - 12)
        if isinstance(data, dict):
            sign_data = self.md5(f"Api_FeiFeiCms{data['service']}{self.versionCode}{timestamp}{md5}")
            data.update({
                'versionCode': self.versionCode,
                'time': timestamp,
                'md5': md5,
                'sign': sign_data
            })
            payload = data
        else:
            sign_data = self.md5(f'Api_FeiFeiCms{data}{self.versionCode}{timestamp}{md5}')
            payload = {
                'service': data,
                'versionCode': self.versionCode,
                'time': timestamp,
                'md5': md5,
                'sign': sign_data
            }
        return payload

    def videos(self,data):
        try:
            data = json.loads(data)
            videos = []
            for i in data:
                if isinstance(i, dict):
                    for j in i.get('videos', []):
                        videos.append({
                            'vod_id': j['vod_id'],
                            'vod_name': j['vod_name'],
                            'vod_pic': j['vod_pic'],
                            'vod_remarks': j['vod_title']
                        })
        except Exception:
            videos = []
        return videos

    def decrypt(self,data, key='', iv=''):
        try:
            if not(key and iv):
                key, iv = '58ae78ab03bfeefb', '68e3d872b480c14f'
            encrypted_data = binascii.unhexlify(data)
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            return decrypted_data.decode('utf-8')
        except Exception:
            return None

    def md5(self, data):
        md5_hash = hashlib.md5()
        if isinstance(data, int): data = str(data)
        md5_hash.update(data.encode('utf-8'))
        return md5_hash.hexdigest()

    def init(self, extend=''):
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass