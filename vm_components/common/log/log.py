#!/usr/bin/env python3
# Software License Agreement (BSD License)
#
# Copyright (c) 2019, Vinmin, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.cub@gmail.com>

import logging
import functools
import sys
import os

# 日志格式
LOGGET_FMT = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - - %(message)s'
LOGGET_DATE_FMT = '%Y-%m-%d %H:%M:%S'


class Logger(logging.Logger):
    """
    自定义日志类，单例模式
    """
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_logger'):
            cls._logger = logging.Logger(__name__)
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(logging.DEBUG)
            stream_handler.setFormatter(logging.Formatter(LOGGET_FMT, LOGGET_DATE_FMT))
            cls._logger.addHandler(stream_handler)
        return cls._logger

logger = Logger()
logger.setLevel(logging.DEBUG)


# 新增日志级别VERBOSE
logging.VERBOSE = 5
logging.addLevelName(logging.VERBOSE, 'VERBOSE')

# 新增日志级别SUCCESS
logging.SUCCESS = 25
logging.addLevelName(logging.SUCCESS, 'SUCCESS')

logger.VERBOSE = logging.VERBOSE
logger.DEBUG = logging.DEBUG
logger.INFO = logging.INFO
logger.SUCCESS = logging.SUCCESS
logger.WARN = logging.WARN
logger.WARNING = logging.WARNING
logger.ERROR = logging.ERROR
logger.CRITICAL = logging.CRITICAL

# 给新增的日志级别VERBOSE和SUCCESS指定对应的方法
logger.verbose = functools.partial(logger.log, logging.VERBOSE)
logger.success = functools.partial(logger.log, logging.SUCCESS)
