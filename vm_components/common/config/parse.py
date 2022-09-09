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
import json
import logging
import argparse
if sys.version.startswith('2'):
    import ConfigParser as configparser
else:
    import configparser


class ConfigTemplate(object):
    """
    配置模板类，根据字典生成类属性
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DefaultConfig(object):
    """
    加载配置，加载方式如下
        一. 初始化配置
            1. 根据实例初始化时的init_config参数初始化
            2. 通过重载方法on_init进行初始化
        二. 可选，加载配置文件，会覆盖同名参数值
            从INI文件加载或从JSON文件加载
        三. 命令行解析，会覆盖同名参数值
        四. 特殊处理，通过重载on_finish方法实现，一般用于对某些参数做处理 

    INI配置格式如下:
        其中各个节点名（如节点一、节点二）需要通过ConfigTemplate来初始化
        [节点一]
        参数1-1的键 = 参数1-1的值
        ...
        [节点二]
        参数2-1的键 = 参数2-1的值
        ...
         
    JSON配置格式如下:
        其中各个节点名（如节点一、节点二）需要通过ConfigTemplate来初始化
        {
            "节点一": {
                "参数1-1的键": "参数1-1的值",
                ...
            },
            "节点二": {
                "参数2-1的键": "参数2-1的值",
                ...
            },
            ...
        }
    """
    SUPPORT_PARAMS_TYPES = (int, float, str, tuple, list, dict, ConfigTemplate)

    def __init__(self, config_file=None, config_type=None, init_config=None, **kwargs):
        """
        :param config_file: 配置文件路径，可选
            1. 仅支持ini和json配置文件，默认为None，即不加载配置文件
        :param config_type: 指定配置文件类型，可选
            1. 可选值'ini'、'json'、None，默认为None，即根据文件名后缀自动确定
        :param init_config: 初始配置，一般为字典
            1. 只有初始化了的配置才生效（即如果配置aaaa没有初始化则不可使用该配置）
            2. 可以通过重载on_init方法来初始化配置
        :param kwargs: 用于指定一些关键字参数
            logger: 用于统一输出
        """

        # 获取logger
        logger = kwargs.pop('logger', None)
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                stream_hander = logging.StreamHandler(sys.stdout)
                stream_hander.setLevel(logging.DEBUG)
                self.logger.addHandler(stream_hander)
            self.logger.setLevel(logging.DEBUG)

        # 初始化配置
        if not isinstance(init_config, dict):
            init_config = {}
        DefaultConfig.on_init(self, **init_config)
        self.on_init()

        # 加载配置文件
        if config_file and os.path.exists(os.path.abspath(config_file)):
            if isinstance(config_type, str) and config_type.lower() in ['ini', 'json']:
                config_type = config_type.lower()
            else:
                config_type = os.path.splitext(config_file)[1][1:].lower()
            if config_type == 'ini':
                DefaultConfig.__load_ini_cfg(self, config_file)
            elif config_type == 'json':
                DefaultConfig.__load_json_cfg(self, config_file)

        # 解析命令行参数
        DefaultConfig.__load_argv(self)

        # 配置的收尾工作
        self.on_finish()

    def on_init(self, **kwargs):
        """
        子类继承时，重载该方法，可以初始化参数（包括新增）
        self.val = 123
        self.flag = True
        """
        for k, v in kwargs.items():
            try:
                setattr(self, k, v)
            except:
                pass

    def on_finish(self):
        """
        子类继承时使用，配置完成后调用，一般用于针对特定参数值进行处理
        """
        pass

    def show(self, ignore=True):
        """
        仅仅用于输出当前的配置
        配置名: 配置值, 配置类型
        :param ignore: 是否忽略某些属性，为True时只打印(int, float, str, tuple, list, dict)类型的属性
        """
        # def _show(obj, prefix=''):
        #     for k, v in obj.__dict__.items():
        #         if isinstance(v, ConfigTemplate):
        #             self.logger.debug('{}{}:'.format(prefix, k))
        #             _show(v, prefix + '  ')
        #         else:
        #             if ignore and not isinstance(v, self.SUPPORT_PARAMS_TYPES):
        #                 continue
        #             self.logger.debug('{}{}: {}, {}'.format(prefix, k, v, type(getattr(obj, k))))

        def _show(obj, prefix='self'):
            for k, v in obj.__dict__.items():
                if isinstance(v, ConfigTemplate):
                    _show(v, prefix='{}.{}'.format(prefix, k))
                else:
                    if ignore and not isinstance(v, self.SUPPORT_PARAMS_TYPES):
                        continue
                    self.logger.debug('{}.{}={}, type={}'.format(prefix, k, v, type(getattr(obj, k))))
        _show(self)

    def __load_argv(self):
        """
        命令行参数解析
        
        命令行格式例子，其中各个节点名需要通过ConfigTemplate来初始化
            1. 设置节点下的参数
                --节点名__参数名=参数值
            2. 设置主参数
                --参数名=参数值
        """
        for arg in sys.argv[1:]:
            ret = arg.split('=', 1)
            if len(ret) < 2:
                continue
            k, v = ret
            if k.startswith('--'):
                k = k[2:]
            if not k:
                continue
            if '__' in k:
                tmp = k.split('__', 1)
                if len(tmp) < 2:
                    continue
                k, k2 = tmp
            else:
                k2 = None

            if hasattr(self, k):
                try:
                    obj = getattr(self, k)
                    if isinstance(obj, ConfigTemplate):
                        k = k2
                    else:
                        obj = self
                    k_type = type(getattr(obj, k))
                    if k_type == bool:
                        if v.upper() == 'TRUE':
                            setattr(obj, k, True)
                        else:
                            setattr(obj, k, False)
                    else:
                        setattr(obj, k, k_type(v))
                except Exception as e:
                    self.logger.error('setattr {} error: {}'.format(k, e))

    def __load_ini_cfg(self, config_file):
        """
        从ini文件加载配置配置
        
        1. 会覆盖对应参数的初始值
        2. 加载的配置会被命令行参数修改对应参数的值，但不会修改配置文件里的值
        
        :param config_file: 配置文件
        
        配置格式例子，其中各个节点名（如节点一、节点二）需要通过ConfigTemplate来初始化
        [节点一]
        参数1-1的键 = 参数1-1的值
        ...
        [节点二]
        参数2-1的键 = 参数2-1的值
        ...
        """
        config_file = os.path.abspath(config_file)
        if os.path.exists(config_file):
            self.logger.debug('Load ini config from {}'.format(config_file))
            try:
                parser = configparser.ConfigParser()
                parser.read(config_file)
                for section in parser.sections():
                    if hasattr(self, section):
                        obj = getattr(self, section)
                        if not isinstance(obj, ConfigTemplate):
                            continue
                        for k, v in parser.items(section):
                            if hasattr(obj, k):
                                try:
                                    if getattr(obj, k) is None:
                                        setattr(obj, k, v)
                                    else:
                                        k_type = type(getattr(obj, k))
                                        if k_type == bool:
                                            if v.upper() == 'TRUE':
                                                setattr(obj, k, True)
                                            else:
                                                setattr(obj, k, False)
                                        else:
                                            setattr(obj, k, k_type(v))
                                except Exception as e:
                                    self.logger.error('setattr {} error: {}'.format(k, e))
            except Exception as e:
                self.logger.error(e)
        else:
            self.logger.error('[IniParse] {} not exist'.format(config_file))

    def __load_json_cfg(self, config_file):
        """
        从json文件加载配置配置
        
        1. 会覆盖对应参数的初始值
        2. 加载的配置会被命令行参数修改对应参数的值，但不会修改配置文件里的值
        
        :param config_file: 配置文件
        
        配置格式例子，其中各个节点名（如节点一、节点二）需要通过ConfigTemplate来初始化
        {
            "节点一": {
                "参数1-1的键": "参数1-1的值",
                ...
            },
            "节点二": {
                "参数2-1的键": "参数2-1的值",
                ...
            },
            ...
        }
        """
        config_file = os.path.abspath(config_file)
        if os.path.exists(config_file):
            self.logger.debug('Load json config from {}'.format(config_file))
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f, encoding='utf-8')
                    for section, item in data.items():
                        if hasattr(self, section):
                            obj = getattr(self, section)
                            if not isinstance(obj, ConfigTemplate):
                                continue
                            for k, v in item.items():
                                if hasattr(obj, k):
                                    try:
                                        if getattr(obj, k) is None:
                                            setattr(obj, k, v)
                                        else:
                                            k_type = type(getattr(obj, k))
                                            setattr(obj, k, k_type(v))
                                    except Exception as e:
                                        self.logger.error('setattr {} error: {}'.format(k, e))
            except Exception as e:
                self.logger.error(e)
        else:
            self.logger.error('[JsonParse] {} not exist'.format(config_file))


if __name__ == '__main__':
    class ConfigExample1(DefaultConfig):
        def __init__(self, **kwargs):
            self.argv_1 = 1
            self.argv_2 = 'hello'
            super(ConfigExample1, self).__init__(**kwargs)

    class ConfigExample2(DefaultConfig):
        def __init__(self, **kwargs):
            super(ConfigExample2, self).__init__(**kwargs)

        def on_init(self, **kwargs):
            self.argv_1 = True
            self.argv_2 = (2, 3)

    class ConfigExample3(DefaultConfig):
        def __init__(self, **kwargs):
            super(ConfigExample3, self).__init__(**kwargs)

    class ConfigExample4(DefaultConfig):
        def __init__(self, **kwargs):
            self.Genernal = ConfigTemplate(
                debug=False
            )
            super(ConfigExample4, self).__init__(**kwargs)

    class ConfigExample5(DefaultConfig):
        def __init__(self, **kwargs):
            self.Genernal = ConfigTemplate(
                debug=False
            )
            super(ConfigExample5, self).__init__(**kwargs)


    config1 = ConfigExample1()
    config2 = ConfigExample2()
    config3 = ConfigExample3(init_config={
        'argv_1': [1, 2, 3, 4],
        'argv_2': {
            'aa': 11,
            'bb': 'hello world'
        }
    })
    config4 = ConfigExample4(config_file='config.ini')
    config5 = ConfigExample5(config_file='config.json')

    config1.show()
    print('=' * 100)
    config2.show()
    print('=' * 100)
    config3.show()
    print('=' * 100)
    config4.show()
    print('=' * 100)
    config5.show()
    print('=' * 100)
