import json
import re
import concurrent.futures
import sys
from typing import Any

import requests
from loguru import logger
from collections import defaultdict

logger.remove()
logger.add(sys.stderr, level="INFO")


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
headers = {
    'User-Agent': USER_AGENT
}

def get_proxies(proxy_path='proxy_listv2.json'):
    with open(proxy_path, 'r', encoding='utf-8') as f:
        proxies = json.load(f)
        return proxies

def fetch_data(tar_url, proxy):
    # 发送GET请求，并打印响应内容
    try:
        proxies = {
            'http': proxy,
            'https': proxy
        }
        response = requests.get(tar_url, headers=headers, proxies=proxies, timeout=60)
        response.raise_for_status()  # 如果请求失败（例如，4xx、5xx），则抛出HTTPError异常
        logger.debug(f"proxy: {proxy}, Status Code: {response.status_code}")
        return {
            'proxy': proxy,
            'tag_url': tar_url,
            'status_code': response.status_code
        }
    except requests.RequestException as e:
        logger.error("proxy: {proxy}, error is: {e}", proxy=proxy, e=e)
        return None


def concurrent_request(proxy_list, tag_urls) -> defaultdict[Any, list]:
    ok_urls = defaultdict(list)
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:  # 你可以根据需要调整max_workers的值
        future_to_url = {executor.submit(fetch_data, tag_url, proxy): (tag_url, proxy) for proxy in proxy_list for tag_url in tag_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            tag_url, proxy = future_to_url[future]
            try:
                # 通过调用future.result()来获取函数的返回值，这会阻塞，直到结果可用
                # 但是请注意，这里我们只是打印结果，没有返回值，所以调用future.result()只是为了等待函数完成
                res = future.result()
                if res and res['status_code'] == 200:
                    ok_urls[res['proxy']].append(res['tag_url'])
                else:
                    logger.debug('not ok tag_url, proxy {}, {}', tag_url, proxy)
            except Exception as exc:
                logger.debug('ok tag_url, proxy {}, {}', tag_url, proxy)
                logger.debug(exc)
    return ok_urls


def save_proxies():
    tag_urls = []
    proxy_list = ['http://127.0.0.1:7890']
    with (open('./proxy_pagesv1.txt', mode='rt', encoding='utf8') as f,
          open('./tag_urls.txt', mode='rt', encoding='utf8') as f2
          ):
        for line in f:
            mt = re.match('(\d+\.\d+\.\d+\.\d+)\t(\d+)\t(\w+)\t.*\t.*\n', line)
            if mt is not None:
                proxy = '{}://{}:{}'.format(mt.group(3).lower(), mt.group(1), mt.group(2))
                proxy_list.append(proxy)
        for line2 in f2:
            tag_urls.append(line2.strip())

    ok_list: defaultdict[Any, list] = concurrent_request(proxy_list, tag_urls)
    if ok_list:
        with open('./proxy_listv2.json', mode='w', encoding='utf8') as f:
            json.dump(ok_list, f, ensure_ascii=False, indent=4)
        with open('./proxy_list.txt', mode='w', encoding='utf8') as f:
            f.write('\n'.join(ok_list.keys()))
        logger.debug('save to proxy list ok')


if __name__ == '__main__':
    # 测试代理ip
    # open https://cn.proxy-tools.com/proxy/https?page=1
    save_proxies()
