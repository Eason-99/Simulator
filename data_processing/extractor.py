"""
模块1：数据提取器
从parquet原始数据中提取有效数据，固化为pickle文件
当前版本：构建空的pickle占位
"""

import pickle
import os
from typing import Dict, Any
import pandas as pd
from log_utils.logger import Logger

# 初始化 Logger
logger = Logger()


class DataExtractor:
    """数据提取器 - 当前版本仅创建空pickle占位"""
    
    def __init__(self, output_dir: str = "data"):
        """
        初始化数据提取器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
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
        output_path = os.path.join(self.output_dir, f"{output_name}.pickle")
        
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
        
        # 3. 构造 Simulator 期望的列表数据
        # Simulator 内部 _generate_new_orders 解析顺序：
        # order_id = request[0]
        # requests = request[1:] -> [origin_lng, origin_lat, dest_lng, dest_lat, immediate_reward, trip_distance, trip_time, designed_reward]
        
        # 映射列名（根据 yellow_tripdata 的标准列名）
        # 如果列名不匹配，请根据 test_parquet_extraction 的输出进行调整
        df_processed = pd.DataFrame()
        df_processed['order_id'] = df.index.astype(str) # 使用索引作为 ID
        df_processed['origin_lng'] = df['PULocationID'] # 简化处理：Parquet通常是ID，Simulator可能需要经纬度
        df_processed['origin_lat'] = df['PULocationID']
        df_processed['dest_lng'] = df['DOLocationID']
        df_processed['dest_lat'] = df['DOLocationID']
        df_processed['immediate_reward'] = df['total_amount']
        df_processed['trip_distance'] = df['trip_distance']
        # 计算 trip_time (秒)
        df_processed['trip_time'] = (pd.to_datetime(df['tpep_dropoff_datetime']) -
                                     df['pickup_datetime']).dt.total_seconds()
        df_processed['designed_reward'] = df['total_amount']
        
        # 附加辅助列用于分组
        df_processed['date'] = df['date']
        df_processed['time_key'] = df['time_key']
        
        # 4. 转换为嵌套字典结构
        request_all = {}
        for date, date_group in df_processed.groupby('date'):
            request_all[date] = {}
            for time_key, time_group in date_group.groupby('time_key'):
                # 转换为 Simulator _generate_new_orders 期望的 list of lists
                # 每个 list 格式: [id, lng, lat, dlng, dlat, reward, dist, time, d_reward]
                data_list = time_group[[
                    'order_id', 'origin_lng', 'origin_lat', 'dest_lng', 'dest_lat',
                    'immediate_reward', 'trip_distance', 'trip_time', 'designed_reward'
                ]].values.tolist()
                request_all[date][time_key] = data_list
        
        # 保存为 pickle
        with open(output_path, 'wb') as f:
            pickle.dump(request_all, f)
        
        logger.log_info(f"Extraction complete. Data saved to: {output_path}", module="extractor")
        logger.log_statistics(f"Extracted statistics for {output_name}:", module="extractor")
        for date, times in request_all.items():
            total_orders = sum(len(orders) for orders in times.values())
            logger.log_statistics(f"  Date: {date} | Time slots: {len(times)} | Total orders: {total_orders}", module="extractor")
            
        logger.log_debug(f"Full extracted data structure preview for {output_name}", data=request_all, module="extractor")
        return output_path
    
    def test_parquet_extraction(self, parquet_path: str):
        """
        测试函数：提取指定parquet文件的前2条数据并按要求打印
        
        Args:
            parquet_path: parquet文件路径
        """
        if not os.path.exists(parquet_path):
            logger.log_info(f"Error: File not found - {parquet_path}", module="extractor")
            return
            
        logger.log_info(f"Testing parquet extraction for {parquet_path}", module="extractor")
        # 读取parquet文件
        df = pd.read_parquet(parquet_path)
        
        # 提取前2条数据
        head_2 = df.head(2)
        
        logger.log_debug(f"Parquet Columns/Rows info for {os.path.basename(parquet_path)}", data=head_2, module="extractor")
        
        logger.log_statistics(f"Parquet Statistics: {os.path.basename(parquet_path)}", module="extractor")
        logger.log_statistics(f"  Total Columns: {len(df.columns)}", module="extractor")
        logger.log_statistics(f"  Total Rows:    {len(df)}", module="extractor")


if __name__ == "__main__":
    # 实例化提取器
    extractor = DataExtractor(output_dir="data")
    
    # 定义目标 parquet 文件路径
    target_parquet = "yellow_tripdata_2025-01.parquet"
    
    # 执行测试函数
    extractor.test_parquet_extraction(target_parquet)


