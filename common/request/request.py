#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Software License Agreement (BSD License)
#
# Copyright (c) 2019, Vinman, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.cub@gmail.com>

import os
import sys
import stat
import json
import shutil
import logging
import requests


class Request(object):
    def __init__(self, logger=None):
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.Logger(__name__)
            # if not self.logger.hasHandlers():
            if not self.logger.handlers:
                stream_hander = logging.StreamHandler(sys.stdout)
                stream_hander.setLevel(logging.DEBUG)
                self.logger.addHandler(stream_hander)
            self.logger.setLevel(logging.DEBUG)

    @property
    def headers(self):
        return {
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)',
        }

    def get(self, url, params=None, **kwargs):
        """
        Get请求
        
        :param url: 要请求的URL
        :param params: get请求的查询参数
        :param kwargs: requests.get方法的关键字参数
        :return: (code, r)
            code: 成功返回0，失败返回-1
            r: 成功返回请求对象，失败返回None
        """
        try:
            headers = self.headers
            headers.update(kwargs.pop('headers', {}))
            r = requests.get(url=url, params=params, headers=headers, **kwargs)
            return 0, r
        except Exception as e:
            self.logger.error('requests.get error, {}'.format(e))
            return -1, None

    def post(self, url, data=None, json=None, **kwargs):
        """
        Post请求
        
        :param url: 要请求的URL
        :param data: 要post的数据，需要序列化，和json参数二选一
        :param json: 要post的json数据，不需序列化，和data参数二选一
        :param kwargs: requests.post的关键字参数
        :return: (code, r)
            code: 成功返回0，失败返回-1
            r: 成功返回请求对象，失败返回None
        """
        try:
            headers = self.headers
            headers.update(kwargs.pop('headers', {}))
            return 0, requests.post(url=url, data=data, json=json, headers=headers, **kwargs)
        except Exception as e:
            self.logger.error('requests.post error, {}'.format(e))
            return -1, None

    def get_json_info(self, url, **kwargs):
        """
        请求URL获取JSON数据
        
        :param url: 要请求的url
        :param kwargs: requests.get的关键字参数
        :return: (code, info)
            code: 0表示成功，-1表示请求异常，-2表示状态码不为200，-3表示json数据解析有问题
            info: 字典(失败时info为{})
        """
        code, r = self.get(url, **kwargs)
        if code == 0:
            if r.status_code == 200:
                try:
                    return 0, json.loads(r.text)
                except Exception as e:
                    self.logger.error('json.loads error, {}'.format(e))
                    return -3, {}
                finally:
                    r.close()
            else:
                self.logger.error('get_json_info failed, status_code={}'.format(r.status_code))
                r.close()
                return -2, {}
        return code, {}

    def download(self, url, target_path, target_name=None, use_cache=True):
        """
        下载内容保存到指定路径
        :param url: 要下载的URL
        :param target_path: 保存目标文件夹
        :param target_name: 保存目标文件名，默认使用从URL分割出来的名字
        :param use_cache: 是否使用缓存，即保存的文件路径已经存在则不重新下载，默认为True
        :return: (status，path)
            status: 成功返回True，失败返回False
            path: 成功返回保存的文件路径，失败返回None
        """
        if target_name is None:
            target_name = url.split('/')[-1]
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path)
            except Exception as e:
                self.logger.error('[Failed][Download] make dirs failed: {}'.format(e))
                return False
        target_file_path = os.path.abspath(os.path.join(target_path, target_name))
        code, r = self.get(url, stream=True, timeout=10)
        if code == 0:
            if r.status_code != 200:
                self.logger.error('download failed, status_code={}'.format(r.status_code))
                r.close()
                if os.path.exists(target_file_path):
                    self.logger.info('[Success][Download] use cache {}, no check size'.format(target_name))
                    return True, target_file_path
                return False, None
            length = int(r.headers['Content-Length'])
            if os.path.exists(target_file_path):
                size = os.stat(target_file_path)[stat.ST_SIZE]
                if use_cache and size == length:
                    r.close()
                    self.logger.info('[Success][Download] use cache {}, check size={}'.format(target_name, length))
                    return True, target_file_path
                else:
                    try:
                        os.remove(target_file_path)
                    except Exception as e:
                        self.logger.error('[Failed][Download] remove cache failed before download: {}'.format(e))

            try:
                with open(target_file_path, 'wb') as f:
                    for content in r.iter_content(1024):
                        f.write(content)
            except Exception as e:
                self.logger.error('[Failed][Download] save error: {}'.format(e))
                return False, None
            r.close()
            size = os.stat(target_file_path)[stat.ST_SIZE]
            if length == size:
                self.logger.info('[Success][Download] download {} success, size={}'.format(target_name, length))
                return True, target_file_path
            else:
                self.logger.info('[Failed][Download] download {} failed, {}/{}'.format(target_name, size, length))
                if os.path.exists(target_file_path):
                    try:
                        os.remove(target_file_path)
                    except Exception as e:
                        self.logger.error('[Failed][Download] remove cache failed after download: {}'.format(e))
                return False, None

        else:
            return False, None


if __name__ == '__main__':
    req = Request()

    code, r = req.get('https://baidu.com')
    print(code, r)

    base_url = 'http://192.168.1.19/releases/'
    # base_url = 'http://update.ufactory.cc/releases/'
    code, info = req.get_json_info(base_url + 'xarm/updates.json')
    print(code, info)
    status, path = req.download(base_url + 'xarm/xarmcore/linux/xarmcore-1.0.0',
                                target_path='tmp/xarmcore', target_name='xarmcore')
    print(status, path)


