"""
核心算法接口抽象类
定义ODDR算法的标准接口，便于替换不同的算法实现
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import pandas as pd # Keep for now for request_tables, but ideally should be replaced too
from interface.data_structure import Order, Driver

class ODDRAlgorithmInterface(ABC):
    """
    ODDR算法接口抽象类
    
    核心算法需要实现以下方法：
    1. dispatch: 订单-司机匹配
    2. reposition: 司机重定位（可选）
    """
    
    @abstractmethod
    def dispatch(self,
                 wait_requests: List[Order],
                 drivers: List[Driver],
                #  current_time: str,
                 **kwargs) -> List[Tuple[str, str]]:
        """
        订单-司机匹配
        
        Args:
            wait_requests: 等待匹配的订单List[Order]
            drivers: 司机状态List[Driver]
            **kwargs: 其他可选参数
            
        Returns:
            List[Tuple[str, str]]: 匹配方案列表，每个元素为 (order_id, driver_id)
        """
        pass
    
    @abstractmethod
    def reposition(self,
                   idle_drivers: List[Driver],
                   current_time: str,
                   **kwargs) -> List[Tuple[str, Tuple[float, float]]]:
        """
        司机重定位（可选实现）
        
        Args:
            idle_drivers: 长时间空闲的司机List[Driver]
            current_time: 当前时间字符串（格式：'YYYY-MM-DD HH:MM:SS'）
            **kwargs: 其他可选参数
            
        Returns:
            List[Tuple[str, Tuple[float, float]]]: 重定位方案列表，每个元素为 (driver_id, (target_lng, target_lat))
        """
        pass
