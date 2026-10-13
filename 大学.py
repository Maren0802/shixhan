from selenium.webdriver import Edge
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from lxml import etree
import csv, time

web = Edge()
wait = WebDriverWait(web, 15)
web.get('https://www.shanghairanking.cn/rankings/bcur/2024')
wait.until(EC.presence_of_all_elements_located((By.XPATH, '//table//tbody/tr')))#表格没渲染出来就停止，防止后面找不到东西报错

#找到单元格文本
def cell(i,path):
    return i.xpath(f'string({path})').strip()

#解析一页的函数
def parse_page(html):
    tree = etree.HTML(html)
    out = []
    for i in tree.xpath('//table//tbody/tr'):
        out.append([
            cell(i, './td[1]'),
            cell(i, './td[2]//span[contains(@class,"name-cn")]')
                or cell(i, './td[2]/div/div[2]/div[1]/div/div/span'),
            cell(i, './td[2]//span[contains(@class,"name-en")]')
                or cell(i, './td[2]/div/div[2]/div[2]/div/span'),
            cell(i, './td[3]'),
            cell(i, './td[5]'),
            cell(i, './td[6]'),
        ])
    return out

#去重
results, seen = [], set()
def collect():
    added = 0
    for row in parse_page(web.page_source):
        if row[1] and row[1] not in seen:
            seen.add(row[1])
            results.append(row)
            added += 1
    return added

page = 1
collect()

#翻页
miss = 0
while True:
    web.execute_script('window.scrollTo(0, document.body.scrollHeight)')#把滚动条滚到指定坐标
    time.sleep(0.5)

    try:
        btn = web.find_element(By.XPATH, '//li[contains(@class,"ant-pagination-next")]')
    except Exception:
        print('未找到下一页按钮，结束'); break

    if 'ant-pagination-disabled' in (btn.get_attribute('class') or ''):
        print('已到最后一页'); break

    prev_first = results[-1][1] if results else ''
    web.execute_script('arguments[0].click()', btn) # JS 强制点击，避免元素被遮挡导致原生 click 报错
    page += 1

    for _ in range(20):
        time.sleep(0.3)
        rows = parse_page(web.page_source)
        if rows and rows[0][1] != prev_first:
            break

    n = collect()
    miss = 0 if n else miss + 1
    #防止程序无限空转
    if miss >= 3:
        print('连续多次无新数据，提前结束'); break
    print(f'第 {page} 页，累计 {len(results)} 条')

web.quit()

with open('university.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['排名', '学校名字', '英文名字', '省份', '评分', '办学层次'])
    w.writerows(results)


