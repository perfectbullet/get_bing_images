import urllib.request
from typing import Any

import requests
from loguru import logger

from get_proxyv2 import get_proxies


def download_with_proxy(image_url, image_path):
    """
    使用代理下载图片
    Args:
        image_url: 图片 URL
        image_path: 保存路径
    """
    proxies_info: dict[str, Any] = get_proxies()
    for proxy in proxies_info:
        logger.info('download_with_proxy proxies is {}, image_url is {}'.format(proxy, image_url))
        response = requests.get(image_url, proxies={'http': proxy, 'https': proxy}, timeout=60)
        if response.status_code == 200:
            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
            logger.info('download_with_proxy successful proxies is {}, image_url is {}'
                        .format(proxy, image_url))
            break
        else:
            logger.debug('download_with_proxy failed proxies is {}, image_url is {}, response.status_code is {}'
                         .format(proxy, image_url, response.status_code))


def download_image(image_url, image_path, use_proxy=True):
    """
    下载图片
    Args:
        image_url: 图片 URL
        image_path: 保存路径
    """
    if use_proxy:
        download_with_proxy(image_url, image_path)
    else:
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()  # 检查请求是否成功
        with open(image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)


if __name__ == '__main__':
    # 示例用法
    image_url = "https://example.com/image.jpg"
    image_path = "local_image.jpg"

    download_with_proxy(image_url, image_path)
