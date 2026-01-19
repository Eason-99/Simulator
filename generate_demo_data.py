"""
生成演示数据脚本
创建demo数据集，包含若干订单和司机
模拟一个坐标系，默认经纬度范围在北半球西经
生成的文件将保存到config中指定的data_dir/dataset目录
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from environment.utils import distance

# 配置
cfg = {
    "lng_range": (0, 0.008993),   # 经度范围 (默认东经)
    "lat_range": (0, 0.008993),   # 纬度范围 (默认北半球)
    "driver_count": 5,      # 司机数量
    "total_orders": 10,      # 订单总数
    "max_orders_per_interval": 3  # 每个时间间隔的最大订单数
}


def generate_random_coordinates(lng_range, lat_range):
    """
    生成随机经纬度坐标

    Args:
        lng_range: 经度范围 (tuple, e.g., (0, 100))
        lat_range: 纬度范围 (tuple, e.g., (0, 100))

    Returns:
        tuple: 随机生成的经纬度 (lng, lat)
    """
    lng = np.random.uniform(lng_range[0], lng_range[1])
    lat = np.random.uniform(lat_range[0], lat_range[1])
    return lng, lat


def generate_demo_data(config: Config = None):
    """
    生成演示数据

    Args:
        config: 配置对象，如果为None则使用默认配置
    """
    if config is None:
        config = Config()

    # 使用config中的路径配置
    output_dir = os.path.join(config.data_dir, config.dataset)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Using config:")
    print(f"  data_dir: {config.data_dir}")
    print(f"  dataset: {config.dataset}")
    print(f"  Output directory: {output_dir}")

    print("Generating demo data...")

    # 1. 生成订单请求数据 (all_requests_0.1.pickle)
    print("\n[1/2] Generating order requests...")
    request_all = {}

    # 创建一天的订单数据
    date = '2015-07-27'
    request_all[date] = {}

    # 在时间间隔生成订单
    total_orders = cfg["total_orders"]
    max_orders_per_interval = cfg["max_orders_per_interval"]

    current_order_count = 0
    interval_time = 0
    request_all[date][str(interval_time)] = []

    for order_id in range(1, total_orders + 1):
        if current_order_count == max_orders_per_interval:
            interval_time += 60 * 2  # 进入下一个时间间隔
            request_all[date][str(interval_time)] = []
            current_order_count = 0

        origin = generate_random_coordinates(cfg["lng_range"], cfg["lat_range"])
        dest = generate_random_coordinates(cfg["lng_range"], cfg["lat_range"])
        trip_distance = distance(origin, dest)  # 使用 utils 中的 distance 方法计算曼哈顿距离
        trip_time = trip_distance / config.vehicle_speed  # 根据速度计算行程时间
        order = [
            f'order_{order_id:03d}',  # order_id
            origin[0],  # origin_lng
            origin[1],  # origin_lat
            dest[0],  # dest_lng
            dest[1],  # dest_lat
            np.random.uniform(10, 20),  # immediate_reward
            trip_distance,  # trip_distance (米)
            trip_time,  # trip_time (秒)
            np.random.uniform(10, 20),  # designed_reward
        ]
        request_all[date][str(interval_time)].append(order)
        current_order_count += 1

    # 保存订单请求数据
    request_file = os.path.join(output_dir, 'all_requests_0.1.pickle')
    with open(request_file, 'wb') as f:
        pickle.dump(request_all, f)
    print(f"  Saved: {request_file}")
    print(f"  Orders: {total_orders}")

    # 2. 生成司机数据 (df_driver_info_100.pickle)
    print("\n[2/2] Generating driver info...")
    driver_info = pd.DataFrame({
        'driver_id': [f'driver_{i + 1:03d}' for i in range(cfg["driver_count"])],
        'start_time': [0] * cfg["driver_count"],  # 开始时间（秒）
        'end_time': [86400] * cfg["driver_count"],  # 结束时间（秒，24小时）
        'lng': [generate_random_coordinates(cfg["lng_range"], cfg["lat_range"])[0] for _ in range(cfg["driver_count"])],
        'lat': [generate_random_coordinates(cfg["lng_range"], cfg["lat_range"])[1] for _ in range(cfg["driver_count"])],
    })

    driver_file = os.path.join(output_dir, 'df_driver_info_100.pickle')
    with open(driver_file, 'wb') as f:
        pickle.dump(driver_info, f)
    print(f"  Saved: {driver_file}")
    print(f"  Drivers: {cfg["driver_count"]}")

    # 生成订单总数文件 (all_requests_0.1_origin_order_num.csv)
    print("\n[3/3] Generating order total count file...")
    order_num_data = {
        "date": [date],
        "total_orders": [total_orders]
    }
    order_num_df = pd.DataFrame(order_num_data)

    order_num_file = os.path.join(output_dir, 'all_requests_0.1_origin_order_num.csv')
    order_num_df.to_csv(order_num_file, index=False)
    print(f"  Saved: {order_num_file}")
    print(f"  Total orders: {total_orders}")

    print("\n" + "=" * 50)
    print("Demo data generation complete!")
    print("=" * 50)
    print(f"\nData saved to: {output_dir}")
    print(f"\nThis matches the config settings:")
    print(f"  config.data_dir = '{config.data_dir}'")
    print(f"  config.dataset = '{config.dataset}'")
    print("\nSummary:")
    print(f"  - Orders: {total_orders}")
    print(f"  - Drivers: {cfg["driver_count"]}")
    print(f"  - Coordinate system: {cfg["lng_range"]}x{cfg["lat_range"]} (lng, lat between {cfg["lng_range"][0]}-{cfg["lng_range"][1]})")
    print(f"  - Time range: 2015-07-27 00:00 to 23:59 (1 min interval)")


if __name__ == "__main__":
    # 使用默认配置生成demo数据
    # 默认会保存到: data/large/ (根据config.py中的默认值)
    # 如果需要保存到其他位置，可以修改config或传入自定义config对象
    config = Config()
    generate_demo_data(config)