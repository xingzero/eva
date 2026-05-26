# coding = utf-8
import re, json, requests, urllib.parse
from lxml import etree
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "nnyy"
        self.host = "https://nnyy.la"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/"
        }
        self.rc4_key = "i_love_you"
        self._log = print   # 恢复日志输出，可替换为自定义 logger

    def getName(self): return self.name
    def init(self, extend=""): pass

    def _get(self, url, encoding="utf-8"):
        headers = self.header.copy()
        parsed = urllib.parse.urlparse(url)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        self._log(f"[get] {url}")
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = encoding
        self._log(f"[status] {r.status_code}, len={len(r.text)}")
        return r.text

    def _rc4(self, hex_str):
        key = self.rc4_key
        data = bytes.fromhex(hex_str)
        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + ord(key[i % len(key)])) % 256
            S[i], S[j] = S[j], S[i]
        i = j = 0
        res = bytearray()
        for b in data:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            res.append(b ^ S[(S[i] + S[j]) % 256])
        return res.decode("utf-8")

    def _build_play_urls(self, html):
        lines = re.findall(r'<dt[^>]+data-sid="(\d+)"[^>]*>(.*?)</dt>', html)
        enc_map = {}
        for sid, nid, enc in re.findall(r'urlDictionary\[(\d+)\]\[(\d+)\]\s*=\s*"([^"]+)"', html):
            enc_map.setdefault(int(sid), {})[int(nid)] = enc
        from_list, url_list = [], []
        for sid_str, name in lines:
            sid = int(sid_str)
            if sid not in enc_map: continue
            ul_pat = re.compile(r'<ul[^>]*data-sid="'+str(sid)+r'"[^>]*>(.*?)</ul>', re.S)
            ul_match = ul_pat.search(html)
            items = []
            if ul_match:
                for li in re.finditer(r'<li[^>]*data-nid="(\d+)"[^>]*>(.*?)</li>', ul_match.group(1), re.S):
                    nid = int(li.group(1))
                    a_text = re.search(r'<a[^>]*>(.*?)</a>', li.group(2))
                    items.append((nid, a_text.group(1).strip() if a_text else str(nid)))
            else:
                items = [(nid, str(nid)) for nid in sorted(enc_map[sid].keys())]
            parts = []
            for nid, ep_name in items:
                enc = enc_map[sid].get(nid)
                if enc:
                    try:
                        real = self._rc4(enc)
                        parts.append(f"{ep_name}${real}")
                    except Exception as e:
                        self._log(f"[rc4] decrypt fail: {e}")
            if parts:
                from_list.append(name.strip())
                url_list.append("#".join(parts))
        return "$$$".join(from_list), "$$$".join(url_list)

    def homeContent(self, filter_arg):
        classes = [
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "电视剧", "type_id": "2"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "动漫", "type_id": "4"},
            {"type_name": "纪录片", "type_id": "6"},
        ]
        area_vals = [{"n": x, "v": x if x != "全部" else ""} for x in ["全部","大陆","香港","台湾","欧美","韩国","日本","法国","德国","意大利","西班牙","印度","泰国","其它"]]
        year_vals = [{"n": x, "v": x if x != "全部" else ""} for x in ["全部","2025","2024","2023","2022","2021","2020","2019","2018","2017","2016","更早"]]
        sort_vals = [{"n":"最新","v":"time"},{"n":"最热","v":"hits"},{"n":"评分","v":"score"}]
        genre_vals = [{"n": x, "v": x if x != "全部" else ""} for x in ["全部","喜剧","爱情","动作","科幻","奇幻","悬疑","犯罪","冒险","灾难","恐怖","惊悚","剧情","战争","历史","传记","歌舞","武侠","情色","西部","经典","动画","同性","网络电影"]]
        filters = {c["type_id"]: [{"key":"area","name":"地区","value":area_vals},{"key":"sort","name":"排序","value":sort_vals},{"key":"genre","name":"类型","value":genre_vals},{"key":"year","name":"年份","value":year_vals}] for c in classes}
        return {"class": classes, "filters": filters}

    def homeVideoContent(self): return {"list": []}

    def categoryContent(self, tid, pg, filter_arg, extend):
        videos = []
        try:
            segs = [""] * 12
            segs[0] = str(tid)
            if extend:
                if extend.get("area"): segs[1] = requests.utils.quote(extend["area"])
                if extend.get("sort") and extend["sort"] != "time": segs[2] = extend["sort"]
                if extend.get("genre"): segs[3] = requests.utils.quote(extend["genre"])
                if extend.get("year"): segs[11] = extend["year"]
            if int(pg) > 1: segs[8] = str(pg)
            url = self.host + "/vodshow/" + "-".join(segs) + ".html"
            html = self._get(url)
            root = etree.HTML(html)
            li_list = root.xpath('//div[contains(@class,"lists-content")]/ul/li')
            self._log(f"[category] found {len(li_list)} items")
            for li in li_list:
                try:
                    a = li.xpath('.//a[contains(@href,"/vodplay/")]')[0]
                    href = a.get("href", "")
                    vod_id = href
                    h2 = li.xpath('.//h2/a/text()')
                    vod_name = h2[0].strip() if h2 else ""
                    imgs = li.xpath('.//img/@data-src | .//img/@src')
                    vod_pic = imgs[0] if imgs else ""
                    if vod_pic and not vod_pic.startswith("http"):
                        if vod_pic.startswith("//"): vod_pic = "https:" + vod_pic
                        elif vod_pic.startswith("/"): vod_pic = self.host + vod_pic
                    note = li.xpath('.//div[contains(@class,"note")]/span/text()')
                    vod_remarks = note[0].strip() if note else ""
                    if vod_id and vod_name:
                        videos.append({"vod_id": vod_id, "vod_name": vod_name, "vod_pic": vod_pic, "vod_remarks": vod_remarks})
                except Exception as e:
                    self._log(f"[parse li] error: {e}")
                    continue
            pagecount = 999
        except Exception as e:
            self._log(f"[category] exception: {e}")
            pagecount = 1
        return {"list": videos, "page": int(pg), "pagecount": pagecount, "limit": 20, "total": pagecount * 20}

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            url = self.host + vod_id if not vod_id.startswith("http") else vod_id
            html = self._get(url)
            root = etree.HTML(html)
            title_node = root.xpath('//h2[contains(@class,"product-title")]//text() | //h1[contains(@class,"product-title")]//text()')
            name = "".join(title_node).strip() if title_node else ""
            imgs = root.xpath('//img[contains(@class,"thumb")]/@data-src | //img[contains(@class,"thumb")]/@src')
            pic = imgs[0] if imgs else ""
            if pic:
                if pic.startswith("//"): pic = "https:" + pic
                elif not pic.startswith("http") and pic.startswith("/"): pic = self.host + pic
            director = actor = area = year = desc = type_name = ""
            for div in root.xpath('//div[contains(@class,"product-excerpt")]'):
                text = (div.xpath('string(.)') or "").strip()
                if "导演：" in text: director = text.split("：")[1].strip()
                elif "主演：" in text: actor = text.split("：")[1].strip()
                elif "类型：" in text: type_name = text.split("：")[1].strip()
                elif "制片国家/地区：" in text: area = text.split("：")[1].strip()
                elif "剧情简介：" in text: desc = text.split("：")[1].strip()
            m = re.search(r'\((\d{4})\)', name)
            if m: year = m.group(1)
            play_from, play_url = self._build_play_urls(html)
            self._log(f"[detail] {name}, lines={len(play_from.split('$$$')) if play_from else 0}")
            vod = {
                "vod_id": vod_id, "vod_name": name, "vod_pic": pic,
                "vod_year": year, "vod_area": area, "vod_actor": actor,
                "vod_director": director, "vod_content": desc,
                "vod_play_from": play_from, "vod_play_url": play_url,
                "type_name": type_name
            }
            return {"list": [vod]}
        except Exception as e:
            self._log(f"[detail] error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        videos = []
        try:
            url = f"{self.host}/vodsearch/-------------.html?wd={requests.utils.quote(key)}"
            html = self._get(url)
            root = etree.HTML(html)
            for li in root.xpath('//div[contains(@class,"lists-content")]/ul/li'):
                try:
                    a = li.xpath('.//a[contains(@href,"/vodplay/")]')[0]
                    href = a.get("href", ""); vod_id = href
                    h2 = li.xpath('.//h2/a/text()'); vod_name = h2[0].strip() if h2 else ""
                    imgs = li.xpath('.//img/@data-src | .//img/@src'); vod_pic = imgs[0] if imgs else ""
                    if vod_pic and not vod_pic.startswith("http"):
                        if vod_pic.startswith("//"): vod_pic = "https:" + vod_pic
                        elif vod_pic.startswith("/"): vod_pic = self.host + vod_pic
                    note = li.xpath('.//div[contains(@class,"note")]/span/text()'); vod_remarks = note[0].strip() if note else ""
                    if vod_id and vod_name:
                        videos.append({"vod_id": vod_id, "vod_name": vod_name, "vod_pic": vod_pic, "vod_remarks": vod_remarks})
                except Exception as e: continue
        except Exception as e:
            self._log(f"[search] error: {e}")
        return {"list": videos, "page": int(pg), "pagecount": 1, "limit": len(videos), "total": len(videos)}

    def playerContent(self, flag, id, vipFlags):
        play_headers = {
            "User-Agent": self.header["User-Agent"],
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*"
        }
        return {"parse": 0, "playUrl": "", "url": id, "header": json.dumps(play_headers)}

    def localProxy(self, params): return None
    def destroy(self): pass