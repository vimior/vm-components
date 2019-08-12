## Python的一些通用或有趣的库的二次封装，方便使用

### common：通用组件

- #### log：日志组件，单例模式

  ```python
  # 日志组件导入
  from common.log import logger, LOGGET_FMT, LOGGET_DATE_FMT
  
  # 设置日志级别
  logger.setLevel(logger.INFO)
  
  # 设置日志输出到文件
  import logging
  file_handler = logging.FileHandler('test-log.log', mode='w')
  file_handler.setLevel(logging.INFO)
  file_handler.setFormatter(logging.Formatter(LOGGET_FMT, LOGGET_DATE_FMT))
  logger.addHandler(file_handler)
  
  # 日志输出
  logger.verbose('verbose')
  logger.debug('debug')
  logger.info('info')
  logger.success('success')
  logger.warning('warning')
  logger.error('error')
  logger.critical('critical')
  ```

- 