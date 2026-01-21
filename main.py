"""
模块3：主程序
调用核心算法接口，分批按时间间隔进行仿真
"""

import os
import sys
import pickle
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from config.config import Config
from data_processing.extractor import DataExtractor
from data_processing.preprocessor import DataPreprocessor
from data_processing.taxi_zone_processor import TaxiZoneSpatialIndexer
from environment.simulator import Simulator
from environment.metrics import MetricsCalculator
from interface.algorithm_interface import ODDRAlgorithmInterface
from interface.result_processor import ResultProcessor
from example_algorithm import ExampleAlgorithm
from log_utils.logger import Logger

# 初始化 Logger
logger = Logger()


def load_data(config: Config) -> tuple:
    """
    加载数据
    
    Args:
        config: 配置对象
        
    Returns:
        tuple: (request_all, driver_info, order_num_origin)
    """
    data_dir = os.path.join(config.data_dir, config.dataset)

    # 加载请求数据
    request_file = os.path.join(data_dir, 'all_requests_0.1.pickle')
    if os.path.exists(request_file):
        with open(request_file, 'rb') as f:
            request_all = pickle.load(f)
        logger.log_info(f"Loaded request data from {request_file}", module="main")
        logger.log_debug(f"Request data preview", data=request_all, module="main")
    else:
        logger.log_info(f"Warning: Request file not found: {request_file}, using empty dict", module="main")
        request_all = {}

    # 加载司机数据
    driver_file = os.path.join(data_dir, 'df_driver_info_100.pickle')
    if os.path.exists(driver_file):
        with open(driver_file, 'rb') as f:
            driver_info = pickle.load(f)
        logger.log_dataframe_info(driver_info, "Driver Info", driver_file, module="main")
    else:
        logger.log_info(f"Warning: Driver file not found: {driver_file}, using empty DataFrame", module="main")
        driver_info = pd.DataFrame()

    # 加载订单数量数据
    order_num_file = os.path.join(data_dir, 'all_requests_0.1_origin_order_num.csv')
    if os.path.exists(order_num_file):
        order_num_origin = pd.read_csv(order_num_file)
        logger.log_dataframe_info(order_num_origin, "Order Number Origin", order_num_file, module="main")
    else:
        logger.log_info(f"Warning: Order num file not found: {order_num_file}, using empty DataFrame", module="main")
        order_num_origin = pd.DataFrame()

    return request_all, driver_info, order_num_origin


