"""
数据检查工具函数
提供打印函数，用于在load_data中每读取一个文件后调用
"""

import pandas as pd
from typing import Any, Dict


def print_request_data(request_all: Dict[str, Any], file_path: str):
    """
    打印订单请求数据的前10行

    Args:
        request_all: 订单请求数据（字典）
        file_path: 文件路径
    """
    print(f"\n[Request Data] {file_path}")
    print("-" * 60)
    if isinstance(request_all, dict):
        print(f"Type: dict")
        all_orders = []
        for date, time_dict in request_all.items():
            if isinstance(time_dict, dict):
                for time_key, orders in time_dict.items():
                    all_orders.extend(orders)
                    if len(all_orders) >= 10:
                        break
            if len(all_orders) >= 10:
                break

        print(f"Total orders found: {len(all_orders)}")
        if len(all_orders) > 0:
            fields = [
                "order_id", "origin_lng", "origin_lat", "dest_lng", "dest_lat",
                "immediate_reward", "trip_distance", "trip_time", "designed_reward"
            ]
            df = pd.DataFrame(all_orders[:10], columns=fields)
            print(df.to_string(index=False))
    else:
        print(f"Type: {type(request_all)}")
    print("-" * 60)


def print_dataframe_info(df: pd.DataFrame, name: str, file_path: str):
    """
    打印DataFrame的前10行和列名

    Args:
        df: DataFrame对象
        name: 数据名称
        file_path: 文件路径
    """
    print(f"\n[{name}] {file_path}")
    print("-" * 60)
    if isinstance(df, pd.DataFrame):
        print(f"Shape: {df.shape}")
        print(f"Column names: {list(df.columns)}")
        if len(df) > 0:
            print(f"\nFirst 10 rows:")
            print(df.head(10).to_string())
        else:
            print("  (Empty DataFrame)")
    else:
        print(f"Type: {type(df)}")
        print(f"Value: {df}")
    print("-" * 60)


def print_driver_info(driver_info: pd.DataFrame, file_path: str):
    """
    打印司机信息

    Args:
        driver_info: 司机信息DataFrame
        file_path: 文件路径
    """
    print_dataframe_info(driver_info, "Driver Info", file_path)


def print_order_num_origin(order_num_origin: pd.DataFrame, file_path: str):
    """
    打印订单数量统计

    Args:
        order_num_origin: 订单数量DataFrame
        file_path: 文件路径
    """
    print_dataframe_info(order_num_origin, "Order Number Origin", file_path)
