"""
工具函数
包含距离计算等工具函数
"""

import numpy as np
from math import radians, atan2, sin


def distance(coord_1, coord_2):
    """
    计算两点之间的曼哈顿距离（米）
    
    Args:
        coord_1: (lon, lat) 坐标1
        coord_2: (lon, lat) 坐标2
        
    Returns:
        float: 距离（米）
    """
    lon1, lat1 = map(radians, coord_1)
    lon2, lat2 = map(radians, coord_2)
    
    R = 6371000  # 地球半径 (米)
    
    # 1. 纬度距离 (南北向)：直接差异 * 半径
    dlat = abs(lat2 - lat1)
    lat_dis = dlat * R
    
    # 2. 经度距离 (东西向)：差异 * 半径 * 纬度的余弦值
    dlon = abs(lon2 - lon1)
    # 取平均纬度做缩放系数，这是城市尺度最通用的近似
    avg_lat = (lat1 + lat2) / 2.0
    lon_dis = dlon * R * np.cos(avg_lat)
    
    return lat_dis + lon_dis


def distance_array(coord_1, coord_2):
    """
    批量计算两点之间的曼哈顿距离（米）
    
    Args:
        coord_1: numpy数组，形状为 (n, 2)，每行为 (lon, lat)
        coord_2: numpy数组，形状为 (n, 2)，每行为 (lon, lat)
        
    Returns:
        numpy数组: 距离数组（米）
    """
    # 确保输入是 float 类型
    coord_1 = coord_1.astype(float)
    coord_2 = coord_2.astype(float)
    
    R = 6371000
    
    # 转弧度
    lon1, lat1 = np.radians(coord_1[:, 0]), np.radians(coord_1[:, 1])
    lon2, lat2 = np.radians(coord_2[:, 0]), np.radians(coord_2[:, 1])
    
    # 1. 纬度距离 (南北)
    dlat = np.abs(lat2 - lat1)
    lat_dis = dlat * R
    
    # 2. 经度距离 (东西) - 关键修正
    dlon = np.abs(lon2 - lon1)
    # 使用平均纬度进行修正
    avg_lat = (lat1 + lat2) / 2.0
    lon_dis = dlon * R * np.cos(avg_lat)
    
    # 曼哈顿距离
    return lat_dis + lon_dis

