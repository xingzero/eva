import re, sys, urllib.parse, requests, json
from pyquery import PyQuery as pq
from time import time

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "麦田影院（优）"

    def init(self, extend):
#        raw_host = extend.get('host', 'https://www.mtyy1.com') if extend else 'https://www.mtyy1.com'
        raw_host = extend.get('host', 'https://www.mtyy3.com') if extend else 'https://www.mtyy3.com'
        self.host = ('https://' + raw_host if not raw_host.startswith('http') else raw_host).rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        self._cache = {}

    def _get_cache(self, key, ttl=600):
        data, expire = self._cache.get(key, (None, 0))
        return data if time() < expire else None

    def _set_cache(self, key, data, ttl=600):
        self._cache[key] = (data, time() + ttl)

    def fetch(self, url, retry=2):
        for i in range(retry):
            try:
                rsp = self.session.get(url, timeout=10)
                if rsp.status_code == 200:
                    return rsp
            except Exception:
                pass
        return None

    def _parse_video_list(self, doc):
        return [{'vod_id': a.attr('href'), 'vod_name': a.attr('title') or item.find('.time-title').text().strip(),
                 'vod_pic': a.find('img').attr('data-src') or a.find('img').attr('src') or '',
                 'vod_remarks': item.find('.public-list-prb').text().strip() or item.find('.public-prt').text().strip()}
                for item in doc('.public-list-box').items()
                if (a := item.find('.public-list-exp')) and a.attr('href')]

    def homeContent(self, filter):
        if (cached := self._get_cache('home_content')): return cached
        result = {'class': []}
        if rsp := self.fetch(self.host):
            doc = pq(rsp.text)
            for li in doc('.head-nav ul li').items():
                if (a := li.find('a')) and (href := a.attr('href')) and href != 'javascript:' and (name := a.text().strip()) != '更多':
                    if m := re.search(r'/vodtype/(\d+)\.html', href):
                        result['class'].append({'type_name': name, 'type_id': m.group(1)})
        self._set_cache('home_content', result, 1800)
        return result

    def homeVideoContent(self):
        if (cached := self._get_cache('home_video')): return cached
        result = {'list': []}
        if rsp := self.fetch(self.host):
            doc = pq(rsp.text)
            videos = [{'vod_id': link.attr('href'), 'vod_name': slide.find('.slide-info-title').text().strip(),
                       'vod_pic': slide.find('.slid-e-bj').attr('data-background') or '',
                       'vod_remarks': slide.find('.slid-e-type').text().strip()}
                      for slide in doc('.slid-e-list .slid-e-list-box').items()
                      if (link := slide.find('a[href^="/vod/"]')) and link.attr('href')]
            result['list'] = (videos or self._parse_video_list(doc))[:12]
        self._set_cache('home_video', result, 600)
        return result

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/vodshow/{tid}--------{pg}---.html"
        result = {'list': [], 'page': pg, 'pagecount': 1, 'limit': 20, 'total': 1}
        if rsp := self.fetch(url):
            doc = pq(rsp.text)
            result['list'] = self._parse_video_list(doc)
            if page_info := doc('.pages .page-info'):
                max_page = max((int(link.text().strip()) for link in page_info.find('a').items() if link.text().strip().isdigit()), default=1)
                result['pagecount'], result['total'] = max_page, max_page * 20
        return result

    def detailContent(self, array):
        if not array or not array[0]: return {}
        vod_id = array[0]
        if cached := self._get_cache(f'detail_{vod_id}', 3600): return cached
        url = self.host + vod_id if vod_id.startswith('/') else self.host + '/' + vod_id
        result = {}
        if rsp := self.fetch(url):
            doc = pq(rsp.text)
            vod_name = doc('h3.slide-info-title').text().strip() or doc('meta[property="og:title"]').attr('content') or ''
            vod_pic = doc('.detail-pic img').attr('data-src') or doc('.detail-pic img').attr('src') or ''
            vod_content = doc('#height_limit').text().strip() or doc('.slide-info.hide2').text().strip() or ''
            vod_remarks = doc('.slide-info-remarks').text().strip() or ''
            play_from, play_urls = [], []
            tabs, boxes = doc('.anthology-tab a'), doc('.anthology-list .anthology-list-box')
            if tabs and boxes:
                for i, tab in enumerate(tabs.items()):
                    if from_name := tab.text().strip():
                        play_from.append(from_name)
                        eps = [f"{ep.text().strip()}${ep.attr('href')}" for ep in boxes.eq(i).find('li a').items() if ep.text().strip() and ep.attr('href')]
                        play_urls.append('#'.join(eps))
            elif eps := [f"{ep.text().strip()}${ep.attr('href')}" for ep in doc('.anthology-list-play a').items() if ep.text().strip() and ep.attr('href')]:
                play_from, play_urls = ['默认线路'], ['#'.join(eps)]
            vod = {'vod_id': vod_id, 'vod_name': vod_name, 'vod_pic': vod_pic, 'vod_remarks': vod_remarks,
                   'vod_content': vod_content, 'vod_play_from': '$$$'.join(play_from), 'vod_play_url': '$$$'.join(play_urls)}
            result['list'] = [vod]
            self._set_cache(f'detail_{vod_id}', result, 3600)
        return result

    def searchContent(self, key, quick, pg='1'):
        url = f"{self.host}/vodsearch/{urllib.parse.quote(key)}----------{pg}---.html"
        result = {'list': []}
        if rsp := self.fetch(url):
            result['list'] = self._parse_video_list(pq(rsp.text))
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 1, "playUrl": "", "url": "", "header": {}}
        if not id: return result
        play_url = id if id.startswith('http') else (self.host + id if id.startswith('/') else self.host + '/' + id)
        if rsp := self.fetch(play_url):
            html = rsp.text
            # 优先匹配 .m3u8 或 .mp4 链接
            if m := re.search(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*', html):
                result["url"] = m.group(0)
                result["header"] = {'Referer': play_url, 'User-Agent': self.session.headers['User-Agent']}
                return result
            # 尝试从 player_data 中提取 url
            if m := re.search(r'var\s+player_data\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\})', html, re.DOTALL):
                try:
                    data = json.loads(m.group(1).replace('\\/', '/'))
                    if url := data.get('url', ''):
                        result["url"] = url
                        result["header"] = {'Referer': play_url, 'User-Agent': self.session.headers['User-Agent']}
                except:
                    pass
        return result

    def isVideoFormat(self, url): return False
    def manualVideoCheck(self): return False
    def localProxy(self, param): return {}