def run_simulation(config: Config, algorithm: ODDRAlgorithmInterface):
    """
    运行仿真逻辑
    
    Args:
        config: 配置对象
        algorithm: ODDR算法接口实例
    """
    logger.log_statistics("=" * 50, module="main")
    logger.log_statistics("ODDR Simulator Started", module="main")
    logger.log_statistics("=" * 50, module="main")
    
    # 加载数据
    logger.log_info("[1/5] Loading data...", module="main")
    request_all, driver_info, order_num_origin = load_data(config)
    logger.log_info("Data loaded successfully.", module="main")
    
    # 初始化结果处理器
    result_processor = ResultProcessor()
    
    # 初始化仿真器
    logger.log_info("[2/5] Initializing simulator...", module="main")
    simulator = Simulator(
        request_all=request_all,
        driver_info=driver_info,
        order_num_origin=order_num_origin,
        algorithm=algorithm,
        result_processor=result_processor,
        start_date=config.start_date,
        end_date=config.end_date,
        start_time=config.start_time,
        end_time=config.end_time,
        delta_t=config.delta_t,
        vehicle_speed=config.vehicle_speed,
        pickup_dis_threshold=config.pickup_dis_threshold,
        maximum_wait_time_mean=config.maximum_wait_time_mean,
        max_idle_time=config.max_idle_time,
        request_interval=config.request_interval
    )
    logger.log_info("Simulator initialized.")
    
    # 初始化效果计算器
    metrics_calculator = MetricsCalculator()
    
    # 计算实验日期范围
    start_date = datetime.strptime(config.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(config.end_date, '%Y-%m-%d')
    
    current_date = start_date
    all_metrics = []
    
    logger.log_info("[3/5] Running simulation...")
    
    # 按日期循环
    while current_date <= end_date:
        experiment_date = current_date.strftime('%Y-%m-%d')
        logger.log_info("-" * 30, module="main")
        logger.log_info(f"Experiment Date: {experiment_date}", module="main")
        logger.log_info("-" * 30, module="main")
        
        # 重置环境
        simulator.reset(experiment_date)
        
        # 运行仿真
        logger.log_info(f"Running steps: {simulator.current_step} to {simulator.finish_run_step}", module="main")
        for step in range(simulator.current_step, simulator.finish_run_step):
            if step % 10 == 0:  # 每10步打印一次
                logger.log_statistics(f"  Step {step}/{simulator.finish_run_step} - Time: {simulator.curent_experiment_time}", module="main")
            
            # 执行一个时间步
            simulator.step()
        
        # 将每天的所有已完成订单整合
        simulator.finalize_run()
        
        # 计算每日指标
        logger.log_info(f"[4/5] Calculating metrics for {experiment_date}...", module="main")
        daily_metrics = metrics_calculator.calculate_daily_metrics(
            matched_requests=simulator.matched_requests,
            driver_reward_table=simulator.driver_reward_table,
            num_all_requests=simulator.num_all_requests
        )
        all_metrics.append(daily_metrics)
        
        # 打印每日结果
        logger.log_statistics(f"Daily Result ({experiment_date}):")
        logger.log_statistics(f"  GMV: {daily_metrics['gmv']:.2f}")
        logger.log_statistics(f"  ORR: {daily_metrics['ocr'] * 100:.2f}%")
        logger.log_statistics(f"  Matched: {daily_metrics['num_matched_requests']}/{daily_metrics['num_all_requests']}")
        
        # 保存每日结果
        save_path = os.path.join(config.save_dir, config.dataset, config.description)
        os.makedirs(save_path, exist_ok=True)
        
        # 保存匹配订单
        matched_save_path = os.path.join(save_path, 'matched_requests')
        os.makedirs(matched_save_path, exist_ok=True)
        simulator.matched_requests.to_csv(
            os.path.join(matched_save_path, f'matched_requests_{experiment_date}.csv'),
            index=False
        )
        
        # 保存司机奖励表
        reward_save_path = os.path.join(save_path, 'driver_reward_table')
        os.makedirs(reward_save_path, exist_ok=True)
        simulator.driver_reward_table.to_csv(
            os.path.join(reward_save_path, f'driver_reward_table_{experiment_date}.csv'),
            index=False
        )
        
        # 保存其他信息
        others_save_path = os.path.join(save_path, 'others')
        os.makedirs(others_save_path, exist_ok=True)
        with open(os.path.join(others_save_path, f'others_{experiment_date}.txt'), 'w') as f:
            f.write(f"matched requests num: {daily_metrics['num_matched_requests']}, "
                   f"all requests num: {daily_metrics['num_all_requests']}\n")
        
        current_date += timedelta(days=1)
    
    # 计算总体指标
    logger.log_info("[5/5] Calculating overall metrics...", module="main")
    overall_metrics = {
        'total_gmv': sum(m['gmv'] for m in all_metrics),
        'total_matched': sum(m['num_matched_requests'] for m in all_metrics),
        'total_requests': sum(m['num_all_requests'] for m in all_metrics),
        'avg_ocr': sum(m['ocr'] for m in all_metrics) / len(all_metrics) if len(all_metrics) > 0 else 0.0
    }
    overall_metrics['overall_ocr'] = overall_metrics['total_matched'] / overall_metrics['total_requests'] \
        if overall_metrics['total_requests'] > 0 else 0.0
    
    # 保存总体结果
    save_path = os.path.join(config.save_dir, config.dataset, config.description)
    metrics_calculator.save_metrics(overall_metrics, save_path, 'overall_result.txt')
    
    logger.log_statistics("=" * 50)
    logger.log_statistics("Simulation Complete!")
    logger.log_statistics("=" * 50)
    logger.log_statistics(f"Total GMV: {overall_metrics['total_gmv']:.2f}")
    logger.log_statistics(f"Overall ORR: {overall_metrics['overall_ocr'] * 100:.2f}%")
    logger.log_statistics(f"Total Matched: {overall_metrics['total_matched']}/{overall_metrics['total_requests']}")
    logger.log_statistics("=" * 50)


def run_extractor():
    """1. 执行数据提取器功能"""
    logger.log_info("Running Data Extractor...", module="main")
    raw_dir = "data/data_raw"
    processed_dir = "data/data_processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    extractor = DataExtractor(output_dir=processed_dir)
    parquet_path = os.path.join(raw_dir, "yellow_tripdata_2025-01.parquet")
    
    if os.path.exists(parquet_path):
        extractor.extract_from_parquet(parquet_path, "yellow_tripdata_2025-01")
    else:
        logger.log_info(f"Error: Parquet file not found at {parquet_path}", module="main")


def run_preprocessor():
    """2. 执行数据预处理功能"""
    logger.log_info("Running Data Preprocessor...", module="main")
    processed_dir = "data/data_processed"
    
    preprocessor = DataPreprocessor(input_dir=processed_dir, output_dir=processed_dir)
    input_name = "yellow_tripdata_2025-01"
    
    if os.path.exists(os.path.join(processed_dir, f"{input_name}.pickle")):
        # 默认按原样处理或可以添加采样逻辑
        preprocessor.preprocess(input_name=input_name, suffix="_processed", ratio=1.0)
    else:
        logger.log_info(f"Error: Pickle file not found at {processed_dir}/{input_name}.pickle", module="main")


def run_taxi_zone_processor():
    """3. 执行出租车区域处理器功能"""
    logger.log_info("Running Taxi Zone Processor...", module="main")
    raw_dir = "data/data_raw"
    processed_dir = "data/data_processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    shapefile_dir = os.path.join(raw_dir, "taxi_zones")
    # 使用相对路径技巧让 pickle 存入 processed 目录
    pickle_filename = "../../data_processed/zone_centroids.pkl"
    
    try:
        TaxiZoneSpatialIndexer(shapefile_dir=shapefile_dir, pickle_filename=pickle_filename)
        logger.log_info(f"Taxi zone centroids saved to {processed_dir}/zone_centroids.pkl", module="main")
    except Exception as e:
        logger.log_info(f"Error during taxi zone processing: {e}", module="main")


def main():
    """主入口函数，处理命令行参数"""
    config = Config()
    # 初始化日志，确保所有功能都能使用日志系统
    logger.init_logger(log_file_path=config.log_file, level=config.log_level)
    
    modes = ["extractor", "data_preprocessing", "taxi_zone", "sim"]
    
    # 当没有参数、参数为 help、或参数不符合预期（拼写错误）时，显示指导信息
    if len(sys.argv) < 2 or sys.argv[1] in ['help', '-h', '--help'] or sys.argv[1] not in modes:
        print("\n使用指南 (Guidance):")
        print("用法: python main.py [mode]")
        print("\n可用模式 (Available modes):")
        print("  extractor          - 1. 执行数据提取器功能 (从 data/data_raw 提取 parquet)")
        print("  data_preprocessing - 2. 执行数据预处理功能 (对 data/data_processed 进行预处理)")
        print("  taxi_zone          - 3. 执行出租车区域处理器功能 (处理 data/data_raw 中的区域数据)")
        print("  sim                - 运行仿真主程序 (Simulation)")
        print("\n示例: python main.py sim")
        return

    mode = sys.argv[1]
    
    if mode == "extractor":
        run_extractor()
    elif mode == "data_preprocessing":
        run_preprocessor()
    elif mode == "taxi_zone":
        run_taxi_zone_processor()
    elif mode == "sim":
        algorithm = ExampleAlgorithm()
        run_simulation(config, algorithm)


if __name__ == "__main__":
    main()

