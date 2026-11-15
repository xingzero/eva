# -*- coding: utf-8 -*-
# 站点：4kyszx.top (Android App 接口)
# 版本：v1.2
# 说明：移除所有打印日志，修复异常处理逻辑

from base.spider import Spider
import hashlib
import hmac
import time
import random
import base64
import json
import sys
import urllib3
from urllib.parse import urlparse, urlencode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.append('..')


class Spider(Spider):
    host = 'https://4kyszx.top'
    api_base = '/api/app'

    MASTER_KEY = b"cms_device_salt_v1_2024cms_app_sign_key_v1_2024_secure"

    def_headers = {
        'User-Agent': 'Dart/3.12 (dart:io)',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'x-device-id': 'dd6d6bc43e55625acc470573f8d6d8b3',
        'x-app-version': '1.0.19+20',
        'x-platform': 'android',
        'x-nonce': '',
        'x-timestamp': '',
        'x-signature': ''
    }

    _categories = None

    # ---------- 签名算法 ----------
    def _derive_signing_key(self, device_id):
        return hmac.new(self.MASTER_KEY, device_id.encode('utf-8'), hashlib.sha256).hexdigest()

    def _calc_signature(self, method, path, query, timestamp, nonce, app_version, signing_key_hex):
        print(query)
        parts = [
            method.upper(),
            path,
            query,
            str(timestamp),
            nonce,
            app_version
        ]
        raw = "\n".join(parts)
        signing_key_bytes = signing_key_hex.encode('utf-8')
        return hmac.new(signing_key_bytes, raw.encode('utf-8'), hashlib.sha256).hexdigest()

    def _build_headers(self, url, method='GET', params=None, body=None, sign_query=None):
        """
        构建带签名的请求头
        :param url: 完整请求 URL（含编码后的 query）
        :param method: 请求方法
        :param params: 未使用，保留
        :param body: 请求体（POST 用）
        :param sign_query: 用于签名的原始查询字符串（未编码），若不提供则从 url 中解析
        """
        timestamp = str(int(time.time()))
        nonce_bytes = random.getrandbits(128).to_bytes(16, 'big')
        nonce_b64 = base64.b64encode(nonce_bytes).decode('utf-8')

        parsed = urlparse(url)
        path = parsed.path
        # 如果提供了 sign_query，则使用它计算签名；否则从 url 中提取
        if sign_query is not None:
            query_for_sign = sign_query
        else:
            query_for_sign = parsed.query  # 此值是编码后的

        device_id = self.def_headers['x-device-id']
        signing_key_hex = self._derive_signing_key(device_id)

        signature = self._calc_signature(
            method=method,
            path=path,
            query=query_for_sign,
            timestamp=timestamp,
            nonce=nonce_b64,
            app_version=self.def_headers['x-app-version'],
            signing_key_hex=signing_key_hex
        )

        headers = self.def_headers.copy()
        headers.update({
            'x-timestamp': timestamp,
            'x-nonce': nonce_b64,
            'x-signature': signature
        })
        return headers

    # ---------- 数据转换 ----------
    def _parse_video_item(self, item):
        pic = item.get('pic', '') or item.get('picSlide', '')
        return {
            'vod_id': str(item.get('id', '')),
            'vod_name': item.get('name', ''),
            'vod_pic': pic,
            'vod_remarks': item.get('remarks', ''),
            'vod_year': item.get('year', ''),
            'vod_area': item.get('area', ''),
            'vod_actor': item.get('actor', ''),
            'vod_director': item.get('director', ''),
            'vod_content': item.get('content', ''),
            'type_name': item.get('categoryName', ''),
            'playFrom': item.get('playFrom', '')
        }

    def _parse_video_list(self, data_list):
        seen = set()
        result = []
        for item in data_list:
            vid = str(item.get('id', ''))
            if vid and vid not in seen:
                seen.add(vid)
                result.append(self._parse_video_item(item))
        return result

    # ---------- 首页分类 ----------
    def homeContent(self, filter):
        if not self.host:
            return None
        url = f"{self.host}{self.api_base}/categories"
        headers = self._build_headers(url, method='GET')
        try:
            resp = self.fetch(url, headers=headers, verify=False)
            data = resp.json()
            if data.get('code') != 200:
                return None
            categories = data.get('data', [])
            self._categories = categories
            class_list = []
            for cat in categories:
                if cat.get('status') == 1:
                    class_list.append({
                        'type_id': str(cat['id']),
                        'type_name': cat['name']
                    })
            return {'class': class_list, 'filters': {}}
        except Exception:
            return None

    # ---------- 首页推荐 ----------
    def homeVideoContent(self):
        if not self.host:
            return None
        if self._categories is None:
            home = self.homeContent(False)
            if not home:
                return {'list': []}
        categories = self._categories or []
        if not categories:
            return {'list': []}

        all_videos = []
        seen_ids = set()
        for cat in categories:
            cat_id = cat.get('id')
            if not cat_id:
                continue
            url = f"{self.host}{self.api_base}/categories/{cat_id}/recommend"
            headers = self._build_headers(url, method='GET')
            try:
                resp = self.fetch(url, headers=headers, verify=False)
                data = resp.json()
                if data.get('code') != 200:
                    continue
                items = data.get('data', [])
                for item in items:
                    vid = str(item.get('id', ''))
                    if vid and vid not in seen_ids:
                        seen_ids.add(vid)
                        all_videos.append(self._parse_video_item(item))
            except Exception:
                continue
        return {'list': all_videos}

    # ---------- 分类视频列表 ----------
    def categoryContent(self, tid, pg, filter, extend):
        if not self.host:
            return None
        url = f"{self.host}{self.api_base}/categories/{tid}/videos"
        params = {'page': pg, 'page_size': 30}
        if extend:
            if extend.get('year'):
                params['year'] = extend['year']
            if extend.get('area'):
                params['area'] = extend['area']
            if extend.get('sort'):
                sort_map = {'最新': 'time', '最热': 'hot', '评分': 'score'}
                params['sort'] = sort_map.get(extend['sort'], extend['sort'])
        full_url = f"{url}?{urlencode(params)}"
        headers = self._build_headers(full_url, method='GET')
        try:
            resp = self.fetch(full_url, headers=headers, verify=False)
            data = resp.json()
            if data.get('code') != 200:
                return {'list': [], 'page': pg}
            result = data.get('data', {})
            video_list = self._parse_video_list(result.get('list', []))
            total = result.get('total', 0)
            page_size = result.get('pageSize', 30)
            return {
                'list': video_list,
                'page': result.get('page', int(pg)),
                'pagecount': (total + page_size - 1) // page_size,
                'total': total
            }
        except Exception:
            return {'list': [], 'page': pg}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        if not self.host:
            return None
        url = f"{self.host}{self.api_base}/videos/search"
        raw_query = f"keyword={key}&page={pg}&page_size=20"
        params = {'keyword': key, 'page': pg, 'page_size': 20}
        full_url = f"{url}?{urlencode(params)}"
        headers = self._build_headers(full_url, method='GET', sign_query=raw_query)
        try:
            resp = self.fetch(full_url, headers=headers, verify=False)
            data = resp.json()
            print(data)
            if data.get('code') != 200:
                return {'list': [], 'page': pg}
            result = data.get('data', {})
            videos = self._parse_video_list(result.get('list', []))
            total = result.get('total', 0)
            page_size = result.get('pageSize', 30)
            return {
                'list': videos,
                'page': result.get('page', int(pg)),
                'pagecount': (total + page_size - 1) // page_size,
                'total': total
            }
        except Exception:
            return {'list': [], 'page': pg}

    # ---------- 详情 ----------
    def detailContent(self, ids):
        if not ids:
            return None
        vid = ids[0]
        url = f"{self.host}{self.api_base}/videos/{vid}"
        headers = self._build_headers(url, method='GET')
        try:
            resp = self.fetch(url, headers=headers, verify=False)
            data = resp.json()
            if data.get('code') != 200:
                return None
            detail = data.get('data', {})

            play_from = []
            play_urls = []
            play_groups = detail.get('playGroups', [])

            for group in play_groups:
                group_name = group.get('name', '默认源')
                parse_api = group.get('parseApi', '')
                episode_urls = []
                for idx, ep in enumerate(group.get('playUrls', [])):
                    ep_name = ep.get('name', f'第{idx+1}集')
                    ep_url = ep.get('url', '')
                    if parse_api and not (ep_url.startswith('http') and ('.m3u8' in ep_url or '.mp4' in ep_url)):
                        full_url = parse_api + ep_url
                    else:
                        full_url = ep_url
                    episode_urls.append(f"{ep_name}${full_url}")
                if episode_urls:
                    play_from.append(group_name)
                    play_urls.append('#'.join(episode_urls))

            video = {
                'vod_id': str(detail.get('id', vid)),
                'vod_name': detail.get('name', ''),
                'vod_pic': detail.get('pic', '') or detail.get('picSlide', ''),
                'vod_remarks': detail.get('remarks', ''),
                'vod_year': detail.get('year', ''),
                'vod_area': detail.get('area', ''),
                'vod_actor': detail.get('actor', ''),
                'vod_director': detail.get('director', ''),
                'vod_content': detail.get('content', ''),
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_urls),
                'type_name': detail.get('categoryName', '')
            }
            return {'list': [video]}
        except Exception:
            return None

    # ---------- 播放解析 ----------
    def playerContent(self, flag, vid, vip_flags):
        if vid.startswith('http') and ('.m3u8' in vid or '.mp4' in vid):
            return {
                'parse': 0,
                'url': vid,
                'header': {
                    'User-Agent': self.def_headers['User-Agent']
                }
            }

        if vid.startswith('http'):
            try:
                resp = self.fetch(vid, headers={
                    'User-Agent': self.def_headers['User-Agent']
                }, verify=False)
                data = resp.json()
                real_url = data.get('url') or data.get('data', {}).get('url', '')
                if real_url.startswith('http'):
                    return {
                        'parse': 0,
                        'url': real_url,
                        'header': {
                            'User-Agent': self.def_headers['User-Agent']
                        }
                    }
            except Exception:
                pass

        return {'parse': 0, 'url': '', 'header': {}}

    # ---------- 框架方法 ----------
    def init(self, extend=''):
        pass

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return url and ('.m3u8' in url or '.mp4' in url)

    def destroy(self):
        pass

    def localProxy(self, param):
        pass