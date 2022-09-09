#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Software License Agreement (BSD License)
#
# Copyright (c) 2019, UFactory, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.wen@ufactory.cc>

import os
import sys
import functools
import paramiko
from paramiko.common import o777, o644
from posixpath import join as urljoin
from collections import Iterable
from .base import AbstractTransport


class SSHTransport(AbstractTransport):
    def __init__(self, config, logger=None):
        """
        SSH通信类
        
        :param config: SSH连接的配置
            {
                'hostname': 主机名,  # 必需
                'port': 端口,  # 默认22
                'username': 用户名,  # 必需
                'password': 密码,  # 非必需，和key_filename二选一
                'key_filename': key_filename,  # 非必需，和password二选一
                'remotePath': sftp默认的远程目录
            }
        :param logger: 指定日志输出
        """
        self._ssh = None
        self._sftp = None
        self._home = None
        super(SSHTransport, self).__init__(config, logger)

    @property
    def ssh(self):
        if self._ssh is None:
            self.connect()
        return self._ssh

    @property
    def sftp(self):
        if self._ssh is None:
            self.connect()
        if self._ssh is not None and self._sftp is None:
            try:
                self._sftp = paramiko.SFTPClient.from_transport(self._ssh.get_transport())
            except Exception as e:
                self.logger.error('sftp connect failed, {}'.format(e))
        return self._sftp

    @property
    def home(self):
        if self._home is None:
            for item in self.exec_command('pwd'):
                if item['stdout']:
                    self._home = item['stdout'][0]
                    break
        return self._home if self._home else '/'

    def connect(self):
        try:
            self.close()
            self._ssh = paramiko.SSHClient()
            if self.config.get('load_system_host_keys', True):
                self._ssh.load_system_host_keys()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh.connect(
                hostname=self.config.get('hostname', self.config.get('host')),
                port=self.config.get('port', 22),
                username=self.config.get('username'),
                password=self.config.get('password', None),
                pkey=self.config.get('pkey', None),
                key_filename=self.config.get('key_filename', None),
                timeout=self.config.get('timeout', None),
                allow_agent=self.config.get('allow_agent', True),
                look_for_keys=self.config.get('look_for_keys', True),
                compress=self.config.get('compress', False),
                sock=self.config.get('sock', None),
                gss_auth=self.config.get('gss_auth', False),
                gss_kex=self.config.get('gss_kex', False),
                gss_deleg_creds=self.config.get('gss_deleg_creds', True),
                gss_host=self.config.get('gss_host', None),
                banner_timeout=self.config.get('banner_timeout', None),
                auth_timeout=self.config.get('auth_timeout', None),
                gss_trust_dns=self.config.get('gss_trust_dns', True),
                passphrase=self.config.get('passphrase', None),
                # disabled_algorithms=self.config.get('disabled_algorithms', None),
            )
            return 0
        except Exception as e:
            self._ssh = None
            self.logger.error('SSH connect failed, {}'.format(e))
            return -1

    def close(self):
        try:
            if self._sftp:
                self._sftp.close()
            if self._ssh:
                self._ssh.close()
        except:
            pass
        finally:
            self._ssh = None
            self._sftp = None
            self._home = None

    def exec_command(self, cmds, **kwargs):
        """
        生成器，执行SSH命令
        
        :param cmds: 命令或命令列表
        :param kwargs: 关键字参数
            bufsize: -1,
            timeout: None,
            get_pty: False,
            environment: None
            password: 执行sudo命令的密码
        :return: {'stdout': [...], 'stderr': [...]}
        """
        password = kwargs.pop('password', self.config.get('password', None))
        if isinstance(cmds, str):
            cmds = [cmds]
        for cmd in cmds:
            if not isinstance(cmd, str):
                self.logger.error('only support string cmd, cmd={}, type={}'.format(cmd, type(cmd)))
                continue
            _cmds = cmd.split(';')
            for i in range(len(_cmds)):
                if _cmds[i].startswith('sudo'):
                    _cmds[i] = 'echo "{}" | sudo -S {}'.format(password, _cmds[i])
            cmd = ';'.join(_cmds)
            count = 3
            while count > 0:
                count -= 1
                try:
                    if self.ssh is None:
                        continue
                    _, stdout, stderr = self.ssh.exec_command(cmd, **kwargs)
                    out_lines = [out.strip() for out in stdout.readlines() if len(out.strip())]
                    err_lines = [out.strip() for out in stderr.readlines() if len(out.strip())]
                    yield {
                        'stdout': out_lines,
                        'stderr': err_lines
                    }
                    break
                except Exception as e:
                    self.logger.error('ExecCmdErr: cmd={}, err={}'.format(cmd, e))
                    self.close()

    def upload(self, file_path, target_filename, subdirectory=None, specific_remote_path=None, callback=-1):
        """
        上传文件
        
        :param file_path: 本地文件路径
        :param target_filename: 远程文件名
        :param subdirectory: 远程子目录
        :param specific_remote_path: 指定远程目录，为None使用config['remotePath']或home目录
        :param callback: 上传进度回调, -1使用默认的
        :return: 
        """
        if specific_remote_path is not None:
            remote_path = specific_remote_path
        else:
            remote_path = self.config.get('remotePath', self.home)
        if subdirectory is not None:
            remote_path = urljoin(remote_path, subdirectory)
        target_path = urljoin(remote_path, target_filename)
        self.logger.info('Start upload from {}'.format(file_path))
        try:
            self.sftp.chdir(remote_path)
        except IOError:
            try:
                self.sftp.mkdir(remote_path)
            except:
                paths = remote_path.split('/')
                remote_path = '/'
                for p in paths:
                    if p:
                        remote_path = urljoin(remote_path, p)
                        try:
                            self.sftp.chdir(remote_path)
                        except IOError:
                            self.sftp.mkdir(remote_path)
            self.sftp.chdir(remote_path)
        if isinstance(callback, Iterable) or callback == -1:
            info = {'progress': -1}
            self.sftp.put(file_path, target_path, callback=callback if isinstance(callback, Iterable) else functools.partial(self.upload_progressbar, info=info))
        else:
            self.sftp.put(file_path, target_path)
        self.logger.info('[Success] upload to {} finish'.format(target_path))

    def download(self, remote_name, file_path, subdirectory=None, specific_remote_path=None, callback=-1):
        """
        下载文件
        
        :param remote_name: 远程文件名字
        :param file_path: 下载保存路径
        :param subdirectory: 远程子目录
        :param specific_remote_path: 远程目录，为None使用config['remotePath']或home目录
        :param callback: 下载进度回调
        :return: 
        """
        if specific_remote_path is not None:
            remote_path = specific_remote_path
        else:
            remote_path = self.config.get('remotePath', self.home)
        if subdirectory is not None:
            remote_path = urljoin(remote_path, subdirectory)
        target_path = urljoin(remote_path, remote_name)
        self.logger.info('Start download from {}'.format(target_path))
        if isinstance(callback, Iterable) or callback == -1:
            info = {'progress': -1}
            self.sftp.get(target_path, file_path, callback=callback if isinstance(callback, Iterable) else functools.partial(self.download_progressbar, info=info))
        else:
            self.sftp.get(target_path, file_path)
        self.logger.info('[Success] download to {} finish'.format(target_path))

    def mkdir(self, path, mode=o777, specific_remote_path=None):
        """
        创建目录
        
        :param path: 目录路径
        :param mode: 权限
        :param specific_remote_path: 指定远程目录, 为None使用config['remotePath']或home目录
        :return: 成功返回0
        """
        if specific_remote_path is not None:
            remote_path = specific_remote_path
        else:
            remote_path = self.config.get('remotePath', self.home)
        target_path = urljoin(remote_path, path)
        try:
            self.sftp.chdir(target_path)
        except IOError:
            try:
                self.sftp.mkdir(target_path, mode=mode)
            except:
                base_path = '/'
                for p in target_path.split('/'):
                    if p:
                        base_path = urljoin(base_path, p)
                        try:
                            self.sftp.chdir(base_path)
                        except IOError:
                            try:
                                self.sftp.mkdir(base_path, mode=mode)
                            except Exception as e:
                                self.logger.error('mkdir {} error: {}'.format(base_path, e))
                                return -1
        try:
            self.sftp.chdir(target_path)
            return 0
        except Exception as e:
            self.logger.error('mkdir->chdir {} error {}'.format(target_path, e))
            return -1

    def chdir(self, path, specific_remote_path=None):
        """
        切换目录
        
        :param path: 目录路径
        :param specific_remote_path: 指定远程目录, 为None使用config['remotePath']或home目录
        :return: 成功返回0
        """
        try:
            if specific_remote_path is not None:
                remote_path = specific_remote_path
            else:
                remote_path = self.config.get('remotePath', '~')
            target_path = urljoin(remote_path, path)
            self.sftp.chdir(target_path)
            return 0
        except Exception as e:
            self.logger.error('chdir error: {}'.format(e))
            return -1

    def listdir(self, path, specific_remote_path=None):
        """
        遍历目录

        :param path: 目录路径
        :param specific_remote_path: 指定远程目录, 为None使用config['remotePath']或home目录
        :return: 成功返回列表，失败返回None
        """
        try:
            if specific_remote_path is not None:
                remote_path = specific_remote_path
            else:
                remote_path = self.config.get('remotePath', self.home)
            target_path = urljoin(remote_path, path)
            return self.sftp.listdir(target_path)
        except Exception as e:
            self.logger.error('listdir error: {}'.format(e))
            return None

    def rmdir(self, path, specific_remote_path=None):
        """
        删除目录

        :param path: 目录路径
        :param specific_remote_path: 指定远程目录, 为None使用config['remotePath']或home目录
        :return: 成功返回0
        """
        try:
            if specific_remote_path is not None:
                remote_path = specific_remote_path
            else:
                remote_path = self.config.get('remotePath', self.home)
            target_path = urljoin(remote_path, path)
            self.sftp.rmdir(target_path)
            return 0
        except Exception as e:
            self.logger.error('rmdir error: {}'.format(e))
            return -1

    def remove(self, path, specific_remote_path=None):
        """
        删除文件

        :param path: 文件路径
        :param specific_remote_path: 指定远程目录, 为None使用config['remotePath']或home目录
        :return: 成功返回0
        """
        try:
            if specific_remote_path is not None:
                remote_path = specific_remote_path
            else:
                remote_path = self.config.get('remotePath', self.home)
            target_path = urljoin(remote_path, path)

            self.sftp.remove(target_path)
            return 0
        except Exception as e:
            self.logger.error('remove error: {}'.format(e))
            return -1

    def rename(self, oldpath, newpath):
        """
        重命名

        :param oldpath: 旧目录绝对路径
        :param newpath: 新目录绝对路径
        :return: 成功返回0
        """
        try:
            self.sftp.rename(oldpath, newpath)
            return 0
        except Exception as e:
            self.logger.error('rename error: {}'.format(e))
            return -1

    def chmod(self, path, mode=o777, specific_remote_path=None):
        """
        设置权限

        :param path: 文件路径
        :param mode: 权限
        :param specific_remote_path: 指定远程目录, 为None使用config['remotePath']或home目录
        :return: 成功返回0
        """
        try:
            if specific_remote_path is not None:
                remote_path = specific_remote_path
            else:
                remote_path = self.config.get('remotePath', self.home)
            target_path = urljoin(remote_path, path)

            self.sftp.chmod(target_path, mode)
            return 0
        except Exception as e:
            self.logger.error('chmod error: {}'.format(e))
            return -1

    def chown(self, path, uid, gid, specific_remote_path=None):
        """
        更改所属用户和组
        
        :param path: 文件路径
        :param uid: 用户uid
        :param gid: 用户gid
        :param specific_remote_path: 指定远程目录, 为None使用config['remotePath']或home目录
        :return: 成功返回0
        """
        try:
            if specific_remote_path is not None:
                remote_path = specific_remote_path
            else:
                remote_path = self.config.get('remotePath', self.home)
            target_path = urljoin(remote_path, path)

            self.sftp.chown(target_path, uid, gid)
            return 0
        except Exception as e:
            self.logger.error('chown error: {}'.format(e))
            return -1


if __name__ == '__main__':
    transport = SSHTransport({
        'hostname': '192.168.1.211',
        'port': 22,
        'username': 'xxxxxx',
        'password': 'xxxxxx'
    })

    print(transport.listdir('.'))

