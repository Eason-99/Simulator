import logging
import os
import sys
import pandas as pd
from typing import Any, Dict, List, Union
from config.config import Config

class Logger:
    """
    日志模块单例类
    提供分级日志控制、控制台同步输出、以及数据截断打印功能。
    """
    _instance = None

    # 日志级别定义 (包含关系：数字越大，包含的信息越多)
    NO_LOG = 0
    INFO = 1        # 一次性信息：执行流程、告警、加载成功等
    STATISTICS = 2  # 阶段性信息：统计信息、循环中的执行流程
    DEBUG = 3       # 详细调试信息

    _LEVEL_MAP = {
        INFO: logging.INFO,        # 映射到标准 logging.INFO
        STATISTICS: logging.INFO,  # 映射到标准 logging.INFO
        DEBUG: logging.DEBUG       # 映射到标准 logging.DEBUG
    }

    _LEVEL_NAMES = {
        INFO: "INFO",
        STATISTICS: "STA",
        DEBUG: "DEBUG"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def init_logger(self, log_file_path: str = "debug.log", level: int = INFO):
        """
        初始化日志系统
        """
        if self._initialized:
            return

        self.log_level = level
        self._logger = logging.getLogger("SimulatorLogger")
        self._logger.setLevel(logging.DEBUG)  # 底层始终开启 DEBUG，由 _log 方法控制过滤
        self._logger.handlers.clear()

        # 格式化器
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s')

        # 文件处理器 (始终输出)
        file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(file_handler)

        # 控制台处理器 (仅在 STATISTICS 和 INFO 级别启用同步输出)
        if self.log_level in [self.STATISTICS, self.INFO]:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)
            self._logger.addHandler(console_handler)

        self._initialized = True

    def set_level(self, config: Config, level: int):
        """动态设置日志级别"""
        self.log_level = level
        # 重新配置处理器（如果需要动态切换控制台输出，可以在这里处理）
        self.init_logger(config=config, level=level) # 传入 config

    def _truncate_data(self, data: Any, max_rows: int = 5) -> str:
        """针对列表、字典、DataFrame 超过 max_rows 条数据时进行截断"""
        if isinstance(data, pd.DataFrame):
            total = len(data)
            if total > max_rows:
                return f"\n(Truncated: Showing first {max_rows} of {total} rows)\n{data.head(max_rows).to_string()}\n..."
            return f"\n{data.to_string()}"
        
        elif isinstance(data, list):
            total = len(data)
            if total > max_rows:
                return f" (Total: {total}, showing first {max_rows}): {str(data[:max_rows])}..."
            return str(data)
        
        elif isinstance(data, dict):
            total = len(data)
            if total > max_rows:
                keys = list(data.keys())
                truncated_dict = {k: data[k] for k in keys[:max_rows]}
                return f" (Total keys: {total}, showing first {max_rows}): {str(truncated_dict)}..."
            return str(data)
        
        return str(data)

    def _log(self, level: int, message: str, data: Any = None, module: str = ""):
        """核心日志记录逻辑"""
        if self.log_level == self.NO_LOG or level > self.log_level:
            return

        final_msg = message
        if data is not None:
            if level == self.DEBUG:
                final_msg = f"{message} | Data: {self._truncate_data(data)}"
            else:
                final_msg = f"{message} | Data: {str(data)}"

        if module:
            final_msg = f"[{module}] {final_msg}"

        py_level = self._LEVEL_MAP.get(level, logging.INFO)
        # 手动添加自定义级别名称前缀以区分
        prefix = f"[{self._LEVEL_NAMES.get(level, 'LOG')}] "
        self._logger.log(py_level, prefix + final_msg)

    def log_statistics(self, message: str, data: Any = None, module: str = ""):
        self._log(self.STATISTICS, message, data, module=module)

    def log_info(self, message: str, data: Any = None, module: str = ""):
        self._log(self.INFO, message, data, module=module)

    def log_debug(self, message: str, data: Any = None, module: str = ""):
        self._log(self.DEBUG, message, data, module=module)

    # --- 迁移自 debug_logger.py 的特定方法 ---

    def log_step_info(self, step_time: str, num_orders: int, num_idle_drivers: int, num_matched_orders: int):
        msg = f"Step Time: {step_time}, Remain Orders: {num_orders}, Idle Drivers: {num_idle_drivers}, Matched Orders: {num_matched_orders}"
        self.log_debug(msg)

    def log_order_driver_info(self, wait_requests: pd.DataFrame, driver_table: pd.DataFrame):
        num_wait_requests = len(wait_requests)
        num_idle_drivers = len(driver_table[driver_table['status'] == 0])
        self.log_debug(f"Waiting requests: {num_wait_requests}, Idle drivers: {num_idle_drivers}")

    def log_driver_states(self, driver_table: pd.DataFrame):
        self.log_debug("Driver States", data=driver_table)

    def log_in_progress_orders(self, matched_requests: pd.DataFrame):
        if matched_requests.empty:
            self.log_debug("No orders currently in progress.")
        else:
            self.log_debug("In-Progress Orders", data=matched_requests)

    # --- 迁移自 inspect_data.py 的特定方法 ---

    def log_dataframe_info(self, df: pd.DataFrame, name: str, file_path: str = ""):
        msg = f"Dataframe Info: [{name}] {file_path}"
        if isinstance(df, pd.DataFrame):
            info = {"shape": df.shape, "columns": list(df.columns)}
            self.log_info(f"{msg} | Meta: {info}")
            self.log_debug(f"{msg} | Full Preview", data=df)
        else:
            self.log_info(f"{msg} | Type: {type(df)}")
