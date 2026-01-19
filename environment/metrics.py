"""
模块5：效果计算
根据最终方案计算效果指标
"""

import pandas as pd
import os
from typing import Dict, Any


class MetricsCalculator:
    """效果计算器"""
    
    def __init__(self):
        """初始化效果计算器"""
        pass
    
    def calculate_daily_metrics(self,
                                matched_requests: pd.DataFrame,
                                driver_reward_table: pd.DataFrame,
                                num_all_requests: int) -> Dict[str, float]:
        """
        计算每日效果指标
        
        Args:
            matched_requests: 匹配的订单DataFrame
            driver_reward_table: 司机奖励表DataFrame
            num_all_requests: 总订单数
            
        Returns:
            Dict: 包含各项指标的字典
        """
        # GMV: 总交易额（Gross Merchandise Value）
        gmv = driver_reward_table['current_overall_reward'].sum()
        
        # ORR: 订单完成率（Order Response Rate）
        num_matched_requests = len(matched_requests)
        ocr = num_matched_requests / num_all_requests if num_all_requests > 0 else 0.0
        
        # 平均每单收益
        avg_reward_per_order = gmv / num_matched_requests if num_matched_requests > 0 else 0.0
        
        # 司机平均完成订单数
        avg_orders_per_driver = driver_reward_table['num_finished_order'].mean() if len(driver_reward_table) > 0 else 0.0
        
        metrics = {
            'gmv': float(gmv),
            'ocr': float(ocr),
            'num_matched_requests': int(num_matched_requests),
            'num_all_requests': int(num_all_requests),
            'avg_reward_per_order': float(avg_reward_per_order),
            'avg_orders_per_driver': float(avg_orders_per_driver)
        }
        
        return metrics
    
    def calculate_overall_metrics(self,
                                   save_path: str) -> Dict[str, Any]:
        """
        计算总体效果指标（从保存的文件中读取）
        
        Args:
            save_path: 保存路径
            
        Returns:
            Dict: 包含总体指标的字典
        """
        driver_reward_table = pd.DataFrame()
        for filename in os.listdir(os.path.join(save_path, 'driver_reward_table')):
            if filename.endswith(".csv"):
                file_path = os.path.join(save_path, 'driver_reward_table', filename)
                data = pd.read_csv(file_path)
                driver_reward_table = pd.concat([driver_reward_table, data])
                driver_reward_table = driver_reward_table.groupby('driver_id').sum().reset_index()
        
        matched_requests = pd.DataFrame()
        for filename in os.listdir(os.path.join(save_path, 'matched_requests')):
            if filename.endswith(".csv"):
                file_path = os.path.join(save_path, 'matched_requests', filename)
                data = pd.read_csv(file_path)
                matched_requests = pd.concat([matched_requests, data])
        
        num_all_requests, num_matched_requests = 0, 0
        for filename in os.listdir(os.path.join(save_path, 'others')):
            if filename.endswith(".txt"):
                file_path = os.path.join(save_path, 'others', filename)
                with open(file_path, 'r') as f:
                    data = f.readlines()
                    num_matched_requests += int(data[0].split(',')[0].split(':')[1])
                    num_all_requests += int(data[0].split(',')[1].split(':')[1])
        
        # 计算指标
        gmv = driver_reward_table['current_overall_reward'].sum()
        ocr = driver_reward_table['num_finished_order'].sum() / num_all_requests if num_all_requests > 0 else 0.0
        
        metrics = {
            'gmv': float(gmv),
            'ocr': float(ocr),
            'num_matched_requests': int(len(matched_requests)),
            'num_all_requests': int(num_all_requests)
        }
        
        return metrics
    
    def save_metrics(self, metrics: Dict[str, Any], save_path: str, filename: str = 'result.txt'):
        """
        保存指标到文件
        
        Args:
            metrics: 指标字典
            save_path: 保存路径
            filename: 文件名
        """
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, filename)
        
        with open(file_path, 'w') as f:
            f.write(f"matched requests num: {metrics.get('num_matched_requests', 0)}, "
                   f"all requests num: {metrics.get('num_all_requests', 0)}\n")
            f.write(f"GMV: {metrics.get('gmv', 0):.2f}, "
                   f"ORR: {metrics.get('ocr', 0) * 100:.2f}%\n")
            if 'avg_reward_per_order' in metrics:
                f.write(f"Average reward per order: {metrics['avg_reward_per_order']:.2f}\n")
            if 'avg_orders_per_driver' in metrics:
                f.write(f"Average orders per driver: {metrics['avg_orders_per_driver']:.2f}\n")
        
        print(f"Metrics saved to: {file_path}")

