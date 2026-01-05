"""
状态管理器
管理司机和订单的状态
"""

import pandas as pd
import numpy as np
from copy import deepcopy
from typing import Dict, Any


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
        
        # 司机列定义
        self.driver_columns = [
            'driver_id', 'start_time', 'end_time', 'lng', 'lat', 'status',
            'target_loc_lng', 'target_loc_lat', 'remaining_time', 'matched_order_id', 'total_idle_time'
        ]
    
    def initialize_driver_table(self, driver_info: pd.DataFrame) -> pd.DataFrame:
        """
        初始化司机表
        
        Args:
            driver_info: 司机信息DataFrame，包含字段：
                - driver_id, start_time, end_time, lng, lat
                
        Returns:
            DataFrame: 初始化后的司机表
        """
        driver_table = deepcopy(driver_info)
        
        # 添加状态字段
        driver_table['status'] = 0  # 0=空闲，1=服务中
        driver_table['target_loc_lng'] = driver_table['lng']
        driver_table['target_loc_lat'] = driver_table['lat']
        driver_table['remaining_time'] = 0
        driver_table['matched_order_id'] = 'None'
        driver_table['total_idle_time'] = 0
        
        return driver_table
    
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
    
    def initialize_driver_reward_table(self, driver_table: pd.DataFrame) -> pd.DataFrame:
        """
        初始化司机奖励表
        
        Args:
            driver_table: 司机表
            
        Returns:
            DataFrame: 司机奖励表
        """
        driver_reward_table = pd.DataFrame(columns=['driver_id', 'num_finished_order', 'current_overall_reward'])
        driver_reward_table['driver_id'] = driver_table['driver_id']
        driver_reward_table['num_finished_order'] = 0
        driver_reward_table['current_overall_reward'] = 0
        
        return driver_reward_table
    
    def update_driver_after_matching(self,
                                     driver_table: pd.DataFrame,
                                     matched_requests: pd.DataFrame,
                                     matched_pairs: pd.DataFrame) -> pd.DataFrame:
        """
        匹配后更新司机状态
        
        Args:
            driver_table: 司机表
            matched_requests: 匹配的订单
            matched_pairs: 匹配对，包含order_id, driver_id, pickup_distance
            
        Returns:
            DataFrame: 更新后的司机表
        """
        # 找到匹配的司机索引
        idle_driver_table = driver_table[driver_table['status'] == 0]
        cor_driver = []
        for driver_id in matched_pairs['driver_id'].values:
            idx = idle_driver_table[idle_driver_table['driver_id'] == driver_id].index
            if len(idx) > 0:
                cor_driver.append(idx[0])
        
        if len(cor_driver) == 0:
            return driver_table
        
        cor_driver = np.array(cor_driver)
        
        # 更新司机状态
        driver_table.loc[cor_driver, 'status'] = 1
        driver_table.loc[cor_driver, 'target_loc_lng'] = matched_requests['dest_lng'].values
        driver_table.loc[cor_driver, 'target_loc_lat'] = matched_requests['dest_lat'].values
        driver_table.loc[cor_driver, 'remaining_time'] = matched_requests['t_end'].values - matched_requests['t_matched'].values
        driver_table.loc[cor_driver, 'matched_order_id'] = matched_requests['order_id'].values
        driver_table.loc[cor_driver, 'total_idle_time'] = 0
        
        return driver_table
    
    def update_driver_state(self,
                            driver_table: pd.DataFrame,
                            delta_t: float,
                            vehicle_speed: float) -> pd.DataFrame:
        """
        更新司机状态（时间步进）
        
        Args:
            driver_table: 司机表
            delta_t: 时间步长（秒）
            vehicle_speed: 车辆速度（米/秒）
            
        Returns:
            DataFrame: 更新后的司机表
        """
        # 减少剩余时间
        driver_table['remaining_time'] = driver_table['remaining_time'].values - delta_t
        
        # 找到到达目标的司机
        loc_negative_time = driver_table['remaining_time'] <= 0
        loc_idle = driver_table['status'] == 0
        loc_on_trip = driver_table['status'] == 1
        
        # 更新到达目标的司机位置
        driver_table.loc[loc_negative_time, 'remaining_time'] = 0
        driver_table.loc[loc_negative_time, 'lng'] = driver_table.loc[loc_negative_time, 'target_loc_lng'].values
        driver_table.loc[loc_negative_time, 'lat'] = driver_table.loc[loc_negative_time, 'target_loc_lat'].values
        
        # 空闲司机累计空闲时间
        driver_table.loc[loc_idle, 'total_idle_time'] += delta_t
        
        # 完成行程的司机状态变为空闲
        driver_table.loc[loc_negative_time & loc_on_trip, 'status'] = 0
        driver_table.loc[loc_negative_time & loc_on_trip, 'matched_order_id'] = 'None'
        
        return driver_table
    
    def update_request_wait_time(self, wait_requests: pd.DataFrame, delta_t: float) -> pd.DataFrame:
        """
        更新等待订单的等待时间
        
        Args:
            wait_requests: 等待订单表
            delta_t: 时间步长（秒）
            
        Returns:
            DataFrame: 更新后的等待订单表
        """
        wait_requests['wait_time'] += delta_t
        return wait_requests

