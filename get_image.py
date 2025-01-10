import json
import os
import re
import time
import urllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from argparse import ArgumentParser

from bs4 import BeautifulSoup
from loguru import logger
from pypinyin import lazy_pinyin

from download_with_proxy import download_image

lock = Lock()


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
    image_url_list = list(set(image_url_list))
    return image_url_list


def save_image(
        image_url,
        idx,
        key_wd,
        image_dir
):
    logger.debug('image_url is {}', image_url)

    try:
        # \W+: 匹配一个或多个非字母数字字符。
        # re.sub: 用空字符串替换匹配到的部分。
        new_key_wd = re.sub(r'\W+', '', key_wd)
        new_key_wd = chinese_to_pinyin(new_key_wd)

        image_path = os.path.join(image_dir, '{}-{}-{}.{}'.format(new_key_wd, idx, int(time.time()), 'jpg'))
        download_image(image_url, image_path, use_proxy=True)
    except Exception as e:
        logger.error('{} error {}', image_url, e)
        return False, None, image_url
    else:
        logger.info("have saved {} images, image_path: {}", idx, image_path)
        return True, image_path, image_url


def chinese_to_pinyin(text):
    pinyin_list = lazy_pinyin(text)
    return '-'.join(pinyin_list)


def remove_saved_images(image_url_list, cache_file='image_cache.json'):
    new_image_url_list = []
    # 加载缓存
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached_urls = json.load(f)
    else:
        cached_urls = {}
    for image_url in image_url_list:
        # 判断是否已下载
        if image_url not in cached_urls:
            new_image_url_list.append(image_url)
        else:
            if not os.path.exists(cached_urls[image_url]):
                new_image_url_list.append(image_url)
    return new_image_url_list


def update_save_image_cache(image_path, image_url, cache_file='image_cache.json'):
    if os.path.exists(cache_file):
        with lock:
            with open(cache_file, 'r') as f:
                cached_urls = json.load(f)
    else:
        cached_urls = {}
    # 更新缓存
    cached_urls[image_url] = image_path
    with lock:
        with open(cache_file, 'w') as f:
            json.dump(cached_urls, f, indent=4)


def get_bing_image_by_kwd(key_wd, group_dir='.'):
    '''
    通过关键词获取到图片
    :return:
    '''
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 UBrowser/6.1.2107.204 Safari/537.36'
    }

    url_template = "https://cn.bing.com/images/async?q={0}&first={1}&count={2}&scenario=ImageBasicHover&datsrc=N_I&layout=ColumnBased&mmasync=1&dgState=c*9_y*2226s2180s2072s2043s2292s2295s2079s2203s2094_i*71_w*198&IG=0D6AD6CBAF43430EA716510A4754C951&SFX={3}&iid=images.5599"
    logger.debug('url_template is {}', url_template)
    # url = 'https://cn.bing.com/images/search?q=m1+abrams&qs=HS&form=QBIR&sp=1&lq=0&pq=m1+&sc=10-3&cvid=9A16316DC66446E5A6EE6F8A81C4168B&ghsh=0&ghacc=0&first=1'

    local_image_dir = os.path.join('images', group_dir, chinese_to_pinyin(re.sub(r'\W+', '', key_wd)))
    logger.debug('local_image_dir is {}', local_image_dir)
    key = urllib.parse.quote(key_wd)
    first = 1
    load_num = 35
    sfx = 1
    max_sfx = 300
    # 最大照片数量
    max_image_num = 123
    # 图片保存路径
    os.makedirs(local_image_dir, exist_ok=True)
    current_image_count = len(os.listdir(local_image_dir))
    image_url_list = []
    while current_image_count < max_image_num and sfx < max_sfx:
        # 获取缩略图列表页
        html = get_start_html(url_template, key, first, load_num, sfx, header)
        image_url_list.extend(get_image_url(html))
        image_url_list = remove_saved_images(image_url_list)
        logger.info('image_url_list length is {}, sfx is {}', len(image_url_list), sfx)
        if len(image_url_list) < 32:
            continue

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            for idx, image_url in enumerate(image_url_list, start=1):
                fs = executor.submit(save_image, image_url, current_image_count + idx, key_wd, local_image_dir)
                futures[fs] = image_url
            for fs in as_completed(futures):
                ok, image_path, image_url = fs.result()
                if ok:
                    current_image_count += 1
                    update_save_image_cache(image_path, image_url)
            sfx += 1
            first = current_image_count + 1
            image_url_list.clear()
    return local_image_dir


def get_list_kwd(key_wds, group_dir):
    # 按关键词列表, 多线程下载
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for idx, key_wd in enumerate(key_wds):
            fs = executor.submit(get_bing_image_by_kwd, key_wd, group_dir)
            futures[fs] = key_wd
        for fs in as_completed(futures):
            logger.info('get {} images by the key word {} and saved at {}', len(key_wds), key_wd, fs.result())


def get_kwd_v1():
    # 读取关键词
    with open('1980年主要的装甲车和坦克.txt', 'r', encoding='utf-8') as f:
        names = []
        for line in f.readlines():
            line = line.strip()
            name = line.split(',')[-1]
            name = name.split('：')[-1]
            names.append(name)
        return names


def get_kwd_v2(kwd_file):
    # 读取关键词
    with open(kwd_file, 'r', encoding='utf-8') as f:
        names = []
        for line in f.readlines():
            name = line.strip()
            names.append(name)
        return names


if __name__ == '__main__':
    # 需要爬取的图片关键词
    parser = ArgumentParser('get image from bing.com')
    parser.add_argument('--kwd', type=str, required=True)
    args = parser.parse_args()
    key_wds = get_kwd_v2(args.kwd)
    logger.info('key_wds is {}', key_wds)
    get_list_kwd(key_wds, args.kwd.split('.')[0])
