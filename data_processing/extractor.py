"""
模块1：数据提取器
从parquet原始数据中提取有效数据，固化为pickle文件
当前版本：构建空的pickle占位
"""

import pickle
import os
from typing import Dict, Any, List, Optional
import pandas as pd
from config.config import Config
from log_utils.logger import Logger
from interface.data_structure import Order # 导入新的Order数据结构

# 初始化 Logger
logger = Logger()


class DataExtractor:
    """数据提取器 - 当前版本仅创建空pickle占位"""
    
    def __init__(self, config: Config):
        """
        初始化数据提取器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.output_dir = config.extractor_output_data_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def extract_from_parquet(self, parquet_path: str, output_name: str, n_rows: int = None) -> str:
        logger.log_info(f"Starting extraction from {parquet_path}", module="extractor")
        """
        从parquet文件提取并过滤订单请求数据，保存为Simulator所需的字典格式pickle。
        Simulator期望的格式：{ 'YYYY-MM-DD': { 'seconds_from_start': [[order_id, lat, lng, ...], ...], ... }, ... }
        
        Args:
            parquet_path: parquet文件路径
            output_name: 输出pickle文件名
            n_rows: 控制只提取前N行数据，为None时提取全部数据
            
        Returns:
            输出pickle文件路径
        """
        output_path = os.path.join(
            self.output_dir,
            f"{output_name}{self.config.extractor_output_pickle_extension}"
        )
        
        # 加载数据，如果指定了 n_rows 则只读取前 N 行
        # 注意：pandas read_parquet 本身不支持 nrows 参数，但我们可以读取后 head(N)
        df = pd.read_parquet(parquet_path)
        if n_rows is not None:
            df = df.head(n_rows)
        
        # 1. 解析时间：将 tpep_pickup_datetime 转换为 datetime 对象
        df['pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
        df['date'] = df['pickup_datetime'].dt.strftime('%Y-%m-%d')
        
        # 2. 计算相对秒数：基于当天的 00:00:00 计算偏移秒数 (Simulator 中的 time_key)
        # 将秒数转换为字符串，代表自当天开始的偏移量
        df['seconds'] = (df['pickup_datetime'].dt.hour * 3600 +
                         df['pickup_datetime'].dt.minute * 60 +
                         df['pickup_datetime'].dt.second)
        # 题目要求：第二层键为时间戳字符串代表自当天开始的秒数（如 '0，60，120'）
        # 这里维持 60s 的步长取整，并转为字符串
        df['time_key'] = (df['seconds'] // 60 * 60).astype(str)
        
        # 3. 构造 Simulator 期望的列表数据，结构参考 Order 数据类
        df_processed = pd.DataFrame()
        df_processed['order_id'] = df.index.astype(int)  # 使用索引作为 ID，并转换为 int
        df_processed['origin_grid_id'] = df['PULocationID']
        df_processed['dest_grid_id'] = df['DOLocationID']
        df_processed['request_time'] = df['seconds'].astype(float)  # 将相对秒数作为请求时间
        df_processed['trip_time'] = (pd.to_datetime(df['tpep_dropoff_datetime']) -
                                     df['pickup_datetime']).dt.total_seconds().astype(float)
        df_processed['price'] = df['total_amount'].astype(float)
        
        # 附加辅助列用于分组
        df_processed['date'] = df['date']
        df_processed['time_key'] = df['time_key']
        
        # 4. 转换为嵌套字典结构，其中包含 Order 对象
        request_all: Dict[str, Dict[str, List[Order]]] = {}
        
        for date, date_group in df_processed.groupby('date'):
            request_all[date] = {}
            for time_key, time_group in date_group.groupby('time_key'):
                orders_list: List[Order] = []
                for _, row in time_group.iterrows():
                    order = Order(
                        order_id=row['order_id'],
                        origin_grid_id=row['origin_grid_id'],
                        dest_grid_id=row['dest_grid_id'],
                        request_time=row['request_time'],
                        max_wait_time=self.config.maximum_wait_time_mean, # cfg中设置的默认最大等待时间
                        trip_time=row['trip_time'],
                        price=row['price'],
                        origin_lng=None,  # 保持为空
                        origin_lat=None,  # 保持为空
                        dest_lng=None,    # 保持为空
                        dest_lat=None     # 保持为空
                    )
                    orders_list.append(order)
                request_all[date][time_key] = orders_list
        
        # 保存为 pickle
        with open(output_path, 'wb') as f:
            pickle.dump(request_all, f)
        
        logger.log_info(f"Extraction complete. Data saved to: {output_path}", module="extractor")
        logger.log_statistics(f"Extracted statistics for {output_name}:", module="extractor")
        for date, times in request_all.items():
            total_orders = sum(len(orders) for orders in times.values())
            logger.log_statistics(f"  Date: {date} | Time slots: {len(times)} | Total orders: {total_orders}", module="extractor")
            
        logger.log_debug(f"Full extracted data structure preview for {output_name}", data=request_all, module="extractor") # 包含大量订单对象数据
        return output_path
    