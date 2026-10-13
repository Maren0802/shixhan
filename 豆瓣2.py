import requests
import re
import csv
import time
from lxml import etree

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0",

    'cookie':'bid=h5gOAPnrnsI;_pk_id.100001.4cf6=780ce93c2ea096fa.1791457213.;'
             ' ll="118099"; '
             '_vwo_uuid_v2=D1785156D0E707E2D7AF5643EABF1F784|86a55f8974b6a400cd025ee97971050b; __utmc=30149280; __utmc=223695111;'
             ' dbcl2="297507449:71MgacL2FRE"; ck=_1-a; '
             '_pk_ref.100001.4cf6=%5B%22%22%2C%22%22%2C1791718720%2C%22https%3A%2F%2Faccounts.douban.com%2F%22%5D; _pk_ses.100001.4cf6=1;'
             ' frodotk_db="c0249ec48f703ecb406ddc4dae50bc61"; '
             '__utma=30149280.2015885920.1791457213.1791701099.1791718720.8;'
             ' __utmb=30149280.0.10.1791718720; '
             '__utmz=30149280.1791718720.8.3.utmcsr=accounts.douban.com|utmccn=(referral)|utmcmd=referral|utmcct=/;'
             ' __utma=223695111.498406097.1791457213.1791701102.1791718720.8; '
             '__utmb=223695111.0.10.1791718720;'
             ' __utmz=223695111.1791718720.8.3.utmcsr=accounts.douban.com|utmccn=(referral)|utmcmd=referral|utmcct=/; push_noty_num=0; '
             'push_doumail_num=0'
}

movie_all = []

def get_tree(url):
    time.sleep(2)
    resp = requests.get(url, headers=headers)
    resp.encoding = 'utf-8'
    return etree.HTML(resp.text)

def xp1(tree, expr):
    r = tree.xpath(expr)
    return r[0].strip() if r else ''

#用分隔符拼成字符串
def xp_all(tree, expr, sep=' / '):
    return sep.join(t.strip() for t in tree.xpath(expr))

def field(label, info_text):
    m = re.search(label + r'[::]\s*(.*?)(?:\n|$)', info_text)
    return m.group(1).strip() if m else ''

movie_links = []
for i in range(10):
    page_url = f'https://movie.douban.com/top250?start={i * 25}&filter='
    tree = get_tree(page_url)
    for item in tree.xpath('//div[@class="item"]'):
        rank = xp1(item, './/em/text()')
        link = xp1(item, './/div[@class="pic"]/a/@href')
        movie_links.append((rank, link))

for rank, link in movie_links:
    tree = get_tree(link)

    name = xp1(tree, '//span[@property="v:itemreviewed"]/text()')
    year = xp1(tree, '//span[@class="year"]/text()').strip('()')

    #info整块转纯文本
    info_nodes = tree.xpath('//div[@id="info"]')
    info_text = info_nodes[0].xpath('string(.)') if info_nodes else ''

    director = xp1(tree, '//a[@rel="v:directedBy"]/text()')
    writer = field('编剧', info_text)      #没有专属标签

    actors = xp_all(tree, '//a[@rel="v:starring"]/text()')
    genre = xp_all(tree, '//span[@property="v:genre"]/text()')
    dates = xp_all(tree, '//span[@property="v:initialReleaseDate"]/text()')
    runtime = xp1(tree, '//span[@property="v:runtime"]/text()')

    rating_num = xp1(tree, '//strong[@property="v:average"]/text()')
    votes = xp1(tree, '//span[@property="v:votes"]/text()')

    star_names = ['五星', '四星', '三星', '两星', '一星']
    per_list = tree.xpath('//span[@class="rating_per"]/text()')
    stars = dict(zip(star_names, [p.strip() for p in per_list]))

    #可能有两个v:summary，取最后一个
    summaries = tree.xpath('//span[@property="v:summary"]')
    summary = ''
    if summaries:
        full_text = summaries[-1].xpath('string(.)')
        summary = ''.join(line.strip() for line in full_text.split('\n'))

    country = field('制片国家/地区', info_text)
    language = field('语言', info_text)
    aka = field('又名', info_text)

    movie_all.append({
        '排名': rank,
        '名称': name,
        '年份': year,
        '导演': director,
        '编剧': writer,
        '主演': actors,
        '类型': genre,
        '制片国家/地区': country,
        '语言': language,
        '上映日期': dates,
        '片长': runtime,
        '又名': aka,
        '评分': rating_num,
        '评价人数': votes,
        '五星': stars.get('五星', ''),
        '四星': stars.get('四星', ''),
        '三星': stars.get('三星', ''),
        '两星': stars.get('两星', ''),
        '一星': stars.get('一星', ''),
        '剧情简介': summary,
    })
    print(f'[{rank}/250] {name} 完成')

names = ['排名', '名称', '年份', '导演', '编剧', '主演', '类型', '制片国家/地区',
         '语言', '上映日期', '片长', '又名', '评分', '评价人数',
         '五星', '四星', '三星', '两星', '一星', '剧情简介']

with open('douban_top250-2.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=names)
    writer.writeheader()
    writer.writerows(movie_all)

print('全部完成！')
