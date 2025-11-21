# -*- coding: utf-8 -*-
# by @汤圆
import sys
import re
import base64
import json
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        return "xlys02"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = "https://www.xlys02.com"
    search_host = "https://www.ymck.pro"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="134", "Google Chrome";v="134"',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'referer': f'{host}/'
    }

    def homeContent(self, filter):
        data = self.getpq()
        result = {}
        
        # 获取分类
        classes = []
        classes.append({'type_name': '电影', 'type_id': '0'})
        classes.append({'type_name': '电视剧', 'type_id': '1'})
        classes.append({'type_name': '大陆剧', 'type_id': '1&area=中国大陆'})
        
        # 获取推荐列表
        videos = self.parse_cards(data('.card.card-sm.card-link'))
        
        result['class'] = classes
        result['list'] = videos
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        # 分类页面解析
        if '&area=' in tid:
            # 处理大陆剧等带参数的分类
            base_tid = tid.split('&')[0]
            area = tid.split('area=')[1]
            url = f"{self.host}/s/all/{pg}?type={base_tid}&area={area}"
        else:
            url = f"{self.host}/s/all/{pg}?type={tid}"
        
        data = self.getpq(url)
        result = {}
        
        videos = self.parse_cards(data('.card.card-sm.card-link'))
        
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        data = self.getpq(ids[0])
        
        # 提取影片标题 - 优化提取逻辑
        vod_name = self.extract_vod_name(data)
        
        # 提取影片基本信息
        vod = {
            'vod_name': vod_name,
            'vod_pic': data('.cover-lg-max-25 img').attr('src') or '',
            'vod_content': self.extract_synopsis(data),
            'vod_play_from': '',
            'vod_play_url': ''
        }
        
        # 提取详细信息
        info_rows = data('.row.mt-3 .col.mb-2 p')
        for row in info_rows.items():
            text = row.text()
            if '别名：' in text:
                vod['vod_name'] = vod['vod_name'] or text.replace('别名：', '').strip()
            elif '导演：' in text:
                vod['vod_director'] = text.replace('导演：', '').strip()
            elif '主演：' in text:
                vod['vod_actor'] = text.replace('主演：', '').strip()
            elif '类型：' in text:
                vod['type_name'] = text.replace('类型：', '').strip()
            elif '制片国家/地区：' in text:
                vod['vod_area'] = text.replace('制片国家/地区：', '').strip('[]')
            elif '语言：' in text:
                vod['vod_lang'] = text.replace('语言：', '').strip()
            elif '集数：' in text:
                vod['vod_remarks'] = text.replace('集数：', '').strip()
            elif '摘要：' in text:
                vod['vod_content'] = vod['vod_content'] or text.replace('摘要：', '').strip()
        
        # 提取三种播放线路
        play_lines = []
        play_urls = []
        
        # 1. 在线播放线路
        online_play = self.parse_online_play(data)
        if online_play:
            play_lines.append('在线播放')
            play_urls.append(online_play)
        
        # 2. 电驴下载线路
        ed2k_play = self.parse_ed2k_play(data)
        if ed2k_play:
            play_lines.append('电驴下载')
            play_urls.append(ed2k_play)
        
        # 3. 种子下载线路
        torrent_play = self.parse_torrent_play(data)
        if torrent_play:
            play_lines.append('种子下载')
            play_urls.append(torrent_play)
        
        if play_lines and play_urls:
            vod['vod_play_from'] = '$$$'.join(play_lines)
            vod['vod_play_url'] = '$$$'.join(play_urls)
        
        return {'list': [vod]}

    def extract_vod_name(self, data):
        """提取影片标题"""
        # 优先使用h2标签的内容
        h2_title = data('h2.d-sm-block.d-md-none').text().strip()
        if h2_title:
            return h2_title
        
        # 如果h2为空，使用h1标签并提取《》中的内容
        h1_title = data('h1.d-none.d-md-block').text().strip()
        if h1_title:
            # 尝试从h1中提取《》内的内容
            match = re.search(r'《([^》]+)》', h1_title)
            if match:
                return match.group(1)
            # 如果没有《》，返回整个h1标题
            return h1_title
        
        # 如果都没有，尝试从页面其他位置获取
        return data('h1').text() or ''

    def extract_synopsis(self, data):
        """提取剧情简介"""
        # 从剧情简介折叠区域提取
        synopsis = data('#synopsis .card-body').text().strip()
        if synopsis:
            return synopsis
        
        # 如果没有找到剧情简介，尝试从摘要中获取
        summary = data('.row.mt-3 .col.mb-2 p:contains("摘要：")').text()
        if summary:
            return summary.replace('摘要：', '').strip()
        
        return ''

    def searchContent(self, key, quick, pg="1"):
        """使用聚合API进行搜索，兼容所有视频源"""
        try:
            # 使用ymck.pro的API进行搜索
            search_url = f"https://www.ymck.pro/API/v2.php?q={key}&size=50"
            
            # 发送请求获取BASE64数据
            response = self.fetch(search_url, headers=self.headers)
            base64_data = response.text
            
            # 解码BASE64数据
            decoded_bytes = base64.b64decode(base64_data)
            decoded_str = decoded_bytes.decode('utf-8')
            
            # 解析JSON数据
            search_results = json.loads(decoded_str)
            
            videos = []
            for result in search_results:
                try:
                    website = result.get('website', '')
                    text = result.get('text', '')
                    url = result.get('url', '')
                    icon = result.get('icon', '')
                    tags = result.get('tags', [])
                    
                    # 过滤条件：只保留特定网站的结果
                    target_sites = ['哔滴影视', '修罗', 'bdys', 'BD影视']
                    if any(site in website for site in target_sites):
                        vod_name = text
                        
                        # 如果标题为空，使用网站名称
                        if not vod_name:
                            vod_name = website
                        
                        # 处理URL，确保是完整URL
                        if url and not url.startswith('http'):
                            if url.startswith('//'):
                                url = 'https:' + url
                            elif url.startswith('/'):
                                url = f"https://www.xlys02.com{url}"
                        
                        # 处理图标URL
                        if icon and not icon.startswith('http'):
                            if icon.startswith('//'):
                                icon = 'https:' + icon
                            elif icon.startswith('/'):
                                icon = f"https://www.ymck.pro{icon}"
                        
                        # 生成备注信息
                        vod_remarks = ' '.join(tags) if tags else website
                        
                        if vod_name and url:
                            videos.append({
                                'vod_id': url,
                                'vod_name': vod_name,
                                'vod_pic': icon,
                                'vod_remarks': vod_remarks
                            })
                            
                except Exception as e:
                    print(f"解析搜索结果项失败: {e}")
                    continue
            
            return {'list': videos, 'page': pg}
            
        except Exception as e:
            print(f"搜索失败: {e}")
            # 如果API搜索失败，回退到原来的搜索方式
            return self.fallback_search(key, pg)

    def fallback_search(self, key, pg):
        """备用搜索方法"""
        try:
            search_url = f"{self.search_host}/search.html?wd={key}"
            data = self.getpq(search_url, host=self.search_host)
            
            videos = []
            search_items = data('.search-result-item')
            
            for item in search_items.items():
                try:
                    website_elem = item('.website-name')
                    website_name = website_elem.text() if website_elem else ''
                    
                    img_elem = item('.website-icon img')
                    img_src = img_elem.attr('src') if img_elem else ''
                    
                    target_sites = ['哔滴影视', '修罗', 'bdys']
                    is_target_site = any(site in website_name for site in target_sites) or 'bdys' in img_src
                    
                    if is_target_site:
                        title_elem = item('.title')
                        vod_name = title_elem.text() if title_elem else ''
                        vod_name = re.sub(r'<[^>]+>', '', vod_name).strip()
                        
                        link_elem = item('a')
                        onclick_attr = link_elem.attr('onclick') or ''
                        
                        vod_id = ''
                        if 'href=' in onclick_attr:
                            match = re.search(r"href='([^']*)'", onclick_attr)
                            if match:
                                vod_id = match.group(1)
                        elif 'window.open' in onclick_attr:
                            match = re.search(r"window.open\('([^']*)'", onclick_attr)
                            if match:
                                vod_id = match.group(1)
                        
                        if vod_id and not vod_id.startswith('http'):
                            if vod_id.startswith('/'):
                                vod_id = f"https://www.xlys02.com{vod_id}"
                        
                        vod_pic = ''
                        tags = []
                        tag_elems = item('.tag-name')
                        for tag in tag_elems.items():
                            tags.append(tag.text())
                        
                        vod_remarks = ' '.join(tags) if tags else '搜索结果'
                        
                        if vod_name and vod_id:
                            videos.append({
                                'vod_id': vod_id,
                                'vod_name': vod_name,
                                'vod_pic': vod_pic,
                                'vod_remarks': vod_remarks
                            })
                except Exception as e:
                    print(f"解析备用搜索结果失败: {e}")
                    continue
            
            return {'list': videos, 'page': pg}
        except Exception as e:
            print(f"备用搜索也失败了: {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        # 播放地址解析 - 增强嗅探功能
        try:
            # 如果是相对路径，转换为完整URL
            if id.startswith('/') and not id.startswith('//'):
                if not id.startswith(self.host):
                    id = f"{self.host}{id}"
            
            # 处理电驴链接
            if id.startswith('ed2k://'):
                return {'parse': 0, 'url': id, 'header': self.headers}
            
            # 处理种子链接
            if id.endswith('.torrent'):
                return {'parse': 0, 'url': id, 'header': self.headers}
            
            data = self.getpq(id)
            
            # 增强嗅探：尝试多种方式查找视频地址
            video_url = self.enhanced_video_sniffing(data, id)
            
            if video_url:
                return {'parse': 0, 'url': video_url, 'header': self.headers}
            
            # 如果没有找到直接播放地址，返回原始页面进行解析
            return {'parse': 1, 'url': id, 'header': self.headers}
            
        except Exception as e:
            print(f"解析播放地址失败: {e}")
            return {'parse': 1, 'url': id, 'header': self.headers}

    def enhanced_video_sniffing(self, data, original_url):
        """增强视频嗅探功能"""
        video_url = None
        
        # 1. 查找video标签
        video_elem = data('video source')
        if video_elem:
            video_url = video_elem.attr('src')
            if video_url and not video_url.startswith('http'):
                if video_url.startswith('//'):
                    video_url = 'https:' + video_url
                else:
                    # 相对路径处理
                    base_url = '/'.join(original_url.split('/')[:3])
                    video_url = base_url + ('/' if not video_url.startswith('/') else '') + video_url
        
        # 2. 查找iframe
        if not video_url:
            iframe_elem = data('iframe')
            if iframe_elem:
                video_url = iframe_elem.attr('src')
                if video_url and not video_url.startswith('http'):
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    else:
                        base_url = '/'.join(original_url.split('/')[:3])
                        video_url = base_url + ('/' if not video_url.startswith('/') else '') + video_url
        
        # 3. 查找JavaScript中的播放地址
        if not video_url:
            scripts = data('script')
            for script in scripts.items():
                script_text = script.text()
                if script_text:
                    # 查找m3u8链接
                    m3u8_patterns = [
                        r'["\'](http[^"\']*\.m3u8[^"\']*)["\']',
                        r'url:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                        r'src:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                        r'file:\s*["\']([^"\']*\.m3u8[^"\']*)["\']'
                    ]
                    for pattern in m3u8_patterns:
                        matches = re.findall(pattern, script_text)
                        if matches:
                            video_url = matches[0]
                            break
                    
                    # 查找mp4链接
                    if not video_url:
                        mp4_patterns = [
                            r'["\'](http[^"\']*\.mp4[^"\']*)["\']',
                            r'url:\s*["\']([^"\']*\.mp4[^"\']*)["\']',
                            r'src:\s*["\']([^"\']*\.mp4[^"\']*)["\']'
                        ]
                        for pattern in mp4_patterns:
                            matches = re.findall(pattern, script_text)
                            if matches:
                                video_url = matches[0]
                                break
        
        # 4. 查找data-url等属性
        if not video_url:
            video_elem = data('[data-url]')
            if video_elem:
                video_url = video_elem.attr('data-url')
        
        # 5. 处理相对路径
        if video_url and not video_url.startswith('http'):
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            else:
                base_url = '/'.join(original_url.split('/')[:3])
                video_url = base_url + ('/' if not video_url.startswith('/') else '') + video_url
        
        return video_url

    def localProxy(self, param):
        pass

    def parse_cards(self, cards):
        """通用解析卡片数据方法"""
        videos = []
        for card in cards.items():
            try:
                # 标题
                title_elem = card('.card-title')
                vod_name = title_elem.text() if title_elem else ''
                
                # 链接 - 通用获取a标签的href
                link_elem = card('a')
                vod_id = link_elem.attr('href') if link_elem else ''
                
                # 确保链接是绝对路径
                if vod_id and not vod_id.startswith('http'):
                    vod_id = f"{self.host}{vod_id}"
                
                # 图片 - 先尝试data-src(首页懒加载)，再尝试src(分类页直接加载)
                img_elem = card('img')
                vod_pic = img_elem.attr('data-src') or img_elem.attr('src') or ''
                if vod_pic and not vod_pic.startswith('http'):
                    vod_pic = f"{self.host}{vod_pic}"
                
                # 副标题处理
                # 更新状态
                badge_elem = card('.badge.bg-pink')
                badge_text = badge_elem.text() if badge_elem else ''
                
                # 日期
                date_elem = card('.text-muted')
                date_text = date_elem.text() if date_elem else ''
                
                # 评分
                ribbon_elem = card('.ribbon')
                score_text = ribbon_elem.text() if ribbon_elem else ''
                
                # 拼接副标题
                remarks_parts = []
                if badge_text:
                    remarks_parts.append(badge_text)
                if score_text:
                    remarks_parts.append(score_text)
                if date_text:
                    remarks_parts.append(date_text)
                
                vod_remarks = ' '.join(remarks_parts) if remarks_parts else date_text
                
                if vod_name and vod_id:
                    videos.append({
                        'vod_id': vod_id,
                        'vod_name': vod_name,
                        'vod_pic': vod_pic,
                        'vod_remarks': vod_remarks
                    })
            except Exception as e:
                print(f"解析视频卡片失败: {e}")
                continue
        
        return videos

    def parse_online_play(self, data):
        """解析在线播放列表"""
        play_list = []
        play_buttons = data('#play-list a.btn')
        
        for button in play_buttons.items():
            play_name = button.text().strip()
            play_url = button.attr('href')
            if play_name and play_url:
                if not play_url.startswith('http'):
                    play_url = f"{self.host}{play_url}"
                play_list.append(f"{play_name}${play_url}")
        
        # 按集数正序排列
        play_list = self.sort_episodes(play_list)
        return '#'.join(play_list) if play_list else ''

    def parse_ed2k_play(self, data):
        """解析电驴下载列表"""
        play_list = []
        download_rows = data('#download-list tr')
        
        for row in download_rows.items():
            # 跳过表头
            if row('th').length > 0:
                continue
            
            # 集数名称
            episode_name = row('td').eq(1).text().strip()
            # 电驴链接
            ed2k_link = row('td').eq(2)('a').attr('href')
            
            if episode_name and ed2k_link:
                play_list.append(f"{episode_name}${ed2k_link}")
        
        # 按集数正序排列（反转列表）
        play_list = self.sort_episodes(play_list)
        return '#'.join(play_list) if play_list else ''

    def parse_torrent_play(self, data):
        """解析种子下载列表"""
        play_list = []
        torrent_items = data('#torrent-list .list-group-item')
        
        for item in torrent_items.items():
            # 种子文件名
            torrent_name = item('a code').text().strip()
            # 种子链接
            torrent_url = item('a').attr('href')
            
            if torrent_name and torrent_url:
                if not torrent_url.startswith('http'):
                    torrent_url = f"{self.host}{torrent_url}"
                play_list.append(f"{torrent_name}${torrent_url}")
        
        # 按集数正序排列（反转列表）
        play_list = self.sort_episodes(play_list, is_torrent=True)
        return '#'.join(play_list) if play_list else ''

    def sort_episodes(self, episodes, is_torrent=False):
        """按集数正序排列"""
        if not episodes:
            return []
        
        if is_torrent:
            # 对于种子文件，我们按文件名中的集数范围排序
            def get_episode_range(episode_str):
                # 从种子文件名中提取集数范围，如 "EP01-05" 或 "EP18-21"
                match = re.search(r'EP(\d+)-?(\d+)?', episode_str)
                if match:
                    start_ep = int(match.group(1))
                    end_ep = int(match.group(2)) if match.group(2) else start_ep
                    return start_ep
                return 0
            
            return sorted(episodes, key=lambda x: get_episode_range(x.split('$')[0]))
        else:
            # 对于普通剧集，按集数排序
            def get_episode_number(episode_str):
                # 从集名字符串中提取数字，如 "第1集" -> 1, "第21集" -> 21
                match = re.search(r'第(\d+)集', episode_str)
                if match:
                    return int(match.group(1))
                # 尝试其他格式
                match = re.search(r'(\d+)', episode_str)
                if match:
                    return int(match.group(1))
                return 0
            
            return sorted(episodes, key=lambda x: get_episode_number(x.split('$')[0]))

    def getpq(self, path='', host=None):
        if host is None:
            host = self.host
            
        if path.startswith('http'):
            url = path
        else:
            url = f"{host}{path}" if path else host
        
        try:
            data = self.fetch(url, headers=self.headers).text
            return pq(data)
        except Exception as e:
            print(f"PyQuery解析失败: {str(e)}")
            return pq('')