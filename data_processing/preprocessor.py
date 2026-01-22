"""
模块2：数据预处理器
对pickle文件进行预处理，生成处理后的pickle文件
支持：数据采样、按区域和时间增加/减少订单
"""

import pickle
import os
import random
import copy
import uuid # For generating unique order IDs
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from log_utils.logger import Logger
from config.config import Config
from data_processing.taxi_zone_processor import TaxiZoneSpatialIndexer
from interface.data_structure import Order # Import the new Order data structure

# 初始化 Logger
logger = Logger()


class DataPreprocessor:
    """数据预处理器 - 支持数据过滤和模拟增减"""
    
    def __init__(self, config: Config):
        """
        初始化数据预处理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.input_dir = config.preprocessor_input_data_dir
        self.output_dir = config.preprocessor_output_data_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.indexer = TaxiZoneSpatialIndexer(config)
    
    def _count_orders(self, data: Dict[str, Dict[str, List[Order]]]) -> int:
        """计算字典中所有订单的总数"""
        count = 0
        for date_data in data.values():
            for time_requests in date_data.values():
                count += len(time_requests)
        return count

    def select_data(self, data: Dict[str, Dict[str, List[Order]]], ratio: float = 1.0, random_select: bool = False) -> Dict[str, Dict[str, List[Order]]]:
        """
        选取部分数据
        
        Args:
            data: 原始二级字典数据，包含 Order 对象列表
            ratio: 选取比例 (0.0 - 1.0)
            random_select: True 则随机选，False 则从头开始选
            
        Returns:
            处理后的字典，包含 Order 对象列表
        """
        if ratio >= 1.0:
            return data
            
        new_data = {}
        for date, time_dict in data.items():
            new_data[date] = {}
            for time_key, requests in time_dict.items():
                n = len(requests)
                target_n = int(n * ratio)
                
                if random_select:
                    new_data[date][time_key] = random.sample(requests, target_n)
                else:
                    new_data[date][time_key] = requests[:target_n]
        return new_data

    def modify_orders(self,
                      data: Dict[str, Dict[str, List[Order]]],
                      target_date: str,
                      target_time_key: str,
                      target_zone_id: int,
                      multiplier_n: int = 1, # Only used for addition
                      is_add: bool = True) -> Dict[str, Dict[str, List[Order]]]:
        """
        在特定日期、时间点和区域增加或减少订单
        
        Args:
            data: 原始二级字典数据，包含 Order 对象列表
            target_date: 目标日期字符串 (e.g., "2025-01-01")
            target_time_key: 目标时间点字符串 (e.g., "0", "3600")
            target_zone_id: 目标区域ID (origin_grid_id)
            multiplier_n: 增加订单的倍数 (仅当 is_add 为 True 时有效)
            is_add: True 为增加，False 为减少
            
        Returns:
            处理后的字典，包含 Order 对象列表
        """
        new_data = copy.deepcopy(data)
        
        if target_date not in new_data:
            logger.log_info(f"[Warning] Target date {target_date} not found in data. No modifications made.", module="preprocessor")
            return new_data
            
        if target_time_key not in new_data[target_date]:
            logger.log_info(f"[Warning] Target time key {target_time_key} not found for date {target_date}. No modifications made.", module="preprocessor")
            return new_data

        requests_at_target_time = new_data[target_date][target_time_key]
        
        if is_add:
            # 增加订单：从现有符合区域条件的订单中复制 n 倍
            zone_requests = [r for r in requests_at_target_time if r.origin_grid_id == target_zone_id]
            
            if not zone_requests:
                logger.log_info(f"[Warning] No existing orders found in zone {target_zone_id} at {target_date} {target_time_key}. Cannot add orders.", module="preprocessor")
                return new_data # 如果该时间点该区域没订单，则不能增加
            
            orders_to_add = []
            for _ in range(multiplier_n): # 复制 n 倍
                for template in zone_requests:
                    new_order = copy.deepcopy(template)
                    # 修改 order_id 防止重复，使用 UUID
                    new_order.order_id = uuid.uuid4().int & (1<<31)-1 # 使用UUID生成一个31位整数ID
                    # 确保起始区域在目标区域内 (already is, but explicit)
                    new_order.origin_grid_id = target_zone_id
                    # 根据新的起点重新设置经纬度（预处理阶段会更新）
                    new_order.origin_lng = None
                    new_order.origin_lat = None
                    orders_to_add.append(new_order)
                    logger.log_debug(f"[ADD] Date: {target_date}, Time: {target_time_key}, ID: {new_order.order_id}, From Grid: {new_order.origin_grid_id}, To Grid: {new_order.dest_grid_id}", module="preprocessor")
            
            requests_at_target_time.extend(orders_to_add)
        else:
            # 减少订单：移除符合区域条件的订单
            original_count = len(requests_at_target_time)
            requests_at_target_time[:] = [r for r in requests_at_target_time if r.origin_grid_id != target_zone_id]
            removed_count = original_count - len(requests_at_target_time)
            logger.log_debug(f"[REMOVE] Date: {target_date}, Time: {target_time_key}, Zone: {target_zone_id}, Removed {removed_count} orders.", module="preprocessor")
                            
        return new_data

    def preprocess(self,
                   input_name: str,
                   suffix: str = "",
                   ratio: float = 1.0,
                   random_select: bool = False,
                   add_config: Optional[Dict] = None, # Updated structure
                   remove_config: Optional[Dict] = None) -> str: # Updated structure
        """
        Args:
            input_name: 输入pickle文件名（不含扩展名）
            suffix: 输出文件名后缀
            ratio: 采样比例
            random_select: 是否随机采样
            add_config: 增加订单配置 {"date": str, "time_key": str, "zone_id": int, "multiplier": int}
            remove_config: 减少订单配置 {"date": str, "time_key": str, "zone_id": int}
            
        Returns:
            输出pickle文件路径
        """
        input_path = os.path.join(self.input_dir, f"{input_name}.pickle")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        with open(input_path, "rb") as f:
            data: Dict[str, Dict[str, List[Order]]] = pickle.load(f)
            
        # 统计修改前
        initial_count = self._count_orders(data)
            
        # 1. 选取数据
        processed_data = self.select_data(data, ratio, random_select)

        # 1.5 坐标转换 (LocationID -> Lon/Lat)
        for date, time_dict in processed_data.items():
            for time_key, requests in time_dict.items():
                for order in requests:
                    # Order 对象现在包含 origin_grid_id 和 dest_grid_id
                    pu_id = order.origin_grid_id
                    do_id = order.dest_grid_id
                    
                    pu_coords = self.indexer.get_coordinates(pu_id)
                    do_coords = self.indexer.get_coordinates(do_id)
                    
                    if pu_coords:
                        order.origin_lng = pu_coords[0] # lng
                        order.origin_lat = pu_coords[1] # lat
                    if do_coords:
                        order.dest_lng = do_coords[0] # lng
                        order.dest_lat = do_coords[1] # lat
        
        # 2. 增加订单
        if add_config:
            processed_data = self.modify_orders(
                processed_data,
                add_config["date"],
                add_config["time_key"],
                add_config["zone_id"],
                add_config.get("multiplier", 1),
                is_add=True
            )
            
        # 3. 减少订单
        if remove_config:
            processed_data = self.modify_orders(
                processed_data,
                remove_config["date"],
                remove_config["time_key"],
                remove_config["zone_id"],
                is_add=False
            )
            
        # 统计修改后
        final_count = self._count_orders(processed_data)
        logger.log_statistics("=" * 50, module="preprocessor")
        logger.log_statistics("Preprocessing Stats", module="preprocessor")
        logger.log_statistics(f"Initial Total Orders: {initial_count}", module="preprocessor")
        logger.log_statistics(f"Final Total Orders:   {final_count}", module="preprocessor")
        logger.log_statistics("=" * 50, module="preprocessor")
            
        output_path = os.path.join(
            self.output_dir,
            f"{input_name}{suffix}{self.config.preprocessor_output_extension}"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "wb") as f:
            pickle.dump(processed_data, f)
            
        logger.log_info(f"Preprocessed data saved to: {output_path}", module="preprocessor")
        logger.log_debug(f"Full extracted data structure preview for {output_path}", data=processed_data, module="preprocessor") # 包含大量订单对象数据
        return output_path

    def generate_drivers(self) -> str:
        """
        生成随机分布的初始司机数据
        
        Returns:
            生成的司机数据文件路径
        """
        logger.log_info("Generating initial driver data...", module="preprocessor")
        boundary = self.indexer.get_boundary()
        
        if not boundary:
            raise ValueError("Cannot generate drivers without taxi zone boundary information.")
            
        num_drivers = self.config.num_drivers
        driver_data = []
        
        for i in range(num_drivers):
            # 随机生成经纬度
            lng = random.uniform(boundary['min_lng'], boundary['max_lng'])
            lat = random.uniform(boundary['min_lat'], boundary['max_lat'])
            
            # 司机信息: [编号, 经度, 纬度, 当前收入, 累计行驶距离]
            # 根据 Simulator 中的预期格式，通常是一个 DataFrame，包含相应列
            driver_data.append({
                'driver_id': f"driver_{i}",
                'lng': lng,
                'lat': lat,
                'income': 0.0,
                'total_distance': 0.0
            })
            
        df_drivers = pd.DataFrame(driver_data)
        
        output_path = os.path.join(
            self.output_dir,
            self.config.preprocessor_output_drivers_filename
        )
        
        with open(output_path, 'wb') as f:
            pickle.dump(df_drivers, f)
            
        logger.log_info(f"Successfully generated {num_drivers} drivers at {output_path}", module="preprocessor")
        
        return output_path

