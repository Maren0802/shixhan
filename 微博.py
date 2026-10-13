import csv
import html
import re
import time
import requests

COOKIE = "SCF=AqVOIFyEOWcfQry8zNfYn6t86HInIF4Us4H6wd4egeLUaw8lYmkn-r_hlG0ILx_K1vgKCS6E9mTxX5gEo6Plfzo.; SUB=_2A25HzlsqDeRhGeFP7lMQ8CrLwjqIHXVkotLirDV8PUNbmtAbLWmskW9NQQn-q0ch3LqIs3h2JWLVYDoLBWrXUm0z; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W5rkZa2ZwyZVR0nF3pZZPwo5JpX5KzhUgL.FoMpSK2pehBN1Kq2dJLoIE7LxK.LBo.LB.qLxK.L1KMLBKnLxK-LBo.LB.BLxKBLB.2LB.8jqgpyds8jqBtt; ALF=02_1794226298; SINAGLOBAL=2837672011512.2065.1791634505850; _s_tentry=weibo.com; Apache=4040266890677.1177.1791766670973; ULV=1791766670985:3:3:2:4040266890677.1177.1791766670973:1791706957218"             # 粘贴浏览器复制的 Cookie（没有它爬不到数据）
KEYWORD = "#沁眼所见#"
POST_LIMIT = 200        # 爬多少条博文
POST_PAGES = 15         # 爬取的上限，二百条左右
COMMENT_PAGES = 5       # 每篇博文爬几页评论

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://s.weibo.com/",
    "Cookie": COOKIE,
}
SEARCH_URL = "https://s.weibo.com/weibo"                        # 搜索结果页
COMMENT_URL = "https://weibo.com/ajax/statuses/buildComments"   # 评论接口

#把带标签的文字变成纯文字，去掉标签
def clean(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

#改时间的写法
def format_time(text):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S",
                             time.strptime(text, "%a %b %d %H:%M:%S +0800 %Y"))
    except Exception:
        return text

#用正则从字符串里抠出想要的那一小段
def grab(text, pattern):
    match = re.search(pattern, text, re.S)       # re.S：让点号 . 也能匹配换行
    if not match:
        return ""
    result = match.group(1) if match.groups() else match.group(0)
    return result.strip()

#提取数字
def first_number(text):
    numbers = re.findall(r"\d[\d\.]*[万亿]?\+?", text)
    return numbers[-1] if numbers else "0"

#抓搜索页 HTML
def get_search_html(page):
    resp = requests.get(SEARCH_URL, headers=HEADERS,params={"q": KEYWORD, "page": page}, timeout=10)
    resp.encoding = "utf-8"
    return resp.text

#抓取评论
def get_comments(blog_id, uid, level):
    comments = []
    max_id = 0
    for _ in range(COMMENT_PAGES):
        params = {
            "flow": 1,
            "is_reload": 1,
            "is_show_bulletin": 2,
            "is_mix": 1 if level == 1 else 0,
            "count": 20,
            "id": blog_id,
            "uid": uid,
            "fetch_level": level,
            "locale": "zh-CN",
            "max_id": max_id,
        }
        resp = requests.get(COMMENT_URL, headers=HEADERS, params=params, timeout=10)
        data = resp.json()

        if data.get("ok") != 1 or not data.get("data"):
            break
        comments.extend(data["data"])
        max_id = data.get("max_id") or 0
        if max_id == 0:
            break
        time.sleep(0.5)
    return comments

