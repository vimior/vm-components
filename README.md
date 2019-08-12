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

- #### config：配置组件

  ```python
  from common.config import DefaultConfig, ConfigTemplate
  
  # 自定义配置类，继承DefaultConfig
  class Config(DefaultConfig):
      def __init__(self, config_file=None, config_type=None, init_config=None, **kwargs):
         super(ConfigExample5, self).__init__(config_file=config_file, config_type=config_type, init_config=init_config, **kwargs)
      
      # 重载on_init方法，初始化配置参数
  	def on_init(self):
          # 使用ConfigTemplate类来初始化节点参数
          self.Genernal = ConfigTemplate(
              debug=False
          )
          # 直接初始化主参数
          self.online = True
  
  # 不加载配置文件
  config = Config()
  config.show()
  # 加载INI配置文件
  config = Config(config_file='config.ini')
  config.show()
  # 加载JSON配置文件
  config = Config(config_file='config.json')
  config.show()
  ```


- 