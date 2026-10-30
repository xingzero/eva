# -*- coding: utf-8 -*-
"""
目标站: 羊羊影视 (yyys.uk)
模板: 影视聚合搜索 / 爬虫播放
站点类型: 综合影视 (电影/剧集/动漫/综艺/短剧/纪录片/漫剧/少儿)
核心逻辑: 调用 HMAC-SHA256 签名 JSON API, 提取视频信息和真实播放链接
签名机制:
  - 从前端 JS 逆向提取的 HMAC-SHA256 双层签名
  - 第一层: HMAC_SHA256(device_salt + sign_key, device_id) -> 签名密钥
  - 第二层: HMAC_SHA256(签名密钥, 规范化请求串) -> 最终签名
  - 规范化串: METHOD\n/api/app/path\nsorted_query\ntimestamp\nnonce\nweb
线路机制:
  - 详情接口 /videos/{id} 返回全部播放线路 (playGroups)
    * 直链线路: parseApi 为空, url 直接为 https m3u8/mp4 直链, 可直接播放
    * 解析线路: parseApi 为解析 API 前缀, url 为编码串, 需 GET parseApi+url 换取真实地址
速度优化:
  - 详情/线路结果按 TTL 缓存, 避免重复请求
  - 播放时仅解析所选线路 (懒解析), 直链线路零额外请求
  - 搜索结果缓存, 翻页不重复请求首页
  - 签名密钥只计算一次 (device_id 固定), 避免每次请求重复推导
支持: 首页, 一/二级分类, 搜索, 详情, 播放
"""
import re
import sys
import json
import time
import hmac
import hashlib
import uuid
import urllib.parse

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://www.yyys.uk"
        self.api_base = "/api/app"
        # 签名常量 (从前端 JS 逆向提取)
        self._device_salt = "cms_device_salt_v1_2024"
        self._sign_key = "cms_app_sign_key_v1_2024_secure"
        self._combined_key = (self._device_salt + self._sign_key).encode("utf-8")
        self._platform = "web"
        # 固定 device_id (同一设备保持一致, 避免每次请求重新注册)
        self._device_id = "web-" + str(uuid.uuid4())
        # 预计算签名密钥 (只算一次)
        self._sign_secret = self._derive_sign_key(self._device_id)

        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.site_url + "/",
            'Origin': self.site_url,
        }
        self.default_pic = ""

        # 一级分类映射: id -> 中文名
        self.categories = {
            1: "电影",
            2: "剧集",
            3: "动漫",
            4: "综艺",
            5: "短剧",
            6: "纪录片",
            7: "漫剧",
            8: "少儿",
        }

        # 二级分类筛选: 地区 (取站点常见值)
        self.area_options = [
            ("全部", ""), ("中国大陆", "中国大陆"), ("中国香港", "中国香港"),
            ("中国台湾", "中国台湾"), ("美国", "美国"), ("日本", "日本"),
            ("韩国", "韩国"), ("英国", "英国"), ("法国", "法国"),
            ("印度", "印度"), ("泰国", "泰国"), ("其他", "其他"),
        ]
        # 二级分类筛选: 年份
        self.year_options = [("全部", "")] + [(str(y), str(y)) for y in range(2027, 2014, -1)]
        # 二级分类筛选: 类型 (按分类区分)
        self.class_options = {
            1: [("全部", ""), ("动作", "动作"), ("喜剧", "喜剧"), ("爱情", "爱情"),
                ("科幻", "科幻"), ("悬疑", "悬疑"), ("惊悚", "惊悚"), ("恐怖", "恐怖"),
                ("剧情", "剧情"), ("犯罪", "犯罪"), ("冒险", "冒险"), ("奇幻", "奇幻"),
                ("战争", "战争"), ("古装", "古装"), ("武侠", "武侠"), ("动画", "动画"),
                ("纪录", "纪录"), ("历史", "历史"), ("音乐", "音乐"), ("恐怖", "恐怖")],
            2: [("全部", ""), ("国产", "国产"), ("港剧", "港剧"), ("韩剧", "韩剧"),
                ("美剧", "美剧"), ("日剧", "日剧"), ("悬疑", "悬疑"), ("言情", "言情"),
                ("古装", "古装"), ("武侠", "武侠"), ("都市", "都市"), ("家庭", "家庭"),
                ("战争", "战争"), ("喜剧", "喜剧"), ("科幻", "科幻"), ("奇幻", "奇幻")],
            3: [("全部", ""), ("国产", "国产"), ("日本", "日本"), ("欧美", "欧美"),
                ("热血", "热血"), ("冒险", "冒险"), ("奇幻", "奇幻"), ("科幻", "科幻"),
                ("搞笑", "搞笑"), ("恋爱", "恋爱"), ("校园", "校园"), ("推理", "推理"),
                ("机战", "机战"), ("运动", "运动"), ("治愈", "治愈"), ("战斗", "战斗")],
            4: [("全部", ""), ("真人秀", "真人秀"), ("脱口秀", "脱口秀"), ("选秀", "选秀"),
                ("音乐", "音乐"), ("美食", "美食"), ("旅行", "旅行"), ("竞技", "竞技"),
                ("情感", "情感"), ("纪实", "纪实"), ("访谈", "访谈"), ("综艺", "综艺")],
            5: [("全部", ""), ("逆袭", "逆袭"), ("甜宠", "甜宠"), ("重生", "重生"),
                ("穿越", "穿越"), ("豪门", "豪门"), ("复仇", "复仇"), ("玄幻", "玄幻"),
                ("古风", "古风"), ("都市", "都市"), ("虐恋", "虐恋"), ("搞笑", "搞笑")],
            6: [("全部", ""), ("人文", "人文"), ("自然", "自然"), ("科技", "科技"),
                ("历史", "历史"), ("军事", "军事"), ("社会", "社会"), ("美食", "美食"),
                ("旅游", "旅游"), ("探险", "探险"), ("人物", "人物")],
            7: [("全部", ""), ("修仙", "修仙"), ("玄幻", "玄幻"), ("都市", "都市"),
                ("热血", "热血"), ("冒险", "冒险"), ("搞笑", "搞笑"), ("战斗", "战斗"),
                ("穿越", "穿越"), ("古风", "古风")],
            8: [("全部", ""), ("早教", "早教"), ("启蒙", "启蒙"), ("益智", "益智"),
                ("成长", "成长"), ("冒险", "冒险"), ("搞笑", "搞笑"), ("奇幻", "奇幻"),
                ("动物", "动物"), ("自然", "自然")],
        }

        # 缓存: 详情/搜索/分类 (TTL 秒), 避免重复请求, 提升加载与播放速度
        self._cache = {}
        self._cache_ttl_detail = 600
        self._cache_ttl_search = 120
        self._cache_ttl_category = 120
        self._cache_ttl_resolve = 300
        self._cache_ttl_home = 300

    # ========== 签名与请求 ==========

    def _derive_sign_key(self, device_id):
        """第一层签名: 从 device_id 推导出签名密钥
        算法: HMAC_SHA256(device_salt + sign_key, device_id) -> hex
        """
        return hmac.new(
            self._combined_key, device_id.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _make_query_canonical(self, params):
        """将查询参数按 key 排序拼接为 key=value&key=value 格式"""
        if not params:
            return ""
        return "&".join(
            "{0}={1}".format(k, str(params[k])) for k in sorted(params.keys())
        )

    def _sign_headers(self, method, path, params=None, body=None):
        """生成 API 签名请求头

        规范化串: METHOD\n/api/app/path\nsorted_query\ntimestamp\nnonce\nplatform
        签名: HMAC_SHA256(签名密钥, 规范化串) -> hex
        """
        method = method.upper()
        full_path = self.api_base + path if path.startswith("/") else self.api_base + "/" + path
        query_str = self._make_query_canonical(params) if params else ""
        ts = str(int(time.time()))
        nonce = str(uuid.uuid4())
        body_hash = ""
        if method != "GET" and body is not None:
            if isinstance(body, dict):
                body_str = json.dumps(body, ensure_ascii=False)
            elif isinstance(body, str):
                body_str = body
            else:
                body_str = str(body)
            body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

        parts = [method, full_path, query_str, ts, nonce, self._platform]
        if body_hash:
            parts.append(body_hash)
        canonical = "\n".join(parts)

        sig = hmac.new(
            self._sign_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        result = {
            "X-Device-ID": self._device_id,
            "X-Platform": self._platform,
            "X-Timestamp": ts,
            "X-Nonce": nonce,
            "X-Signature": sig,
            "X-App-Version": self._platform,
        }
        if body_hash:
            result["X-Body-Hash"] = body_hash
        return result

    def _api_get(self, path, params=None):
        """调用签名 GET API 并返回解析后的 JSON 字典"""
        url = self.site_url + self.api_base + path
        sec_headers = self._sign_headers("GET", path, params)
        headers = {**self.headers, **sec_headers}
        try:
            resp = self.fetch(url, headers=headers, params=params)
            if not resp:
                return {}
            return json.loads(resp.text)
        except Exception:
            return {}

    # ========== 缓存（速度优化） ==========

    def _cache_get(self, key):
        """读取缓存项, 过期则视为未命中"""
        item = self._cache.get(key)
        if not item:
            return None
        if item[0] < time.time():
            self._cache.pop(key, None)
            return None
        return item[1]

    def _cache_set(self, key, value, ttl):
        self._cache[key] = (time.time() + ttl, value)

    # ========== 卡片解析 ==========

    def _parse_card(self, card):
        """将 API 视频对象转换为 vod 字典 (列表页通用)"""
        vid = str(card.get("id", "") or "")
        name = card.get("name", "") or ""
        pic = card.get("pic", "") or ""
        remark = card.get("remarks", "") or ""
        year = str(card.get("year", "")) if card.get("year") else ""
        area = card.get("area", "") or ""
        class_extend = card.get("classExtend", "") or ""
        score = card.get("doubanScore", "") or ""
        if score and score != "0.0":
            remark = score + " " + remark if remark else score
        return {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic if pic else self.default_pic,
            "vod_remarks": remark,
            "vod_year": year,
            "vod_area": area,
            "vod_type": class_extend,
        }

    # ========== 工具方法 ==========

    def _play_header(self, ua="", ref=""):
        """播放直链时需要携带的请求头"""
        user_agent = ua if ua else self.headers['User-Agent']
        referer = ref if ref else (self.site_url + "/")
        return {
            'User-Agent': user_agent,
            'Referer': referer,
        }

    def _get_detail(self, vid):
        """获取视频详情 (含全部线路与选集, 带缓存)

        详情接口: /videos/{id}
        返回 playGroups 数组, 每组含线路信息与全部剧集 URL
        """
        vid = str(vid).strip()
        cache_key = "detail:{0}".format(vid)
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        result = self._api_get("/videos/{0}".format(urllib.parse.quote(vid)))
        if not result or result.get("code") != 200:
            return None
        detail = result.get("data") or {}
        if "id" not in detail:
            return None

        self._cache_set(cache_key, detail, self._cache_ttl_detail)
        return detail

    def _resolve_play_url(self, play_url, parse_api, ua, ref):
        """解析播放地址: 直链直接返回, 编码串通过 parseApi 解析

        返回 (real_url, is_direct) 或 (None, False)
        """
        if not play_url:
            return None, False

        # 直链: parseApi 为空且 url 以 http 开头
        if not parse_api and play_url.startswith("http"):
            if ".m3u8" in play_url or ".mp4" in play_url:
                return play_url, True

        # 编码串: 需要通过 parseApi 解析
        if parse_api:
            cache_key = "resolve:{0}".format(play_url)
            cached = self._cache_get(cache_key)
            if cached:
                return cached, True

            # 对 play_url 做 URL 编码 (处理 |, == 等特殊字符)
            encoded_play_url = urllib.parse.quote(play_url, safe='')
            full_url = parse_api + encoded_play_url
            try:
                resp = self.fetch(full_url, headers=self._play_header(ua, ref))
                if resp:
                    try:
                        data = json.loads(resp.text)
                        # 兼容 code=200 或 code=0 的成功响应
                        code = data.get("code", -1)
                        real_url = data.get("url", "") or ""
                        if real_url.startswith("http") and code in (200, 0, 1):
                            self._cache_set(cache_key, real_url, self._cache_ttl_resolve)
                            return real_url, True
                    except (ValueError, KeyError, TypeError):
                        pass
                    # 非 JSON 响应, 可能直接就是 URL
                    text = resp.text.strip()
                    if text.startswith("http"):
                        self._cache_set(cache_key, text, self._cache_ttl_resolve)
                        return text, True
            except Exception:
                pass

        return None, False

    # ========== 首页 ==========

    def homeContent(self, filter):
        """获取首页内容: 一级分类(含二级筛选) + 推荐视频"""
        categories = []
        for cat_id, cat_name in self.categories.items():
            class_opts = self.class_options.get(cat_id, [("全部", "")])
            categories.append({
                "type_id": str(cat_id),
                "type_name": cat_name,
                "filter": [
                    {
                        "key": "class",
                        "name": "类型",
                        "value": [{"n": n, "v": v} for n, v in class_opts],
                    },
                    {
                        "key": "area",
                        "name": "地区",
                        "value": [{"n": n, "v": v} for n, v in self.area_options],
                    },
                    {
                        "key": "year",
                        "name": "年份",
                        "value": [{"n": n, "v": v} for n, v in self.year_options],
                    },
                ],
            })

        # 推荐视频: 调用推荐接口
        videos = self._get_recommend(20)

        return {"class": categories, "list": videos, "filters": {}}

    def homeVideoContent(self):
        """获取首页推荐视频列表"""
        return {"list": self._get_recommend(30)}

    def _get_recommend(self, limit=20):
        """获取推荐视频列表 (带缓存)"""
        cache_key = "home:recommend:{0}".format(limit)
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        videos = []
        result = self._api_get("/videos/recommend", params={"page": "1", "limit": str(limit)})
        if result and result.get("code") == 200:
            data = result.get("data") or {}
            card_list = data if isinstance(data, list) else data.get("list", [])
            for card in card_list:
                if card.get("id"):
                    videos.append(self._parse_card(card))

        self._cache_set(cache_key, videos, self._cache_ttl_home)
        return videos

    # ========== 分类(含二级筛选) ==========

    def _apply_filters(self, params, extend):
        """从 extend 字典中提取有效筛选参数, 过滤掉 '全部' / 空字符串 / None"""
        if not extend:
            return
        for fk in ("class", "area", "year"):
            fv = extend.get(fk)
            if fv and str(fv).strip() and str(fv).strip() != "全部":
                params[fk] = str(fv).strip()

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类列表

        tid:     一级分类 ID (1-8)
        pg:      页码
        filter:  TVBox 框架传入, 此处不直接使用
        extend:  筛选字典, 如 {"class": "动作", "area": "中国大陆", "year": "2026"}
        """
        page = int(pg) if pg else 1
        limit = 20
        cat_id = tid

        params = {
            "page": str(page),
            "limit": str(limit),
        }
        self._apply_filters(params, extend)

        # 分类视频缓存 (相同参数翻页时只缓存当前页)
        cache_key = "cat:{0}:{1}".format(cat_id, json.dumps(params, sort_keys=True))
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        path = "/categories/{0}/videos".format(urllib.parse.quote(str(cat_id)))
        result = self._api_get(path, params=params)

        if not result or result.get("code") != 200:
            ret = {"list": [], "page": page, "pagecount": 1, "limit": limit, "total": 0}
            return ret

        data = result.get("data") or {}
        cards = data.get("list", []) or []
        videos = [self._parse_card(c) for c in cards if c.get("id")]

        total = data.get("total", 0) or 0
        pagecount = (total + limit - 1) // limit if total > 0 else page
        if not pagecount:
            pagecount = 1

        ret = {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": limit,
            "total": total,
        }
        self._cache_set(cache_key, ret, self._cache_ttl_category)
        return ret

    # ========== 搜索 ==========

    def searchContent(self, key, quick, pg="1"):
        """搜索内容

        key: 搜索关键词
        pg:  页码
        使用站点搜索: /videos/search?keyword={key}
        """
        page = int(pg) if pg else 1
        limit = 20
        params = {
            "keyword": key,
            "page": str(page),
            "limit": str(limit),
        }

        # 搜索结果缓存 (仅缓存首页, 翻页不缓存)
        cache_key = "search:{0}:{1}".format(key, page)
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        result = self._api_get("/videos/search", params=params)

        if not result or result.get("code") != 200:
            return {"list": [], "page": page, "pagecount": 1, "limit": limit, "total": 0}

        data = result.get("data") or {}
        cards = data.get("list", []) or []
        videos = [self._parse_card(c) for c in cards if c.get("id")]

        total = data.get("total", 0) or 0
        pagecount = (total + limit - 1) // limit if total > 0 else 1

        ret = {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": limit,
            "total": total,
        }
        # 仅缓存首页搜索结果, 避免新内容延迟
        if page == 1:
            self._cache_set(cache_key, ret, self._cache_ttl_search)
        return ret

    # ========== 详情 ==========

    def detailContent(self, ids):
        """获取视频详情 (含全部线路与选集)

        ids[0]: 视频 ID
        播放源: playGroups 中的每条线路
        剧集地址: 每集以 "集名$url@@parseApi@@ua@@referer" 形式编码, 播放时按所选线路解析
        """
        if not ids:
            return {"list": []}

        vid = str(ids[0])
        detail = self._get_detail(vid)
        if not detail:
            return {"list": []}

        # 基本信息
        title = detail.get("name", "") or ""
        pic = detail.get("pic", "") or self.default_pic
        content = detail.get("content", "") or ""
        actor = detail.get("actor", "") or ""
        director = detail.get("director", "") or ""
        year = str(detail.get("year", "")) if detail.get("year") else ""
        area = detail.get("area", "") or ""
        class_extend = detail.get("classExtend", "") or ""
        score = detail.get("doubanScore", "") or ""
        lang = detail.get("lang", "") or ""
        remarks = detail.get("remarks", "") or ""
        sub_title = detail.get("subTitle", "") or ""

        # 清理 content 中的 HTML 标签
        if content:
            content = re.sub(r'<[^>]+>', '', content).strip()

        # 播放源与选集
        play_from = []
        play_url = []

        play_groups = detail.get("playGroups", []) or []

        # 线路排序: 直链线路优先 (parseApi 为空且 url 以 http 开头), 解析线路其次
        # 同优先级内按原 sort 排序
        def _line_priority(group):
            parse_api = group.get("parseApi", "") or ""
            first_url = ""
            play_urls = group.get("playUrls", []) or []
            if play_urls:
                first_url = play_urls[0].get("url", "") or ""
            is_direct = (not parse_api) and first_url.startswith("http")
            return (0 if is_direct else 1, group.get("sort", 0))

        play_groups.sort(key=_line_priority)

        for group in play_groups:
            group_name = group.get("name", "") or group.get("code", "") or "默认线路"
            parse_api = group.get("parseApi", "") or ""
            ua = group.get("userAgent", "") or ""
            ref = group.get("referer", "") or ""
            group_code = group.get("code", "") or ""

            play_urls = group.get("playUrls", []) or []
            play_urls.sort(key=lambda p: p.get("sort", 0))

            ep_list = []
            for pu in play_urls:
                ep_name = pu.get("name", "") or ""
                if not ep_name:
                    num = pu.get("sort")
                    ep_name = "第{0}集".format(num) if num is not None else "播放"
                url = pu.get("url", "") or ""
                if not url:
                    continue
                # 编码: 集名$url@@parseApi@@ua@@referer@@videoId
                # videoId 用于播放降级: 当前线路解析失败时自动尝试其他线路
                encoded = "{0}${1}@@{2}@@{3}@@{4}@@{5}".format(
                    ep_name, url, parse_api, ua, ref, vid
                )
                ep_list.append(encoded)

            if ep_list:
                play_from.append(group_name)
                play_url.append("#".join(ep_list))

        # 无线路数据兜底
        if not play_from:
            play_from.append("默认线路")
            play_url.append("播放${0}/video/{1}@@".format(self.site_url, vid))

        result = [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": content,
            "vod_actor": actor,
            "vod_director": director,
            "vod_year": year,
            "vod_area": area,
            "vod_type": class_extend,
            "vod_remarks": remarks,
            "vod_lang": lang,
            "vod_sub_title": sub_title,
            "vod_score": score,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }]
        return {"list": result}

    # ========== 播放 ==========

    def playerContent(self, flag, id, vipFlags):
        """获取播放链接

        id 格式: 集名$url@@parseApi@@ua@@referer@@videoId (从 vod_play_url 拆分而来)
        flag:    当前选中的播放源名称 (对应线路 name)
        逻辑:
          1) 从 id 中拆出 url, parseApi, ua, referer, videoId
          2) 直链 (parseApi 为空, url 以 http 开头) 直接返回, 零延迟
          3) 编码串 (parseApi 非空) 通过 parseApi+url 解析真实地址
          4) 解析失败: 自动降级到其他线路尝试同一集 (多线路 fallback)
          5) 全部失败: 回到站点播放页 webview 嗅探
        """
        raw_id = id
        # 拆出 url 部分 (集名$url@@...)
        ep_name = ""
        if "$" in raw_id:
            ep_name, raw_id = raw_id.split("$", 1)
            ep_name = ep_name.strip()

        # 拆出 parseApi, ua, referer, videoId
        parts = raw_id.split("@@")
        play_url = (parts[0] if len(parts) > 0 else "").strip()
        parse_api = (parts[1] if len(parts) > 1 else "").strip()
        ua = (parts[2] if len(parts) > 2 else "").strip()
        ref = (parts[3] if len(parts) > 3 else "").strip()
        video_id = (parts[4] if len(parts) > 4 else "").strip()

        if not play_url:
            return {"parse": 1, "url": id, "header": self.headers}

        # 1) 直链直接返回 (parseApi 为空, url 为 http m3u8/mp4)
        if not parse_api and play_url.startswith("http"):
            return {
                "parse": 0,
                "url": play_url,
                "header": self._play_header(ua, ref),
            }

        # 2) 编码串: 通过 parseApi 解析
        if parse_api:
            real_url, _ = self._resolve_play_url(play_url, parse_api, ua, ref)
            if real_url:
                return {
                    "parse": 0,
                    "url": real_url,
                    "header": self._play_header(ua, ref),
                }

        # 3) 多线路降级: 当前线路解析失败, 自动尝试其他线路的同一集
        if video_id:
            fallback_url = self._try_fallback_lines(video_id, ep_name, play_url)
            if fallback_url:
                return fallback_url

        # 4) 全部失败: 回到站点播放页 webview 嗅探
        if play_url.startswith("http"):
            return {"parse": 1, "url": play_url, "header": self.headers}
        return {
            "parse": 1,
            "url": "{0}/video/{1}".format(self.site_url, urllib.parse.quote(play_url)),
            "header": self.headers
        }

    def _try_fallback_lines(self, video_id, ep_name, failed_url):
        """多线路降级: 遍历其他线路, 找到同一集的可播放地址

        策略:
          1) 获取视频详情 (带缓存, 不额外请求)
          2) 遍历所有 playGroups, 直链线路优先
          3) 匹配同一集名 (或集序号)
          4) 直链直接返回, 解析线路调用 parseApi
          5) 返回第一个可用的播放地址
        """
        detail = self._get_detail(video_id)
        if not detail:
            return None

        play_groups = detail.get("playGroups", []) or []
        # 直链线路优先 (降级时也优先最可靠的)
        def _line_priority(group):
            parse_api = group.get("parseApi", "") or ""
            first_url = ""
            play_urls = group.get("playUrls", []) or []
            if play_urls:
                first_url = play_urls[0].get("url", "") or ""
            is_direct = (not parse_api) and first_url.startswith("http")
            return (0 if is_direct else 1, group.get("sort", 0))

        play_groups.sort(key=_line_priority)

        for group in play_groups:
            parse_api = group.get("parseApi", "") or ""
            ua = group.get("userAgent", "") or ""
            ref = group.get("referer", "") or ""
            play_urls = group.get("playUrls", []) or []
            play_urls.sort(key=lambda p: p.get("sort", 0))

            for pu in play_urls:
                url = pu.get("url", "") or ""
                if not url or url == failed_url:
                    continue
                pu_name = pu.get("name", "") or ""
                if not pu_name:
                    num = pu.get("sort")
                    pu_name = "第{0}集".format(num) if num is not None else "播放"

                # 匹配同一集: 集名相同 或 集序号相同
                if pu_name != ep_name and not self._ep_match(pu_name, ep_name, pu.get("sort")):
                    continue

                # 直链直接返回
                if not parse_api and url.startswith("http"):
                    if ".m3u8" in url or ".mp4" in url:
                        return {
                            "parse": 0,
                            "url": url,
                            "header": self._play_header(ua, ref),
                        }

                # 解析线路: 调用 parseApi
                if parse_api:
                    real_url, _ = self._resolve_play_url(url, parse_api, ua, ref)
                    if real_url:
                        return {
                            "parse": 0,
                            "url": real_url,
                            "header": self._play_header(ua, ref),
                        }

        return None

    def _ep_match(self, name1, name2, sort_num):
        """宽松匹配集名: "1"=="第01集"=="第1集" 等"""
        if not name1 or not name2:
            return False
        if name1 == name2:
            return True
        # 提取数字比较
        import re
        nums1 = re.findall(r'\d+', name1)
        nums2 = re.findall(r'\d+', name2)
        if nums1 and nums2:
            try:
                return int(nums1[0]) == int(nums2[0])
            except (ValueError, IndexError):
                pass
        if sort_num is not None:
            try:
                for n in nums2:
                    if int(n) == sort_num:
                        return True
            except (ValueError, IndexError):
                pass
        return False

    # ========== 辅助: LIVE & 1线接口 (TVBox 框架可选) ==========

    def isWild(self, url):
        """标记是否为嗅探地址"""
        return False
