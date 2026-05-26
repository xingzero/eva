# coding = utf-8
#!/usr/bin/python
import re
import json
import requests
from lxml import etree
from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        self.name = "cupfox"
        self.host = "https://www.syxdldb.com"

        # Session复用
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
            'Referer': self.host
        })

    def getName(self):
        return self.name

    def init(self, extend=''):
        pass

    def homeContent(self, filter):
        """
        首页分类，只保留分类
        """
        return {
            "class": [
                {"type_name": "电影", "type_id": "1"},
                {"type_name": "电视剧", "type_id": "2"},
                {"type_name": "综艺", "type_id": "3"},
                {"type_name": "动漫", "type_id": "4"}
            ]
        }

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        """
        分类页面解析
        """
        videos = []
        seen = set()
        try:
            if int(pg) <= 1:
                url = f"{self.host}/frim/index{tid}.html"
            else:
                url = f"{self.host}/frim/index{tid}-{pg}.html"

            html = self.session.get(url, timeout=5).text
            root = etree.HTML(html)
            items = root.xpath('//div[contains(@class, "module-item")]')

            for item in items:
                link = item.xpath('.//a[@class="module-item-pic"]/@href')
                if not link:
                    continue
                href = link[0]
                match = re.search(r'/movie/index(\d+)\.html', href)
                if not match:
                    continue
                vod_id = match.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)

                vod_name = ''.join(item.xpath('.//a[@class="module-item-title"]/text()')).strip()
                pic = item.xpath('.//img/@data-src') or item.xpath('.//img/@src')
                vod_pic = pic[0] if pic else ""
                if vod_pic.startswith('//'):
                    vod_pic = 'https:' + vod_pic
                elif vod_pic.startswith('/'):
                    vod_pic = self.host + vod_pic

                vod_remarks = ''.join(item.xpath('.//div[@class="module-item-text"]/text()')).strip()

                videos.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })

        except Exception:
            pass

        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 9999,
            'limit': 24,
            'total': 999999
        }

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            url = f"{self.host}/movie/index{vod_id}.html"
    
            resp = self.session.get(url, timeout=5)
            resp.encoding = 'utf-8'
            html = resp.text
            root = etree.HTML(html)
    
            # ===== 基本信息 =====
            vod_name = ''.join(root.xpath('//h1[@class="page-title"]/text()')).strip()
    
            # ===== 封面 =====
            vod_pic = ''
            pic = root.xpath('//div[contains(@class,"module-item-pic")]//img/@data-src')
            if not pic:
                pic = root.xpath('//div[contains(@class,"module-item-pic")]//img/@src')
            if pic:
                vod_pic = pic[0]
                if vod_pic.startswith('//'):
                    vod_pic = 'https:' + vod_pic
                elif vod_pic.startswith('/'):
                    vod_pic = self.host + vod_pic
    
            # ===== 分类 / 年份 / 地区 =====
            vod_type = ''
            vod_year = ''
            vod_area = ''
    
            type_el = root.xpath('//div[@class="video-info-aux"]/a[1]/text()')
            if type_el:
                vod_type = type_el[0].strip()
    
            year_el = root.xpath('//div[@class="video-info-aux"]//a[contains(@href,"year")]//text()')
            if year_el:
                vod_year = ''.join(year_el).strip()
    
            area_el = root.xpath('//div[@class="video-info-aux"]//a[contains(@href,"area")]//text()')
            if area_el:
                vod_area = ''.join(area_el).strip()
    
            # ===== 导演 / 主演（增强版，兼容文本+链接）=====
            def get_text_by_label(label):
                nodes = root.xpath(f'//div[@class="video-info-items"][.//span[contains(text(),"{label}")]]//div//text()')
                return ''.join([n.strip() for n in nodes if n.strip()])
    
            vod_director = get_text_by_label("导演")
            vod_actor = get_text_by_label("主演")
    
            # ===== 简介（双保险）=====
            vod_content = ''
    
            content = root.xpath('//div[contains(@class,"video-info-content")]//text()')
            if content:
                vod_content = ''.join([c.strip() for c in content if c.strip()])
    
            # fallback：meta
            if not vod_content:
                meta_desc = root.xpath('//meta[@property="og:description"]/@content')
                if meta_desc:
                    vod_content = meta_desc[0].strip()
    
            # ===== 播放列表（保持你原逻辑）=====
            line_names = root.xpath('//span[@data-dropdown-value]/text()')
            lines = []
            for n in line_names:
                n = n.strip()
                if n and n not in lines:
                    lines.append(n)
    
            if not lines:
                lines = ["默认线路"]
    
            containers = root.xpath('//div[contains(@class,"module-player-list")]')
    
            play_from = []
            play_urls = []
    
            for i, c in enumerate(containers):
                line = lines[i] if i < len(lines) else f"线路{i+1}"
    
                lis = c.xpath('.//li')
                episodes = []
    
                for li in lis:
                    a = li.xpath('.//a')
                    if not a:
                        continue
    
                    href = a[0].get('href')
                    title = a[0].get('title') or a[0].text or ''
    
                    if href and not href.startswith('http'):
                        href = self.host + href
    
                    if title and href:
                        episodes.append(f"{title}${href}")
    
                if episodes:
                    play_from.append(line)
                    play_urls.append('#'.join(episodes))
    
            vod_play_from = "$$$".join(play_from)
            vod_play_url = "$$$".join(play_urls)
    
            return {
                "list": [{
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_type": vod_type,
                    "vod_year": vod_year,
                    "vod_area": vod_area,
                    "vod_actor": vod_actor,
                    "vod_director": vod_director,
                    "vod_content": vod_content,
                    "vod_play_from": vod_play_from,
                    "vod_play_url": vod_play_url
                }]
            }
    
        except Exception as e:
            print("detailContent error:", e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            html = self.session.get(id, timeout=5).text
            match = re.search(r'var now=["\']([^"\']+\.m3u8[^"\']*)["\']', html)
            if match:
                play_url = match.group(1)
            else:
                match = re.search(r'var now=["\']([^"\']+)["\']', html)
                play_url = match.group(1) if match else ""
            return {
                "parse": 0,
                "playUrl": "",
                "url": play_url,
                "header": json.dumps({
                    'User-Agent': self.session.headers['User-Agent'],
                    'Referer': self.host
                })
            }
        except Exception:
            return {"parse": 0, "playUrl": "", "url": ""}

    def searchContent(self, key, quick, pg='1'):
        videos = []
        seen = set()
        try:
            url = f"{self.host}/search.php"
            params = {'searchword': key, 'page': pg}
            html = self.session.get(url, params=params, timeout=5).text
            root = etree.HTML(html)
    
            # ❗关键：搜索页结构
            items = root.xpath('//div[contains(@class,"module-search-item")]')
    
            for item in items:
                link = item.xpath('.//a[contains(@class,"module-item-pic")]/@href')
                if not link:
                    continue
    
                href = link[0]
                match = re.search(r'/movie/index(\d+)\.html', href)
                if not match:
                    continue
    
                vod_id = match.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
    
                # ✅ 标题（真正位置）
                h3 = item.xpath('.//h3/a')
                vod_name = ''.join(h3[0].xpath('.//text()')).strip() if h3 else ''
    
                if not vod_name:
                    vod_name = "未知影片"
    
                # ✅ 图片
                img = item.xpath('.//a[contains(@class,"module-item-pic")]//img')
                vod_pic = ''
                if img:
                    vod_pic = img[0].get('data-src') or img[0].get('src') or ''
    
                if vod_pic.startswith('//'):
                    vod_pic = 'https:' + vod_pic
                elif vod_pic.startswith('/'):
                    vod_pic = self.host + vod_pic
    
                # ✅ 备注（状态）
                vod_remarks = ''.join(item.xpath('.//a[contains(@class,"video-serial")]/text()')).strip()
    
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
    
        except Exception as e:
            print("searchContent error:", e)
    
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 9999,
            'limit': 24,
            'total': len(videos)
        }