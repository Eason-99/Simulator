"""
状态管理器
管理司机和订单的状态
"""

import pandas as pd
import numpy as np
from copy import deepcopy
from typing import Dict, Any, List
from interface.data_structure import DriverContext, VehicleStatus # Import DriverContext and VehicleStatus


class StateManager:
    """状态管理器"""
    
    def __init__(self):
        """初始化状态管理器"""
        # 订单列定义
        self.request_columns = [
            'order_id', 'trip_time', 'origin_lng', 'origin_lat', 'dest_lng', 'dest_lat',
            'immediate_reward', 'designed_reward', 't_start', 't_matched', 'pickup_time',
            'wait_time', 't_end', 'status', 'driver_id', 'maximum_wait_time', 'cancel_prob',
            'pickup_distance', 'weight', 'origin_order_num_1h_ago', 'dest_order_num_1h_ago'
        ]
        
    
    def initialize_request_tables(self) -> Dict[str, pd.DataFrame]:
        """
        初始化订单表
        
        Returns:
            Dict: 包含wait_requests和matched_requests的字典
        """
        wait_requests = pd.DataFrame(columns=self.request_columns)
        matched_requests = pd.DataFrame(columns=self.request_columns)
        
        return {
            'wait_requests': wait_requests,
            'matched_requests': matched_requests
        }
    
    def update_driver_state(self,
                            drivers: List[DriverContext],
                            delta_t: float,
                            vehicle_speed: float):
        """
        更新司机状态（时间步进）
        
        Args:
            drivers: 司机对象列表
            delta_t: 时间步长（秒）
            vehicle_speed: 车辆速度（米/秒）
        """
        for driver_context in drivers:
            # 减少剩余时间
            if driver_context.driver.remaining_travel_time is not None:
                driver_context.driver.remaining_travel_time -= delta_t
            
            # 到达目标
            if driver_context.driver.remaining_travel_time <= 0:
                driver_context.driver.remaining_travel_time = 0.0
                # 更新位置到目标位置
                driver_context.driver.lng = driver_context.target_lng
                driver_context.driver.lat = driver_context.target_lat
                
                # 如果之前在服务中，现在变为空闲
                if driver_context.driver.status in [VehicleStatus.PICKING_UP, VehicleStatus.IN_TRIP]:
                    driver_context.driver.status = VehicleStatus.IDLE
                    driver_context.driver.current_order_id = None
                    driver_context.target_lng = driver_context.driver.lng # 目标位置重置为当前位置
                    driver_context.target_lat = driver_context.driver.lat # 目标位置重置为当前位置

            # 空闲司机累计空闲时间
            if driver_context.driver.status == VehicleStatus.IDLE:
                driver_context.total_idle_time += delta_t
            else:
                driver_context.total_idle_time = 0.0 # 不空闲则清零
