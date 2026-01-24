"""
配置管理
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class Config:
    """仿真器配置"""

    # --- 全局/通用参数 ---
    # 基础数据目录，所有数据相关的相对路径都以此为基准
    data_base_dir: str = 'data'
    
    data_input_dir: str = os.path.join(
        data_base_dir, 'data_raw'
    ) # 原始数据存放目录
    
    data_processed_dir: str = os.path.join(
        data_base_dir, 'data_processed'
    ) # 处理后数据存放目录

    description: str = 'test' # 用于区分不同的实验结果子目录
    result_data_dir: str = os.path.join(
        data_base_dir, 'data_result', description
    ) # 实验结果存放目录

    # --- 仿真器 (Simulator) 参数 ---
    simulator_requests_data_path: str = os.path.join(
        data_processed_dir, 'yellow_tripdata_2025-01.pickle'
    ) # 订单请求数据路径
    simulator_drivers_data_path: str = os.path.join(
        data_processed_dir, 'df_driver_info.pickle'
    ) # 司机数据路径

    start_date: str = '2025-01-01'
    end_date: str = '2025-01-01'
    start_time: float = 0
    end_time: float = 18640  # 一天的结束时间，单位秒
    delta_t: float = 60  # 时间步长（秒）
    vehicle_speed: float = 6  # 车辆速度（米/秒）
    pickup_dis_threshold: float = 200000  # 接单距离阈值（米）
    maximum_wait_time_mean: float = 300  # 最大等待时间均值（秒）
    max_idle_time: float = 300  # 最大空闲时间（秒）
    num_drivers: int = 100  # 初始化的司机数量

    # --- 提取器 (Extractor) 参数 ---
    extractor_raw_data_dir: str = data_input_dir # 原始数据存放目录
    extractor_output_data_dir: str = data_processed_dir # 提取器输出数据存放目录
    extractor_parquet_filename: str = 'yellow_tripdata_2025-01.parquet' # 原始Parquet文件名
    extractor_output_pickle_basename: str = 'yellow_tripdata_2025-01' # 提取后Pickle文件的基础名
    extractor_output_pickle_extension: str = '.pickle' # 提取后Pickle文件的扩展名

    # --- 预处理器 (Preprocessor) 参数 ---
    preprocessor_input_data_dir: str = data_processed_dir # 预处理器输入数据目录
    preprocessor_output_data_dir: str = data_processed_dir # 预处理器输出数据目录
    preprocessor_input_requests_basename: str = 'yellow_tripdata_2025-01' # 订单请求数据的基础文件名
    preprocessor_input_drivers_basename: str = 'df_driver_info_100' # 司机信息数据的基础文件名 (如果预处理司机数据)
    preprocessor_output_drivers_filename: str = 'df_driver_info.pickle' # 生成的司机初始化文件名
    preprocessor_input_extension: str = '.pickle' # 预处理器输入文件扩展名
    preprocessor_output_suffix: str = '_preprocessed' # 预处理器输出文件后缀
    preprocessor_output_extension: str = '.pickle' # 预处理器输出文件扩展名

    # --- 区域处理器 (TaxiZoneProcessor) 参数 ---
    taxi_zone_shapefile_dir: str = os.path.join(
        data_base_dir, 'data_raw', 'taxi_zones'
    ) # Taxi Zone Shapefile 文件的目录
    taxi_zone_shapefile_name: str = 'taxi_zones.shp' # Shapefile 主文件名
    taxi_zone_centroids_pickle_filename: str = 'zone_centroids.pkl' # 质心数据缓存文件名
    taxi_zone_boundary_pickle_filename: str = 'zone_boundary.pkl' # 边界范围数据缓存文件名

    # --- 日志 (Logger) 参数 ---
    log_level: int = 3  # 0: NO, 1: INFO(flow/warn), 2: STA(stat/loop), 3: DEBUG
    log_file_name: str = 'debug.log' # 日志文件名
    log_output_dir: str = 'debug_logs' # 日志文件存放目录 (相对于工作目录)
    
    # --- 地图 (Map) 参数 ---
    map_hop_adjacency_matrix_csv_path: str = os.path.join(
        data_processed_dir, 'hop_adjacency_matrix_remapped.csv'
    ) # HOP 邻接矩阵 CSV 文件路径
    map_grid_mapping_pickle_path: str = os.path.join(
        data_processed_dir, 'region_id_mapping.pkl'
    ) # 网格ID映射关系 Pickle 文件路径