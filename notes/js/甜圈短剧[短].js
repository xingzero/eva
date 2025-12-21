// 自动生成于 7/22/2025, 4:29:59 PM
// 原始文件: 甜圈短剧[短].js

globalThis.h_ost = 'https://mov.cenguigui.cn';
var rule = {
    title: '甜圈短剧[短]',
    host: h_ost,
    searchUrl: '/duanju/api.php?name=**&page=fypage',
    url: '/duanju/api.php?classname=fyclass&offset=fypage',
    headers: {
        'User-Agent': 'okhttp/3.12.11',
    },
    timeout: 5000,
    filterable: 1,
    limit: 20,
    multi: 1,
    searchable: 2,
    play_parse: true,
    search_match: true, //精准搜索
    class_parse: $js.toString(() => {
    let classes = [
    { type_id: '推荐榜', type_name: '🔥推荐榜' },
    { type_id: '新剧', type_name: '🎬新剧' },
    { type_id: '逆袭', type_name: '🎬逆袭' },
    { type_id: '霸总', type_name: '🎬霸总' },
    { type_id: '现代言情', type_name: '🎬现代言情' },
    { type_id: '打脸虐渣', type_name: '🎬打脸虐渣' },
    { type_id: '豪门恩怨', type_name: '🎬豪门恩怨' },
    { type_id: '神豪', type_name: '🎬神豪' },
    { type_id: '马甲', type_name: '🎬马甲' },
    { type_id: '都市日常', type_name: '🎬都市日常' },
    { type_id: '战神归来', type_name: '🎬战神归来' },
    { type_id: '小人物', type_name: '🎬小人物' },
    { type_id: '女性成长', type_name: '🎬女性成长' },
    { type_id: '大女主', type_name: '🎬大女主' },
    { type_id: '穿越', type_name: '🎬穿越' },
    { type_id: '都市修仙', type_name: '🎬都市修仙' },
    { type_id: '强者回归', type_name: '🎬强者回归' },
    { type_id: '亲情', type_name: '🎬亲情' },
    { type_id: '古装', type_name: '🎬古装' },
    { type_id: '重生', type_name: '🎬重生' },
    { type_id: '闪婚', type_name: '🎬闪婚' },
    { type_id: '赘婿逆袭', type_name: '🎬赘婿逆袭' },
    { type_id: '虐恋', type_name: '🎬虐恋' },
    { type_id: '追妻', type_name: '🎬追妻' },
    { type_id: '天下无敌', type_name: '🎬天下无敌' },
    { type_id: '家庭伦理', type_name: '🎬家庭伦理' },
    { type_id: '萌宝', type_name: '🎬萌宝' },
    { type_id: '古风权谋', type_name: '🎬古风权谋' },
    { type_id: '职场', type_name: '🎬职场' },
    { type_id: '奇幻脑洞', type_name: '🎬奇幻脑洞' },
    { type_id: '异能', type_name: '🎬异能' },
    { type_id: '无敌神医', type_name: '🎬无敌神医' },
    { type_id: '古风言情', type_name: '🎬古风言情' },
    { type_id: '传承觉醒', type_name: '🎬传承觉醒' },
    { type_id: '现言甜宠', type_name: '🎬现言甜宠' },
    { type_id: '奇幻爱情', type_name: '🎬奇幻爱情' },
    { type_id: '乡村', type_name: '🎬乡村' },
    { type_id: '历史古代', type_name: '🎬历史古代' },
    { type_id: '王妃', type_name: '🎬王妃' },
    { type_id: '高手下山', type_name: '🎬高手下山' },
    { type_id: '娱乐圈', type_name: '🎬娱乐圈' },
    { type_id: '强强联合', type_name: '🎬强强联合' },
    { type_id: '破镜重圆', type_name: '🎬破镜重圆' },
    { type_id: '暗恋成真', type_name: '🎬暗恋成真' },
    { type_id: '民国', type_name: '🎬民国' },
    { type_id: '欢喜冤家', type_name: '🎬欢喜冤家' },
    { type_id: '系统', type_name: '🎬系统' },
    { type_id: '真假千金', type_name: '🎬真假千金' },
    { type_id: '龙王', type_name: '🎬龙王' },
    { type_id: '校园', type_name: '🎬校园' },
    { type_id: '穿书', type_name: '🎬穿书' },
    { type_id: '女帝', type_name: '🎬女帝' },
    { type_id: '团宠', type_name: '🎬团宠' },
    { type_id: '年代爱情', type_name: '🎬年代爱情' },
    { type_id: '玄幻仙侠', type_name: '🎬玄幻仙侠' },
    { type_id: '青梅竹马', type_name: '🎬青梅竹马' },
    { type_id: '悬疑推理', type_name: '🎬悬疑推理' },
    { type_id: '皇后', type_name: '🎬皇后' },
    { type_id: '替身', type_name: '🎬替身' },
    { type_id: '大叔', type_name: '🎬大叔' },
    { type_id: '喜剧', type_name: '🎬喜剧' },
    { type_id: '剧情', type_name: '🎬剧情' }
        ];
    input = classes;
    }),
    lazy: $js.toString(() => {
        input =  {
            parse: 0,
            url: `https://mov.cenguigui.cn/duanju/api.php?video_id=${input}&type=mp4`
        };
    }),
    一级: $js.toString(() => {
        let d = [];
        let html =  request(input, {
    headers: rule.headers });
        let data = JSON.parse(html).data;
        data.forEach((it) => {
            d.push({
                title: it.title,
                img: it.cover,
                year: it.copyright,
                desc: it.sub_title,
                url: it.book_id
            });
        });
        setResult(d);
    }),
    二级: $js.toString(() => {
        let url = `https://mov.cenguigui.cn/duanju/api.php?book_id=${orId}`;
        let item = JSON.parse( request(url));
         VOD = {
            vod_name: item.book_name,
            type_name: item.category,
            vod_pic: item.book_pic,
            vod_content: item.desc,
            vod_remarks: item.duration,
            vod_year: '更新时间:' + item.time,
            vod_actor: item.author
        };
        let playUrls = item.data.map(item => `${item.title}$${item.video_id}`);
        VOD.vod_play_from = '甜圈短剧';
        VOD.vod_play_url = playUrls.join("#");
        }),
    搜索: $js.toString(() => {
        let d = [];
        let html =  request(input, {headers: rule.headers });
        let data = JSON.parse(html).data;
        if (rule.search_match) {
            data = data.filter(item =>
                item.title &&
                new RegExp(KEY, "i").test(item.title)
            );
        }
        data.forEach((it) => {
            d.push({
                title: it.title,
                img: it.cover,
                year: it.author,
                desc: it.type,
                url: it.book_id
            });
        });
         setResult(d);
    }),
}