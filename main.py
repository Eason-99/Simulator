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

from config.config import Config
from data_processing.extractor import DataExtractor
from data_processing.preprocessor import DataPreprocessor
from environment.simulator import Simulator
from environment.metrics import MetricsCalculator
from interface.algorithm_interface import ODDRAlgorithmInterface
from interface.result_processor import ResultProcessor
from example_algorithm import ExampleAlgorithm

# 导入debug工具（可选，如果不需要可以注释掉）
try:
    from debug.inspect_data import (
        print_request_data,
        print_driver_info,
        print_order_num_origin
    )
    DEBUG_MODE = True
except ImportError as e:
    print("Failed to import debug tools. Debugging features will be disabled.")
    print(f"Error: {e}")
    DEBUG_MODE = False


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
        if DEBUG_MODE:
            print_request_data(request_all, request_file)
    else:
        print(f"Warning: Request file not found: {request_file}, using empty dict")
        request_all = {}

    # 加载司机数据
    driver_file = os.path.join(data_dir, 'df_driver_info_100.pickle')
    if os.path.exists(driver_file):
        with open(driver_file, 'rb') as f:
            driver_info = pickle.load(f)
        if DEBUG_MODE:
            print_driver_info(driver_info, driver_file)
    else:
        print(f"Warning: Driver file not found: {driver_file}, using empty DataFrame")
        driver_info = pd.DataFrame()

    # 加载订单数量数据
    order_num_file = os.path.join(data_dir, 'all_requests_0.1_origin_order_num.csv')
    if os.path.exists(order_num_file):
        order_num_origin = pd.read_csv(order_num_file)
        if DEBUG_MODE:
            print_order_num_origin(order_num_origin, order_num_file)
    else:
        print(f"Warning: Order num file not found: {order_num_file}, using empty DataFrame")
        order_num_origin = pd.DataFrame()

    return request_all, driver_info, order_num_origin


def main(config: Config, algorithm: ODDRAlgorithmInterface):
    """
    主函数
    
    Args:
        config: 配置对象
        algorithm: ODDR算法接口实例
    """
    print("=" * 50)
    print("ODDR Simulator")
    print("=" * 50)
    
    # 加载数据
    print("\n[1/5] Loading data...")
    request_all, driver_info, order_num_origin = load_data(config)
    print("Data loaded.")
    # return
    # 初始化结果处理器
    result_processor = ResultProcessor()
    
    # 初始化仿真器
    print("\n[2/5] Initializing simulator...")
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
    print("Simulator initialized.")
    
    # 初始化效果计算器
    metrics_calculator = MetricsCalculator()
    
    # 计算实验日期范围
    start_date = datetime.strptime(config.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(config.end_date, '%Y-%m-%d')
    
    current_date = start_date
    all_metrics = []
    
    print("\n[3/5] Running simulation...")
    print("=" * 50)
    
    # 按日期循环
    while current_date <= end_date:
        experiment_date = current_date.strftime('%Y-%m-%d')
        print(f"\nExperiment Date: {experiment_date}")
        
        # 重置环境
        simulator.reset(experiment_date)
        
        # 运行仿真
        print(f"Running steps: {simulator.current_step} to {simulator.finish_run_step}")
        for step in range(simulator.current_step, simulator.finish_run_step):
            if step % 10 == 0:  # 每10步打印一次
                print(f"  Step {step}/{simulator.finish_run_step} - Time: {simulator.curent_experiment_time}")
            
            # 执行一个时间步
            simulator.step()
        
        # 将每天的所有已完成订单整合
        simulator.finalize_run()
        
        # 计算每日指标
        print(f"\n[4/5] Calculating metrics for {experiment_date}...")
        daily_metrics = metrics_calculator.calculate_daily_metrics(
            matched_requests=simulator.matched_requests,
            driver_reward_table=simulator.driver_reward_table,
            num_all_requests=simulator.num_all_requests
        )
        all_metrics.append(daily_metrics)
        
        # 打印每日结果
        print(f"  GMV: {daily_metrics['gmv']:.2f}")
        print(f"  OCR: {daily_metrics['ocr'] * 100:.2f}%")
        print(f"  Matched: {daily_metrics['num_matched_requests']}/{daily_metrics['num_all_requests']}")
        
        # 保存每日结果（可选）
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
    print("\n[5/5] Calculating overall metrics...")
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
    
    print("\n" + "=" * 50)
    print("Simulation Complete!")
    print("=" * 50)
    print(f"Total GMV: {overall_metrics['total_gmv']:.2f}")
    print(f"Overall OCR: {overall_metrics['overall_ocr'] * 100:.2f}%")
    print(f"Total Matched: {overall_metrics['total_matched']}/{overall_metrics['total_requests']}")
    print("=" * 50)


if __name__ == "__main__":
    # 创建配置
    config = Config()

    # 使用ExampleAlgorithm替代DummyAlgorithm
    algorithm = ExampleAlgorithm()

    # 运行主程序
    main(config, algorithm)

