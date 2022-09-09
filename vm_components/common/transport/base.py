#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Software License Agreement (BSD License)
#
# Copyright (c) 2019, Vinman, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.cub@gmail.com>

import sys
import math
import logging
from abc import ABCMeta, abstractmethod
from six import with_metaclass


class AbstractTransport(with_metaclass(ABCMeta)):
    def __init__(self, config, logger=None):
        self.config = config
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            # if not self.logger.hasHandlers():
            if not self.logger.handlers:
                stream_hander = logging.StreamHandler(sys.stdout)
                stream_hander.setLevel(logging.DEBUG)
                self.logger.addHandler(stream_hander)
            self.logger.setLevel(logging.DEBUG)

    def connect(self):
        raise NotImplementedError

    def upload_progressbar(self, transferred, toBeTransferred, info=None):
        percent = transferred * 100 // toBeTransferred
        if info['progress'] != percent:
            self.logger.debug(
                'Uploading: [%-50s] %d%%' % ('=' * (percent // 2), percent))
        info['progress'] = percent
        if transferred == toBeTransferred:
            self.logger.info('[Success] upload finish, size={}'.format(toBeTransferred))

    def download_progressbar(self, transferred, toBeTransferred, info=None):
        percent = transferred * 100 // toBeTransferred
        if info['progress'] != percent:
            self.logger.debug(
                'Downloading: [%-50s] %d%%' % ('=' * (percent // 2), percent))
        info['progress'] = percent
        if transferred == toBeTransferred:
            self.logger.info('[Success] download finish, size={}'.format(toBeTransferred))
