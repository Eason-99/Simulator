"""
配置管理
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """仿真器配置"""
    # 时间参数
    start_date: str = '2015-07-27'
    end_date: str = '2015-07-27'
    # end_date: str = '2015-07-31'
    start_time: float = 0
    # end_time: float = 86400
    end_time: float = 600
    delta_t: float = 60  # 时间步长（秒）
    
    # 车辆参数
    vehicle_speed: float = 6330  # 车辆速度（米/秒）
    pickup_dis_threshold: float = 200000  # 接单距离阈值（米）
    # pickup_dis_threshold: float = 950  # 接单距离阈值（米）
    
    # 订单参数
    maximum_wait_time_mean: float = 300  # 最大等待时间均值（秒）
    maximum_wait_time_std: float = 0
    request_interval: float = 60  # 订单生成间隔（秒）
    
    # 司机参数
    max_idle_time: float = 300  # 最大空闲时间（秒）
    
    # 数据路径
    dataset: str = 'large'
    data_dir: str = 'data'
    
    # 保存路径
    save_dir: str = 'save'
    description: str = 'test'
    
    # 其他参数
    num_zones: int = 263

