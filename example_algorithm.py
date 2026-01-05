"""
示例算法实现
展示如何实现ODDRAlgorithmInterface接口
- dispatch: 就近分配（距离最近的司机分配给订单）
- reposition: 随机分配（随机选择一个网格）
"""

import pandas as pd
import numpy as np
import random
from typing import List, Tuple
from interface.algorithm_interface import ODDRAlgorithmInterface
from environment.utils import distance_array


class ExampleAlgorithm(ODDRAlgorithmInterface):
    """
    示例算法实现
    这是一个简单的示例，实际使用时需要替换为你的核心算法
    """
    
    def __init__(self):
        """初始化算法"""
        pass
    
    def dispatch(self,
                 wait_requests: pd.DataFrame,
                 driver_table: pd.DataFrame,
                 driver_reward_table: pd.DataFrame,
                 current_time: str,
                 **kwargs) -> List[Tuple[str, str]]:
        """
        订单-司机匹配 - 就近分配策略
        
        对每个订单，找到距离起点最近的空闲司机进行匹配
        
        Args:
            wait_requests: 等待匹配的订单
            driver_table: 司机状态表
            driver_reward_table: 司机奖励表
            current_time: 当前时间
            **kwargs: 其他参数（可能包含pickup_dis_threshold等）
            
        Returns:
            List[Tuple[str, str]]: 匹配方案 [(order_id, driver_id), ...]
        """
        # 找到空闲司机
        idle_drivers = driver_table[driver_table['status'] == 0].copy()
        
        if len(wait_requests) == 0 or len(idle_drivers) == 0:
            return []
        
        matches = []
        used_drivers = set()
        
        # 对每个订单，找到距离最近的空闲司机
        for _, order in wait_requests.iterrows():
            order_id = str(order['order_id'])
            order_origin = np.array([[order['origin_lng'], order['origin_lat']]])
            
            # 计算该订单起点到所有空闲司机的距离
            min_distance = float('inf')
            best_driver_id = None
            best_driver_idx = None
            
            # 遍历所有空闲司机
            for idx, (_, driver) in enumerate(idle_drivers.iterrows()):
                driver_id = str(driver['driver_id'])
                
                # 跳过已被使用的司机
                if driver_id in used_drivers:
                    continue
                
                # 计算距离
                driver_loc = np.array([[driver['lng'], driver['lat']]])
                distance = distance_array(order_origin, driver_loc)[0]
                
                # 更新最近司机
                if distance < min_distance:
                    min_distance = distance
                    best_driver_id = driver_id
                    best_driver_idx = idx
            
            # 如果找到可用司机，添加到匹配列表
            if best_driver_id is not None:
                matches.append((order_id, best_driver_id))
                used_drivers.add(best_driver_id)
        
        return matches
    
    def reposition(self,
                   idle_drivers: pd.DataFrame,
                   current_time: str,
                   **kwargs) -> List[Tuple[str, Tuple[float, float]]]:
        """
        司机重定位 - 随机分配策略
        
        对每个空闲司机，随机选择一个经纬度进行重定位
        
        Args:
            idle_drivers: 长时间空闲的司机
            current_time: 当前时间
            **kwargs: 其他参数
            
        Returns:
            List[Tuple[str, Tuple[float, float]]]: 重定位方案 [(driver_id, (target_lng, target_lat)), ...]
        """
        if len(idle_drivers) == 0:
            return []
        
        # 定义一个随机的经纬度范围（示例）
        lng_range = (-74.0, -73.9)
        lat_range = (40.7, 40.8)
        
        # 对每个空闲司机，随机选择一个经纬度
        reposition_plan = []
        for _, driver in idle_drivers.iterrows():
            driver_id = str(driver['driver_id'])
            target_lng = random.uniform(*lng_range)
            target_lat = random.uniform(*lat_range)
            reposition_plan.append((driver_id, (target_lng, target_lat)))
        
        return reposition_plan

