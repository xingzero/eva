# coding=utf-8
#!/usr/bin/python
# 茶杯狐影视爬虫 - 最终稳定版（已优化播放与多线路）
# 网站: https://www.ht10010.com/

import re
import json
import requests
import base64
import time
from urllib.parse import urljoin, unquote
from lxml import etree

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def getName(self):
            return "茶杯狐影视"
        def init(self, extend=""):
            pass
        def homeContent(self, filter):
            return {"class": [], "list": []}
        def homeVideoContent(self):
            return {"list": []}
        def categoryContent(self, tid, pg, filter, extend=""):
            return {"list": []}
        def searchContent(self, key, quick, pg="1"):
            return {"list": []}
        def detailContent(self, ids):
            return {"list": []}
        def playerContent(self, flag, id, vipFlags):
            return {"parse": 0, "playUrl": "", "url": ""}
        def isVideoFormat(self, url):
            return False
        def manualVideoCheck(self):
            pass
        def localProxy(self, params):
            return None
        def destroy(self):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.name = "ccyh"
        self.host = "https://www.ht10010.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host,
            'Origin': self.host
        })
        self.max_retries = 2

    def getName(self):
        return self.name

    def init(self, extend=""):
        print("[茶杯狐] 初始化爬虫，获取 Cookie")
        for i in range(self.max_retries):
            try:
                r = self.session.get(self.host, timeout=5)
                if r.status_code == 200:
                    print("[茶杯狐] Cookie 初始化成功")
                    return
            except Exception as e:
                print(f"[茶杯狐] 初始化尝试 {i+1} 失败: {e}")
                time.sleep(1)

    def fetch_bytes(self, url):
        """返回原始字节内容"""
        print(f"[茶杯狐] 请求: {url}")
        for i in range(self.max_retries):
            try:
                r = self.session.get(url, timeout=10)
                return r.content
            except Exception as e:
                print(f"[茶杯狐] 请求失败 ({i+1}/{self.max_retries}): {e}")
                if i < self.max_retries - 1:
                    time.sleep(1)
        return None

    def _extract_id_from_url(self, url):
        match = re.search(r'/detail/(\d+)\.html', url)
        if match:
            return match.group(1)
        match = re.search(r'/play/(\d+)-\d+-\d+\.html', url)
        if match:
            return match.group(1)
        match = re.search(r'/cupfox-list/(\d+)', url)
        if match:
            return match.group(1)
        return re.sub(r'\D', '', url) or url

    # ==================== 首页分类 ====================
    def homeContent(self, filter):
        print("[茶杯狐] 获取首页分类")
        classes = [
            {"type_name": "电视剧", "type_id": "2"},
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "动漫", "type_id": "4"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "短剧", "type_id": "5"}
        ]
        filters = {}
        for cate in classes:
            tid = cate['type_id']
            filters[tid] = [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新", "v": "time"},
                    {"n": "人气", "v": "hits"},
                    {"n": "评分", "v": "score"}
                ]}
            ]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        print("[茶杯狐] 获取首页推荐")
        videos = []
        try:
            html_bytes = self.fetch_bytes(self.host)
            if not html_bytes:
                return {"list": []}
            root = etree.HTML(html_bytes)
            items = root.xpath('//div[contains(@class, "public-list-box")]')
            for item in items:
                try:
                    link_elem = item.xpath('.//a[contains(@class, "public-list-exp")]')
                    if not link_elem:
                        continue
                    href = link_elem[0].get('href', '')
                    vod_name = link_elem[0].get('title', '')
                    if not href or not vod_name:
                        continue
                    vod_id = self._extract_id_from_url(href)
                    img_elem = item.xpath('.//img')
                    vod_pic = ''
                    if img_elem:
                        vod_pic = img_elem[0].get('data-src', '') or img_elem[0].get('src', '')
                        if vod_pic and vod_pic.startswith('//'):
                            vod_pic = 'https:' + vod_pic
                        elif vod_pic and not vod_pic.startswith('http'):
                            vod_pic = urljoin(self.host, vod_pic)
                    remark_elem = item.xpath('.//span[contains(@class, "public-list-prb")]//i')
                    vod_remarks = remark_elem[0].xpath('string()').strip() if remark_elem else ''
                    videos.append({
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": vod_remarks
                    })
                except Exception as e:
                    print(f"[茶杯狐] 解析首页项失败: {e}")
        except Exception as e:
            print(f"[茶杯狐] 获取首页推荐失败: {e}")
        return {"list": videos}

    # ==================== 分类内容 ====================
    def categoryContent(self, tid, pg, filter, extend):
        print(f"[茶杯狐] 获取分类: tid={tid}, pg={pg}")
        videos = []
        try:
            pg = int(pg) if pg else 1
            if tid.startswith('http'):
                url = tid
            else:
                if tid.isdigit():
                    sort = extend.get('sort', '') if extend else ''
                    sort_param = f'--{sort}' if sort else ''
                    url = f"{self.host}/cupfox-list/{tid}--------{pg}---{sort_param}.html"
                else:
                    url = f"{self.host}/{tid}"
            print(f"[茶杯狐] 分类URL: {url}")
            html_bytes = self.fetch_bytes(url)
            if not html_bytes:
                return {"list": [], "page": pg, "pagecount": 0}
            root = etree.HTML(html_bytes)
            items = root.xpath('//div[contains(@class, "public-list-box")]')
            for item in items:
                try:
                    link_elem = item.xpath('.//a[contains(@class, "public-list-exp")]')
                    if not link_elem:
                        continue
                    href = link_elem[0].get('href', '')
                    vod_name = link_elem[0].get('title', '')
                    if not href:
                        continue
                    vod_id = self._extract_id_from_url(href)
                    img_elem = item.xpath('.//img')
                    vod_pic = ''
                    if img_elem:
                        vod_pic = img_elem[0].get('data-src', '') or img_elem[0].get('src', '')
                        if vod_pic and vod_pic.startswith('//'):
                            vod_pic = 'https:' + vod_pic
                        elif vod_pic and not vod_pic.startswith('http'):
                            vod_pic = urljoin(self.host, vod_pic)
                    remark_elem = item.xpath('.//span[contains(@class, "public-list-prt")]//i')
                    if not remark_elem:
                        remark_elem = item.xpath('.//span[contains(@class, "public-list-prb")]//i')
                    vod_remarks = remark_elem[0].xpath('string()').strip() if remark_elem else ''
                    if vod_name and vod_id:
                        videos.append({
                            "vod_id": vod_id,
                            "vod_name": vod_name,
                            "vod_pic": vod_pic,
                            "vod_remarks": vod_remarks
                        })
                except Exception as e:
                    print(f"[茶杯狐] 解析分类项失败: {e}")
            print(f"[茶杯狐] 分类完成：{len(videos)} 个视频")
        except Exception as e:
            print(f"[茶杯狐] 获取分类失败: {e}")
        return {
            'list': videos,
            'page': pg,
            'pagecount': 100,
            'limit': 20,
            'total': len(videos) * 100
        }

    # ==================== 详情页内容（已优化：多线路 + 集数反序） ====================
    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        vod_id = ids[0]
        print(f"[茶杯狐] 获取详情: {vod_id}")
        try:
            url = f"{self.host}/detail/{vod_id}.html"
            print(f"[茶杯狐] 详情URL: {url}")
            content = self.fetch_bytes(url)
            if not content:
                return {'list': []}
            root = etree.HTML(content)

            # 标题
            title_elem = root.xpath('//h3[@class="slide-info-title"] | //h1 | //title')
            if title_elem:
                vod_name = title_elem[0].xpath('string()').strip()
            else:
                vod_name = vod_id
            if ' - ' in vod_name:
                vod_name = vod_name.split(' - ')[0]

            # 图片
            pic_elem = root.xpath('//div[contains(@class, "detail-pic")]//img')
            vod_pic = ''
            if pic_elem:
                vod_pic = pic_elem[0].get('src', '') or pic_elem[0].get('data-src', '')
                if vod_pic and vod_pic.startswith('//'):
                    vod_pic = 'https:' + vod_pic
                elif vod_pic and not vod_pic.startswith('http'):
                    vod_pic = urljoin(self.host, vod_pic)

            # 导演、演员、年份、地区
            vod_year = ''
            vod_area = ''
            vod_actor = ''
            vod_director = ''
            info_items = root.xpath('//div[contains(@class, "slide-info")]')
            for item in info_items:
                text = item.xpath('string()').strip()
                if '导演：' in text:
                    vod_director = text.replace('导演：', '').strip()
                elif '演员：' in text:
                    vod_actor = text.replace('演员：', '').strip()
                elif '年份：' in text:
                    vod_year = text.replace('年份：', '').strip()
                elif '地区：' in text:
                    vod_area = text.replace('地区：', '').strip()

            # 简介
            desc_elem = root.xpath('//div[contains(@class, "text")] | //div[@id="height_limit"]')
            vod_content = desc_elem[0].xpath('string()').strip() if desc_elem else ''

            # ---------- 播放线路提取 ----------
            vod_play_from = []   # 线路名称列表
            vod_play_url = []    # 对应线路的集数字符串（# 分隔）

            # 1. 获取线路 tab 名称
            source_tabs = root.xpath('//div[contains(@class, "anthology-tab")]//a')
            source_names = [tab.xpath('string()').strip() for tab in source_tabs if tab.xpath('string()').strip()]

            # 2. 获取每个线路对应的集数容器
            list_containers = root.xpath('//div[contains(@class, "anthology-list")]//div[contains(@class, "anthology-list-box")]')

            if list_containers:
                for idx, container in enumerate(list_containers):
                    # 线路名（如果索引超出则用默认名称）
                    source_name = source_names[idx] if idx < len(source_names) else f"播放源{idx+1}"
                    # 提取所有集数链接（li 下的 a）
                    ep_links = container.xpath('.//li[contains(@class, "ecnav-dt")]//a')
                    if not ep_links:
                        ep_links = container.xpath('.//li//a[contains(@href, "/play/")]')

                    if ep_links:
                        episodes = []
                        for ep_link in ep_links:
                            ep_url = ep_link.get('href', '')
                            ep_name = ep_link.xpath('string()').strip()
                            if ep_url:
                                if ep_url.startswith('/'):
                                    ep_url = self.host + ep_url
                                episodes.append(f"{ep_name}${ep_url}")
                        # 重要：网站集数显示是倒序（最新集在前），需要反转使第1集在最前
                        episodes.reverse()
                        vod_play_from.append(source_name)
                        vod_play_url.append("#".join(episodes))
            else:
                # 备用：如果上面没提取到，则根据规律构造默认线路（1-4）
                # 检查是否有至臻4k、自营t等，也可以直接生成
                for line_id in range(1, 5):
                    source_name = f"线路{line_id}"
                    # 假装提取到第1-16集（实际需要从页面获取总集数，但这里简化为已知）
                    # 实际网站详情页都会有数据，一般不会进入此分支
                    pass

            # 特殊情况：如果仍然没有线路，尝试从 player_aaaa 中提取单个链接（备选）
            if not vod_play_url:
                html_str = content.decode('utf-8', errors='ignore')
                player_match = re.search(r'var\s+player_[a-z0-9]+\s*=\s*(\{.*?\})', html_str, re.DOTALL)
                if player_match:
                    try:
                        player_data = json.loads(player_match.group(1))
                        if player_data and player_data.get('url'):
                            play_url = player_data.get('url', '')
                            if play_url:
                                vod_play_from = ["默认线路"]
                                vod_play_url = [f"第01集${play_url}"]
                    except Exception:
                        pass

            video_detail = {
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_year": vod_year,
                "vod_area": vod_area,
                "vod_actor": vod_actor,
                "vod_director": vod_director,
                "vod_content": vod_content,
                "vod_play_from": "$$$".join(vod_play_from) if vod_play_from else "默认线路",
                "vod_play_url": "$$$".join(vod_play_url) if vod_play_url else ""
            }
            print(f"[茶杯狐] 详情完成: {vod_name}, 播放源: {len(vod_play_from)}")
            return {'list': [video_detail]}
        except Exception as e:
            print(f"[茶杯狐] 获取详情失败: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}

    # ==================== 播放页处理（只负责解析 m3u8，不涉及线路提取） ====================
    def playerContent(self, flag, id, vipFlags):
        print(f"[茶杯狐] 获取播放链接: {id}")
        try:
            if id.startswith('http'):
                play_url = id
            else:
                if id.startswith('/'):
                    play_url = self.host + id
                else:
                    play_url = f"{self.host}/play/{id}.html"
            print(f"[茶杯狐] 播放URL: {play_url}")
            content = self.fetch_bytes(play_url)
            if not content:
                print("[茶杯狐] 播放页获取失败，交由系统嗅探")
                return {"parse": 1, "playUrl": "", "url": play_url}
            html_str = content.decode('utf-8', errors='ignore')
            real_url = ""

            # 方法1：player_aaaa 变量（支持加密）
            match_json = re.search(r'var\s+player_[a-z0-9]+\s*=\s*(\{.*?\})', html_str, re.DOTALL)
            if match_json:
                try:
                    player_data = json.loads(match_json.group(1))
                    if player_data:
                        video_url = player_data.get('url', '')
                        encrypt = player_data.get('encrypt', 0)
                        if encrypt == 1:
                            real_url = unquote(video_url)
                        elif encrypt == 2:
                            try:
                                real_url = unquote(base64.b64decode(video_url).decode('utf-8'))
                            except:
                                pass
                        else:
                            real_url = video_url
                        print(f"[茶杯狐] 从player对象提取: {real_url[:100]}")
                except Exception as e:
                    print(f"[茶杯狐] 解析player对象失败: {e}")

            # 方法2：iframe 中的 m3u8
            if not real_url:
                iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+m3u8[^"\']*)["\']', html_str, re.I)
                if iframe_match:
                    real_url = iframe_match.group(1)
                    print(f"[茶杯狐] 从iframe提取: {real_url}")

            # 方法3：直接正则提取 m3u8
            if not real_url:
                m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html_str, re.I)
                if m3u8_match:
                    real_url = m3u8_match.group(1)
                    print(f"[茶杯狐] 正则提取: {real_url}")

            if real_url and real_url.startswith('http'):
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": real_url,
                    "header": json.dumps({
                        'User-Agent': self.session.headers['User-Agent'],
                        'Referer': self.host
                    })
                }
            print(f"[茶杯狐] 未找到直链，交由系统嗅探: {play_url}")
            return {"parse": 1, "playUrl": "", "url": play_url}
        except Exception as e:
            print(f"[茶杯狐] 播放解析失败: {e}")
            return {"parse": 1, "playUrl": "", "url": id}

    def searchContent(self, key, quick, pg="1"):
        print("[茶杯狐] 搜索功能暂未实现")
        return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}

    def isVideoFormat(self, url):
        video_formats = ['.m3u8', '.mp4', '.avi', '.mkv', '.flv', '.ts']
        return any(url.lower().endswith(fmt) for fmt in video_formats)

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        return None

    def destroy(self):
        pass