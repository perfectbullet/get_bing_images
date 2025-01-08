import json
import os
import urllib
from bs4 import BeautifulSoup
import re
import time
from loguru import logger
from pypinyin import lazy_pinyin

from download_with_proxy import download_image


def get_start_html(url_template, key, first, load_num, sfx, header):
    # get html object
    ok_url = url_template.format(key, first, load_num, sfx)
    logger.debug('ok_url is {}', ok_url)
    page = urllib.request.Request(ok_url, headers=header)
    html = urllib.request.urlopen(page)
    return html


def get_image_url(html):
    # 从缩略图列表页中找到原图的url，并返回这一页的图片数量
    soup = BeautifulSoup(html, "lxml")
    link_list = soup.find_all("a", class_="iusc")
    image_url_list = []
    # 最多取 count 个
    for link in link_list:
        slink = str(link)
        # result = re.search(rule, slink)
        # mt = re.match('''.*"murl":"(https?://.*\.jpg)","turl\S+''', slink, re.IGNORECASE)
        # mt1 = re.match('''.*"murl":"(https?://\S+jpg)\?auto=webp","turl\S+''', slink, re.IGNORECASE)
        mt = re.match(r'''.*"murl":"(https?://.*\.(?:jpg|jpeg|png))(\?.*)?","turl.*''', slink, re.IGNORECASE)
        if mt is None:
            logger.debug('mt 和 mt1 正则表达式没有匹配到: {}', slink)
            continue
        image_url = mt.group(1)
        # image_url = mt.group(1) if mt is not None else mt1.group(1)
        # logger.debug('get image url {}', image_url)
        image_url_list.append(image_url)
    return image_url_list


def save_image(
        image_url,
        idx,
        key_wd,
        image_dir,
        cache_file='image_cache.json'
):
    logger.debug('image_url is {}', image_url)

    # 加载缓存
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached_urls = json.load(f)
    else:
        cached_urls = {}

    # 判断是否已下载
    if image_url in cached_urls:
        logger.debug("image already downloaded: {}", image_url)
        return True
    try:
        # \W+: 匹配一个或多个非字母数字字符。
        # re.sub: 用空字符串替换匹配到的部分。
        new_key_wd = re.sub(r'\W+', '', key_wd)
        new_key_wd = chinese_to_pinyin(new_key_wd)

        image_path = os.path.join(image_dir, '{}-{}-{}.{}'.format(new_key_wd, idx, int(time.time()),'jpg'))
        download_image(image_url, image_path, use_proxy=True)
    except Exception as e:
        logger.error('{} error {}', image_url, e)
        return False
    else:
        logger.info("have saved {} images, image_path: {}", idx, image_path)
        # 更新缓存
        cached_urls[image_url] = image_path
        with open(cache_file, 'w') as f:
            json.dump(cached_urls, f, indent=4)
        return True


def chinese_to_pinyin(text):
    pinyin_list = lazy_pinyin(text)
    return ''.join(pinyin_list)


def main():
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 UBrowser/6.1.2107.204 Safari/537.36'
    }

    url_template = "https://cn.bing.com/images/async?q={0}&first={1}&count={2}&scenario=ImageBasicHover&datsrc=N_I&layout=ColumnBased&mmasync=1&dgState=c*9_y*2226s2180s2072s2043s2292s2295s2079s2203s2094_i*71_w*198&IG=0D6AD6CBAF43430EA716510A4754C951&SFX={3}&iid=images.5599"
    logger.debug('url_template is {}', url_template)
    # url = 'https://cn.bing.com/images/search?q=m1+abrams&qs=HS&form=QBIR&sp=1&lq=0&pq=m1+&sc=10-3&cvid=9A16316DC66446E5A6EE6F8A81C4168B&ghsh=0&ghacc=0&first=1'
    # 需要爬取的图片关键词
    key_wd = "特朗普"
    local_image_dir = os.path.join('images', chinese_to_pinyin(re.sub(r'\W+', '', key_wd)))
    logger.debug('local_image_dir is {}', local_image_dir)
    key = urllib.parse.quote(key_wd)
    first = 1
    load_num = 35
    sfx = 1
    max_sfx = 100
    # 最大照片数量
    max_image_num = 500
    current_image_count = 0
    # 图片保存路径
    os.makedirs(local_image_dir, exist_ok=True)
    while current_image_count < max_image_num and sfx < max_sfx:
        # 获取缩略图列表页
        html = get_start_html(url_template, key, first, load_num, sfx, header)
        image_url_list = get_image_url(html)
        logger.info('image_url_list length is {}, sfx is {}', len(image_url_list), sfx)
        for image_url in image_url_list:
            ok = save_image(image_url, current_image_count, key_wd, local_image_dir)
            if ok:
                current_image_count += 1
        sfx += 1
        first = current_image_count + 1


if __name__ == '__main__':
    main()
