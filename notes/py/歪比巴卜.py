# coding=utf-8
"""
目标站: 歪比巴卜
首页: https://wbbb1.com
"""
import re
import sys
import time
import json
import base64
import hashlib
import urllib.parse
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://wbbb1.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Referer": self.host,
            "pics": "1"
        }

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "动漫"},
            {"type_id": "4", "type_name": "综艺"}
            
        ]
        # 从页面提取的完整筛选配置
        common_filters = [
            {
                "key": "class",
                "name": "类型",
                "value": [
                    {"n": "全部", "v": "", "s": 1},
                    {"n": "喜剧", "v": "喜剧"},
                    {"n": "爱情", "v": "爱情"},
                    {"n": "恐怖", "v": "恐怖"},
                    {"n": "动作", "v": "动作"},
                    {"n": "科幻", "v": "科幻"},
                    {"n": "剧情", "v": "剧情"},
                    {"n": "战争", "v": "战争"},
                    {"n": "警匪", "v": "警匪"},
                    {"n": "犯罪", "v": "犯罪"},
                    {"n": "动画", "v": "动画"},
                    {"n": "奇幻", "v": "奇幻"},
                    {"n": "武侠", "v": "武侠"},
                    {"n": "冒险", "v": "冒险"}
                ]
            },
            {
                "key": "area",
                "name": "地区",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "大陆", "v": "大陆"},
                    {"n": "港台", "v": "港台"},
                    {"n": "美国", "v": "美国"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "印度", "v": "印度"},
                    {"n": "法国", "v": "法国"},
                    {"n": "英国", "v": "英国"}
                ]
            },
            {
                "key": "lang",
                "name": "语言",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "国语", "v": "国语"},
                    {"n": "粤语", "v": "粤语"},
                    {"n": "韩语", "v": "韩语"},
                    {"n": "日语", "v": "日语"},
                    {"n": "英语", "v": "英语"},
                    {"n": "泰语", "v": "泰语"}
                ]
            },
            {
                "key": "year",
                "name": "年份",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"},
                    {"n": "2014", "v": "2014"},
                    {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"}
                ]
            },
            {
                "key": "letter",
                "name": "字母",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "A", "v": "A"},
                    {"n": "B", "v": "B"},
                    {"n": "C", "v": "C"},
                    {"n": "D", "v": "D"},
                    {"n": "E", "v": "E"},
                    {"n": "F", "v": "F"},
                    {"n": "G", "v": "G"},
                    {"n": "H", "v": "H"},
                    {"n": "I", "v": "I"},
                    {"n": "J", "v": "J"},
                    {"n": "K", "v": "K"},
                    {"n": "L", "v": "L"},
                    {"n": "M", "v": "M"},
                    {"n": "N", "v": "N"},
                    {"n": "O", "v": "O"},
                    {"n": "P", "v": "P"},
                    {"n": "Q", "v": "Q"},
                    {"n": "R", "v": "R"},
                    {"n": "S", "v": "S"},
                    {"n": "T", "v": "T"},
                    {"n": "U", "v": "U"},
                    {"n": "V", "v": "V"},
                    {"n": "W", "v": "W"},
                    {"n": "X", "v": "X"},
                    {"n": "Y", "v": "Y"},
                    {"n": "Z", "v": "Z"},
                    {"n": "0-9", "v": "0-9"}
                ]
            }
        ]
        filters = {"1": common_filters, "2": common_filters, "3": common_filters}
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        res = self.fetch(self.host, headers=self.headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        videos = []
        items = soup.select('.module-poster-item')
        for item in items:
            title = item.get('title', '')
            href = item.get('href', '')
            match = re.search(r'/detail/(\d+)\.html', href)
            if not match: continue
            vod_id = match.group(1)
            pic_el = item.select_one('.lazy')
            pic = pic_el.get('data-original', '') if pic_el else ''
            remark_el = item.select_one('.module-item-note')
            remark = remark_el.text.strip() if remark_el else ''
            videos.append({
                "vod_id": vod_id, "vod_name": title,
                "vod_pic": urllib.parse.urljoin(self.host, pic) if pic else "",
                "vod_remarks": remark
            })
        return {"list": videos}

    def categoryContent(self, tid, pg, filter, extend):
        route = [""] * 12
        route[0] = str(tid)
        route[1] = extend.get('area', '')
        route[3] = extend.get('class', '')
        route[8] = str(pg)
        
        url = f"{self.host}/show/{'-'.join(route)}.html"
        res = self.fetch(url, headers=self.headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        videos = []
        items = soup.select('.module-item')
        for item in items:
            title_el = item.select_one('.module-poster-item-title')
            title = item.get('title') or (title_el.text.strip() if title_el else '')
            href = item.get('href', '')
            match = re.search(r'/detail/(\d+)\.html', href)
            if not match: continue
            vod_id = match.group(1)
            pic_el = item.select_one('.lazy')
            pic = pic_el.get('data-original', '') if pic_el else ''
            remark_el = item.select_one('.module-item-note')
            remark = remark_el.text.strip() if remark_el else ''
            videos.append({
                "vod_id": vod_id, "vod_name": title,
                "vod_pic": urllib.parse.urljoin(self.host, pic) if pic else "",
                "vod_remarks": remark
            })
            
        pagecount = int(pg)
        last_page_a = soup.select('a.page-link')
        for a in last_page_a:
            if a.text == '尾页':
                m = re.search(r'---(\d+)---', a.get('href', ''))
                if m: pagecount = int(m.group(1))
                break
        if not videos: pagecount = 0
        return {"list": videos, "page": int(pg), "pagecount": pagecount, "limit": 40, "total": 9999}

    def detailContent(self, ids):
        vod_id = ids[0]
        url = f"{self.host}/detail/{vod_id}.html"
        res = self.fetch(url, headers=self.headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        h1 = soup.select_one('h1')
        desc_el = soup.select_one('.show-desc p')
        vod = {
            "vod_id": vod_id, "vod_name": h1.text.strip() if h1 else "",
            "vod_pic": "", "vod_content": desc_el.text.strip() if desc_el else "",
            "vod_play_from": "", "vod_play_url": ""
        }
        
        tabs = soup.select('.module-tab-items-box .tab-item')
        play_froms = [tab.get('data-dropdown-value', tab.text.strip()) for tab in tabs]
        vod["vod_play_from"] = "$$$".join(play_froms)
        
        lists = soup.select('.module-play-list')
        play_urls = []
        for pl in lists:
            a_tags = pl.select('a')
            urls = []
            for a in a_tags:
                title = a.text.strip()
                href = a.get('href', '')
                urls.append(f"{title}${self.host}{href}")
            play_urls.append("#".join(urls))
        vod["vod_play_url"] = "$$$".join(play_urls)
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/search/{urllib.parse.quote(key)}----------{pg}---.html"
        res = self.fetch(url, headers=self.headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        videos = []
        items = soup.select('.module-search-item, .module-item')
        for item in items:
            a_tag = item.select_one('.module-poster-item') or item.select_one('a')
            if not a_tag: continue
            href = a_tag.get('href', '')
            match = re.search(r'/detail/(\d+)\.html', href)
            if not match: continue
            vod_id = match.group(1)
            title = a_tag.get('title', '')
            pic_el = item.select_one('.lazy')
            pic = pic_el.get('data-original', '') if pic_el else ''
            videos.append({"vod_id": vod_id, "vod_name": title, "vod_pic": urllib.parse.urljoin(self.host, pic) if pic else ""})
        return {"list": videos, "page": int(pg), "pagecount": 1}

    # ================== 核心解密与签名算法 ==================
    def get_md5(self, text):
        return hashlib.md5(str(text).encode('utf-8')).hexdigest()

    def rc4(self, key, data):
        S = list(range(256))
        j = 0
        key_bytes = key.encode('utf-8')
        for i in range(256):
            j = (j + S[i] + key_bytes[i % len(key_bytes)]) % 256
            S[i], S[j] = S[j], S[i]
        i = j = 0
        res = bytearray()
        data_bytes = data.encode('utf-8')
        for char in data_bytes:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            res.append(char ^ S[(S[i] + S[j]) % 256])
        return res

    def enplay(self, key, data):
        rc4_data = self.rc4(key, data)
        return base64.b64encode(rc4_data).decode('utf-8')

    def decrypt_m3u8(self, encrypted_url_b64):
        key = b"OddfJktEbGu7gCv9"
        iv  = b"okjutU3RjGpWqB8Z"
        encrypted_data = base64.b64decode(encrypted_url_b64)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(encrypted_data)
        return unpad(decrypted_data, AES.block_size).decode('utf-8')
    # ======================================================

    def playerContent(self, flag, id, vipFlags):
        """完全避开解析坑，使用最纯净的 URL 盲发请求"""
        try:
            res = self.fetch(id, headers=self.headers)
            
            iframe_src = ""
            url_param = ""
            host = "xn--qvr2v.850088.xyz" 
            
            # 直接从页面抠取 iframe 的真实播放链接
            iframe_match = re.search(r'<iframe[^>]*src=["\'](https?://[^"\']+/player/\?url=[^"\']+)["\']', res.text, re.I)
            if iframe_match:
                iframe_src = iframe_match.group(1).replace('&amp;', '&')
                parsed = urllib.parse.urlparse(iframe_src)
                host = parsed.netloc
                qs = urllib.parse.parse_qs(parsed.query)
                url_param = qs.get('url', [''])[0]
            else:
                # 备选：从 JSON 里提取
                match = re.search(r'player_aaaa\s*=\s*(\{.*?\})[;<]', res.text)
                if match:
                    try:
                        player_data = json.loads(match.group(1))
                        url_param = player_data.get('url', '')
                        iframe_src = f"https://{host}/player/?url={url_param}"
                    except:
                        pass
                        
            if not url_param:
                return {"parse": 1, "url": id, "header": self.headers}
                
            if url_param.endswith('.m3u8') or url_param.endswith('.mp4'):
                return {"parse": 0, "url": url_param, "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.host, "pics": "1"}}

            # --- 本地直链秒算 ---
            try:
                salt = "stray"
                t = str(int(time.time()))
                
                url_md5 = self.get_md5(url_param)
                rc4_key = (url_md5 + " P")[-22:]
                
                key_val = self.enplay(rc4_key, self.get_md5(url_param + salt))
                vkey_val = self.enplay(rc4_key, t + self.get_md5(rc4_key + salt))
                ckey_val = self.enplay(rc4_key, self.get_md5(host + salt))
                
                api_url = f"https://{host}/player/api.php"
                post_data = {
                    "url": url_param,  # 【核心修正】：只发干净的密文，不带 &next
                    "key": key_val,
                    "vkey": vkey_val,
                    "ckey": ckey_val
                }
                
                headers = {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": iframe_src,
                    "Origin": f"https://{host}",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest"
                }
                
                api_res = self.post(api_url, data=post_data, headers=headers)
                
                if api_res.status_code == 200:
                    api_json = api_res.json()
                    encrypted_url_b64 = api_json.get("url", "")
                    if encrypted_url_b64:
                        real_play_url = self.decrypt_m3u8(encrypted_url_b64)
                        return {
                            "parse": 0, 
                            "url": real_play_url, 
                            "header": {
                                "User-Agent": headers["User-Agent"],
                                "Referer": f"https://{host}/",
                                "pics": "1"
                            }
                        }
            except Exception:
                pass
                
            # 万一环境缺少 Crypto 等库引发异常，将轻量级地址丢给 WebView
            return {
                "parse": 1, 
                "url": iframe_src, 
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.host
                }
            }
            
        except Exception:
            return {"parse": 1, "url": id, "header": self.headers}
