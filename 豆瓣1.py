import requests
import re
from bs4 import BeautifulSoup
import csv
import time

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0",

    'cookie':'bid=h5gOAPnrnsI;_pk_id.100001.4cf6=780ce93c2ea096fa.1791457213.;ll="118099"; _vwo_uuid_v2=D1785156D0E707E2D7AF5643EABF1F784|86a55f8974b6a400cd025ee97971050b; __utmc=30149280; __utmc=223695111;dbcl2="297507449:71MgacL2FRE"; ck=_1-a; _pk_ref.100001.4cf6=%5B%22%22%2C%22%22%2C1791718720%2C%22https%3A%2F%2Faccounts.douban.com%2F%22%5D; _pk_ses.100001.4cf6=1;frodotk_db="c0249ec48f703ecb406ddc4dae50bc61"; __utma=30149280.2015885920.1791457213.1791701099.1791718720.8;__utmb=30149280.0.10.1791718720; __utmz=30149280.1791718720.8.3.utmcsr=accounts.douban.com|utmccn=(referral)|utmcmd=referral|utmcct=/;__utma=223695111.498406097.1791457213.1791701102.1791718720.8; __utmb=223695111.0.10.1791718720; __utmz=223695111.1791718720.8.3.utmcsr=accounts.douban.com|utmccn=(referral)|utmcmd=referral|utmcct=/; push_noty_num=0; push_doumail_num=0'
}

movie_all = []

def get_html(url):
    time.sleep(2)
    resp = requests.get(url, headers=headers)
    resp.encoding = 'utf-8'       
    return resp.text

def safe(node):
    return node.text.strip() if node else ''

#从纯文本里找标签
def field(label, info_text):
    m = re.search(label + r'[::]\s*(.*?)(?:\n|$)', info_text)
    return m.group(1).strip() if m else ''

movie_links = []
for i in range(10):
    page_url = f'https://movie.douban.com/top250?start={i * 25}&filter='
    soup = BeautifulSoup(get_html(page_url), 'lxml')
    for movie in soup.find_all('div', class_='item'):
        rank = movie.find('em').text
        link = movie.find('a')['href']
        movie_links.append((rank, link))

for rank, link in movie_links:
    soup = BeautifulSoup(get_html(link), 'lxml')

    name = safe(soup.find('span', property='v:itemreviewed'))
    year = safe(soup.find('span', class_='year')).strip('()')

    info_div = soup.find('div', id='info')
    info_text = info_div.get_text() if info_div else ''

    director_tag = soup.find('a', attrs={'rel': 'v:directedBy'})
    director = director_tag.text if director_tag else ''

    writer = field('编剧', info_text)

    actors = ' / '.join(a.text for a in soup.find_all('a', attrs={'rel': 'v:starring'}))
    genre = ' / '.join(a.text for a in soup.find_all('span', property='v:genre'))
    dates = ' / '.join(a.text for a in soup.find_all('span', property='v:initialReleaseDate'))

    runtime = safe(soup.find('span', property='v:runtime'))
    rating_num = safe(soup.find('strong', property='v:average'))
    votes = safe(soup.find('span', property='v:votes'))

    star_names = ['五星', '四星', '三星', '两星', '一星']
    stars = {}
    for star_name, per in zip(star_names, soup.find_all('span', class_='rating_per')):
        stars[star_name] = per.text

    summaries = soup.find_all('span', property='v:summary')
    summary = ''.join(line.strip() for line in summaries[-1].get_text().split('\n')) if summaries else ''

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
         '五星', '四星', '三星', '两星', '一星',  '剧情简介']

with open('douban_top250.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=names)
    writer.writeheader()
    writer.writerows(movie_all)


