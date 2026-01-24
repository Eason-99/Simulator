"""
模块3：主程序
调用核心算法接口，分批按时间间隔进行仿真
"""

import os
import sys
import pickle
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interface.data_structure import Order, Driver

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


def load_data(config: Config) -> Tuple[Dict[str, Dict[str, List[Order]]], List[Driver]]:
    """
    加载数据
    
    Args:
        config: 配置对象
        
    Returns:
        Tuple: (request_all, driver_info) - request_all现在包含Order对象
    """
    # 加载请求数据
    request_file = config.simulator_requests_data_path
    if os.path.exists(request_file):
        with open(request_file, 'rb') as f:
            request_all = pickle.load(f)
        logger.log_info(f"Loaded request data from {request_file}", module="main")
        logger.log_debug(f"Request data preview", data=request_all, module="main")
    else:
        logger.log_info(f"Warning: Request file not found: {request_file}, using empty dict", module="main")
        request_all = {}

    # 加载司机数据
    driver_file = config.simulator_drivers_data_path
    if os.path.exists(driver_file):
        with open(driver_file, 'rb') as f:
            driver_info = pickle.load(f)
        logger.log_debug(f"Loaded Driver Info from {driver_file}, count {len(driver_info)}", data=driver_info, module="main")
    else:
        logger.log_info(f"Warning: Driver file not found: {driver_file}, using empty DataFrame", module="main")
        driver_info = pd.DataFrame()

    return request_all, driver_info


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
    request_all, driver_info = load_data(config)
    logger.log_info("[1/5] Data loaded successfully.", module="main")
    
    # 初始化结果处理器
    result_processor = ResultProcessor()
    
    # 初始化仿真器
    logger.log_info("[2/5] Initializing simulator...", module="main")
    simulator = Simulator(
        request_all=request_all,
        driver_info=driver_info,
        algorithm=algorithm,
        result_processor=result_processor,
        config=config
    )
    logger.log_info("[2/5] Simulator initialized.")
    
    
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
                logger.log_statistics(f"  Step {step}/{simulator.finish_run_step} - Time: {simulator.time}", module="main")
            
            # 执行一个时间步
            simulator.step()
        
        # 将每天的所有已完成订单整合
        simulator.finalize_run()
        
        # 将每天的所有已完成订单整合并记录指标
        simulator.finalize_run()
        
        current_date += timedelta(days=1)
    
    # 打印总体指标
    logger.log_info("[5/5] Calculating overall metrics...", module="main")
    simulator.log_overall_metrics()
    
    logger.log_statistics("=" * 50)
    logger.log_statistics("Simulation Complete!")
    logger.log_statistics("=" * 50)


def run_extractor(config: Config):
    """1. 执行数据提取器功能"""
    logger.log_info("Running Data Extractor...", module="main")
    raw_dir = config.extractor_raw_data_dir
    processed_dir = config.extractor_output_data_dir
    os.makedirs(processed_dir, exist_ok=True)
    
    extractor = DataExtractor(config=config)
    parquet_path = os.path.join(raw_dir, config.extractor_parquet_filename)
    
    if os.path.exists(parquet_path):
        extractor.extract_from_parquet(parquet_path, config.extractor_output_pickle_basename, 100000) # 先取10w条
    else:
        logger.log_info(f"Error: Parquet file not found at {parquet_path}", module="main")


def run_preprocessor(config: Config):
    """2. 执行数据预处理功能"""
    logger.log_info("Running Data Preprocessor...", module="main")
    processed_dir = config.preprocessor_input_data_dir  # Assuming input and output are the same

    preprocessor = DataPreprocessor(config=config)
    input_name = config.preprocessor_input_requests_basename
    
    if os.path.exists(os.path.join(processed_dir, f"{input_name}{config.preprocessor_input_extension}")):
        # 默认按原样处理或可以添加采样逻辑
        preprocessor.preprocess(input_name=input_name, suffix=config.preprocessor_output_suffix, ratio=1.0)
        # 生成初始化司机数据
        preprocessor.generate_drivers()
    else:
        logger.log_info(f"Error: Pickle file not found at {processed_dir}/{input_name}.pickle", module="main")


def run_taxi_zone_processor(config: Config):
    """3. 执行出租车区域处理器功能"""
    logger.log_info("Running Taxi Zone Processor...", module="main")
    raw_dir = config.extractor_raw_data_dir
    processed_dir = config.extractor_output_data_dir
    os.makedirs(processed_dir, exist_ok=True)
    
    shapefile_dir = config.taxi_zone_shapefile_dir
    pickle_filename = config.taxi_zone_centroids_pickle_filename
    
    try:
        # TaxiZoneSpatialIndexer 内部应使用 config.extractor_output_data_dir 作为基础路径
        TaxiZoneSpatialIndexer(config=config)
        logger.log_info(f"Taxi zone centroids saved to {processed_dir}/{pickle_filename}", module="main")
    except Exception as e:
        logger.log_info(f"Error during taxi zone processing: {e}", module="main")


def main():
    """主入口函数，处理命令行参数"""
    config = Config()
    # 初始化日志，确保所有功能都能使用日志系统
    os.makedirs(config.log_output_dir, exist_ok=True)
    log_file_full_path = os.path.join(config.log_output_dir, config.log_file_name)
    logger.init_logger(log_file_path=log_file_full_path, level=config.log_level)
    
    modes = {
        "--1": "taxi_zone",
        "--2": "extractor",
        "--3": "data_preprocessing",
        "--4": "sim"
    }
    
    # 当没有参数、参数为 help、或参数不符合预期（拼写错误）时，显示指导信息
    if len(sys.argv) < 2 or sys.argv[1] in ['help', '-h', '--help'] or sys.argv[1] not in modes.keys():
        print("\n使用指南 (Guidance):")
        print("用法: python main.py [参数代号]")
        print("\n可用模式 (Available modes):")
        print("  --1  - 执行出租车区域处理器功能 (处理 data/data_raw 中的区域数据并提取边界)")
        print("  --2  - 执行数据提取器功能 (从 data/data_raw 提取 parquet)")
        print("  --3  - 执行数据预处理功能 (包括订单坐标转换和随机司机生成)")
        print("  --4  - 运行仿真主程序 (Simulation)")
        print("\n示例: python main.py --4")
        return

    # 根据参数代号获取实际模式
    mode = modes[sys.argv[1]]
    
    if mode == "extractor":
        run_extractor(config=config)
    elif mode == "data_preprocessing":
        run_preprocessor(config=config)
    elif mode == "taxi_zone":
        run_taxi_zone_processor(config=config)
    elif mode == "sim":
        algorithm = ExampleAlgorithm()
        run_simulation(config, algorithm)


if __name__ == "__main__":
    main()