#解析搜索结果页
def parse_posts(page_html):
    cards = re.split(r'<div class="card-wrap" action-type="feed_list_item"', page_html)[1:]       # 丢掉第一段

    posts = []
    for card in cards:
        card = card.split("<!--/card-wrap-->")[0]           # 先在这里切断，否则数据会串到下一篇博文
        action_bar = card[card.rfind('class="card-act"'):]              # 从最后一个 card-act 开始截取，避免把卡片里"转发的别人的微博"的数字算进来

        forward_text = clean(grab(action_bar, r'<a[^>]*action-type="feed_list_forward"[\s\S]*?</a>'))
        comment_text = clean(grab(action_bar, r'<a[^>]*action-type="feed_list_comment"[\s\S]*?</a>'))
        like_text = grab(action_bar, r'woo-like-count">([^<]*)<')

        kinds = []
        if "media-video" in card:
            kinds.append("视频")
        if "media-piclist" in card:
            kinds.append("图片")

        posts.append({
            "作者": grab(card, r'class="name"[^>]*nick-name="([^"]*)"'),
            "uid": grab(card, r'href="//weibo\.com/(\d+)[^"]*"[^>]*class="name"'),
            "id": grab(card, r'mid="(\d+)"'),
            "时间": re.sub(r"\s*转赞人数.*$", "",
                           grab(card, r'class="from"[\s\S]*?<a[^>]*>\s*([^<]+?)\s*</a>')),
            "内容": clean(grab(card, r'<p class="txt"[^>]*>([\s\S]*?)</p>')),
            "形式": "+".join(kinds) if kinds else "文字",
            "转发数": first_number(forward_text),
            "评论数": first_number(comment_text),
            "点赞数": first_number(like_text),
        })
    return posts

def comment_row(belong, level, comment):
    return [
        belong,
        level,
        comment.get("user", {}).get("screen_name", ""),
        clean(comment.get("text_raw", "")),
        format_time(comment.get("created_at", "")),
        comment.get("source", "").replace("来自", "").strip()
    ]

def main():
    post_file = open("微博博文.csv", "w", newline="", encoding="utf-8-sig")
    comment_file = open("微博评论.csv", "w", newline="", encoding="utf-8-sig")
    post_writer = csv.writer(post_file)
    comment_writer = csv.writer(comment_file)
    post_writer.writerow(["发布者", "发布时间", "微博内容", "形式", "转发数", "评论数", "点赞数"])
    comment_writer.writerow(["所属博文", "评论层级", "评论人", "评论内容", "评论时间", "IP属地"])

    post_count = 0
    seen_ids = set()              # 去重

    for page in range(1, POST_PAGES + 1):
        print(f"===== 第 {page} 页博文（已保存 {post_count} 条）=====")
        posts = parse_posts(get_search_html(page))

        for post in posts:
            # 翻页时同一篇博文可能重复出现，编号见过的就跳过
            if post["id"] in seen_ids:
                continue
            seen_ids.add(post["id"])

            post_writer.writerow([post["作者"], post["时间"], post["内容"],
                                  post["形式"], post["转发数"], post["评论数"], post["点赞数"]])
            post_count += 1
            print(f'  [{post_count}] 博文 [{post["作者"]}] {post["时间"]} {post["形式"]} '
                  f'转{post["转发数"]}/评{post["评论数"]}/赞{post["点赞数"]}')

            if post["评论数"] == "0":
                continue

            belong = f'{post["作者"]}:{post["内容"][:20]}'
            for comment in get_comments(post["id"], post["uid"], level=0):
                comment_writer.writerow(comment_row(belong, "一级", comment))

                if int(comment.get("total_number", 0) or 0) > 0:
                    replies = get_comments(comment["id"], comment["user"]["id"], level=1)
                    if not replies:
                        replies = comment.get("comments") or []
                    for reply in replies:
                        comment_writer.writerow(comment_row(belong, "二级", reply))
            time.sleep(1)
        post_file.flush()
        comment_file.flush()

        if post_count >= POST_LIMIT:
            print(f"已保存 {post_count} 条博文，达到上限，结束翻页")
            break
        time.sleep(1.5)

    post_file.close()
    comment_file.close()
    print(f"全部完成！共 {post_count} 条博文")


if __name__ == "__main__":
    main()
