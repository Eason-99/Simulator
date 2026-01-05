"""
Debug Logger 模块
提供对 Simulator 各个关键步骤的调试打印功能。
通过在 Simulator 文件头部设置 DEBUG_MODE 开关控制是否启用打印。
"""

import logging
import os

class DebugLogger:
    def __init__(self, debug_mode: bool = False, log_file: str = "debug.log"):
        """
        初始化 DebugLogger

        Args:
            debug_mode (bool): 是否启用调试模式
            log_file (str): 日志文件路径
        """
        self.debug_mode = debug_mode
        self.log_file = log_file

        # 配置日志输出到文件
        logging.basicConfig(
            level=logging.DEBUG if self.debug_mode else logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, mode='w'),
                logging.StreamHandler()
            ]
        )

    def log_step_info(self, step_time: str, num_orders: int, num_idle_drivers: int, num_matched_orders: int):
        """
        打印每一步的关键信息

        Args:
            step_time (str): 当前时间（模拟器时间）
            num_orders (int): 当前剩余订单数
            num_idle_drivers (int): 当前空闲司机数
            num_matched_orders (int): 当前匹配的订单数
        """
        if self.debug_mode:
            logging.debug(f"Step Time: {step_time}, Remain Orders: {num_orders}, Idle Drivers: {num_idle_drivers}, Matched Orders: {num_matched_orders}")
            # logging.debug("--------------------------------------------------")

    def log_custom_message(self, message: str):
        """
        打印自定义调试信息

        Args:
            message (str): 自定义信息
        """
        if self.debug_mode:
            logging.debug(message)

    def log_error(self, error_message: str):
        """
        打印错误信息

        Args:
            error_message (str): 错误信息
        """
        logging.error(error_message)

    def log_warning(self, warning_message: str):
        """
        打印警告信息

        Args:
            warning_message (str): 警告信息
        """
        logging.warning(warning_message)

    def log_info(self, info_message: str):
        """
        打印普通信息

        Args:
            info_message (str): 普通信息
        """
        logging.info(info_message)

    def log_order_driver_info(self, wait_requests, driver_table):
        """
        打印订单-司机候选对的相关信息

        Args:
            wait_requests (pd.DataFrame): 等待订单表
            driver_table (pd.DataFrame): 司机表
        """
        if self.debug_mode:
            num_wait_requests = len(wait_requests)
            num_idle_drivers = len(driver_table[driver_table['status'] == 0])

            logging.debug(f"Number of waiting requests: {num_wait_requests}")
            logging.debug(f"Number of idle drivers: {num_idle_drivers}")

    def log_driver_states(self, driver_table):
        """
        打印所有司机的状态信息

        Args:
            driver_table (pd.DataFrame): 司机表
        """
        if self.debug_mode:
            logging.debug("Driver States:")
            logging.debug("\n" + driver_table.to_string(index=False))
            logging.debug("--------------------------------------------------")