"""
核心算法接口抽象类
定义ODDR算法的标准接口，便于替换不同的算法实现
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import pandas as pd


class ODDRAlgorithmInterface(ABC):
    """
    ODDR算法接口抽象类
    
    核心算法需要实现以下方法：
    1. dispatch: 订单-司机匹配
    2. reposition: 司机重定位（可选）
    """
    
    @abstractmethod
    def dispatch(self,
                 wait_requests: pd.DataFrame,
                 driver_table: pd.DataFrame,
                 driver_reward_table: pd.DataFrame,
                 current_time: str,
                 **kwargs) -> List[Tuple[str, str]]:
        """
        订单-司机匹配
        
        Args:
            wait_requests: 等待匹配的订单DataFrame，包含字段：
                - order_id: 订单ID
                - origin_lng, origin_lat: 起点经纬度
                - dest_lng, dest_lat: 终点经纬度
                - immediate_reward: 即时奖励
                - wait_time: 已等待时间
                - maximum_wait_time: 最大等待时间
            driver_table: 司机状态DataFrame，包含字段：
                - driver_id: 司机ID
                - lng, lat: 当前位置经纬度
                - status: 状态（0=空闲，1=服务中）
                - total_idle_time: 累计空闲时间
            driver_reward_table: 司机奖励表DataFrame，包含字段：
                - driver_id: 司机ID
                - num_finished_order: 已完成订单数
                - current_overall_reward: 当前累计奖励
            current_time: 当前时间字符串（格式：'YYYY-MM-DD HH:MM:SS'）
            **kwargs: 其他可选参数
            
        Returns:
            List[Tuple[str, str]]: 匹配方案列表，每个元素为 (order_id, driver_id)
        """
        pass
    
    @abstractmethod
    def reposition(self,
                   idle_drivers: pd.DataFrame,
                   current_time: str,
                   **kwargs) -> List[Tuple[str, Tuple[float, float]]]:
        """
        司机重定位（可选实现）
        
        Args:
            idle_drivers: 长时间空闲的司机DataFrame，包含字段：
                - driver_id: 司机ID
                - lng, lat: 当前位置经纬度
            current_time: 当前时间字符串（格式：'YYYY-MM-DD HH:MM:SS'）
            **kwargs: 其他可选参数
            
        Returns:
            List[Tuple[str, Tuple[float, float]]]: 重定位方案列表，每个元素为 (driver_id, (target_lng, target_lat))
        """
        pass
    
    def get_order_driver_pairs(self,
                               wait_requests: pd.DataFrame,
                               driver_table: pd.DataFrame,
                               pickup_dis_threshold: float = 950.0) -> pd.DataFrame:
        """
        获取订单-司机候选对（可选辅助方法）
        
        Args:
            wait_requests: 等待匹配的订单
            driver_table: 司机状态表
            pickup_dis_threshold: 接单距离阈值（米）
            
        Returns:
            DataFrame: 订单-司机候选对，包含字段：
                - driver_id, order_id, order_driver_distance, ...
        """
        # 这个方法可以在子类中重写，提供默认实现
        # 当前返回空DataFrame，由具体算法实现
        return pd.DataFrame()

