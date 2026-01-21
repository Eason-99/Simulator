"""
模块2：数据预处理器
对pickle文件进行预处理，生成处理后的pickle文件
支持：数据采样、按区域和时间增加/减少订单
"""

import pickle
import os
import random
import copy
from typing import Any, Dict, List, Optional, Tuple
from log_utils.logger import Logger

# 初始化 Logger
logger = Logger()


class DataPreprocessor:
    """数据预处理器 - 支持数据过滤和模拟增减"""
    
    def __init__(self, input_dir: str = "data", output_dir: str = "data"):
        """
        初始化数据预处理器
        
        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def _count_orders(self, data: Dict[str, Dict[str, List]]) -> int:
        """计算字典中所有订单的总数"""
        count = 0
        for date_data in data.values():
            for time_requests in date_data.values():
                count += len(time_requests)
        return count

    def select_data(self, data: Dict[str, Dict[str, List]], ratio: float = 1.0, random_select: bool = False) -> Dict[str, Dict[str, List]]:
        """
        选取部分数据
        
        Args:
            data: 原始二级字典数据
            ratio: 选取比例 (0.0 - 1.0)
            random_select: True 则随机选，False 则从头开始选
            
        Returns:
            处理后的字典
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
                      data: Dict[str, Dict[str, List]], 
                      target_zones: List[Any], 
                      time_ranges: List[Tuple[int, int]], 
                      delta: int,
                      is_add: bool = True) -> Dict[str, Dict[str, List]]:
        """
        在特定区域和特定时间段增加或减少订单
        
        Args:
            data: 原始二级字典数据
            target_zones: 区域ID列表 (PULocationID)
            time_ranges: 时间段列表，元素为 (start_seconds, end_seconds)
            delta: 增减的数量 (每个符合条件的时间片)
            is_add: True 为增加，False 为减少
            
        Returns:
            处理后的字典
        """
        new_data = copy.deepcopy(data)
        
        for date, time_dict in new_data.items():
            for time_key, requests in time_dict.items():
                t = int(time_key)
                # 检查是否在时间段内
                in_time_range = any(start <= t <= end for start, end in time_ranges)
                if not in_time_range:
                    continue
                
                if is_add:
                    # 增加订单：从现有符合区域条件的订单中随机复制，或者直接复制样本
                    # 注意：这里简化处理，如果没有现有订单则无法增加，或者需要模板
                    zone_requests = [r for r in requests if r[1] in target_zones]
                    if not zone_requests:
                        # 如果当前片区没订单，尝试找该时间点其他片区的订单作为模板，但修改其起始区域
                        zone_requests = requests
                    
                    if zone_requests:
                        for i in range(delta):
                            template = random.choice(zone_requests)
                            new_order = copy.deepcopy(template)
                            # 修改 order_id 防止重复
                            new_order[0] = f"{new_order[0]}_extra_{i}"
                            # 确保起始区域在目标区域内
                            new_order[1] = random.choice(target_zones)
                            requests.append(new_order)
                            
                            logger.log_debug(f"[ADD] Date: {date}, Time: {time_key}, ID: {new_order[0]}, From: {new_order[1]}, To: {new_order[3]}", module="preprocessor")
                else:
                    # 减少订单：移除符合区域条件的订单
                    # 找到符合区域条件的索引
                    indices = [i for i, r in enumerate(requests) if r[1] in target_zones]
                    to_remove_count = min(len(indices), delta)
                    if to_remove_count > 0:
                        remove_indices = random.sample(indices, to_remove_count)
                        # 按索引从大到小删除
                        for idx in sorted(remove_indices, reverse=True):
                            removed_order = requests.pop(idx)
                            logger.log_debug(f"[REMOVE] Date: {date}, Time: {time_key}, ID: {removed_order[0]}", module="preprocessor")
                            
        return new_data

    def preprocess(self, 
                   input_name: str, 
                   suffix: str = "_processed",
                   ratio: float = 1.0,
                   random_select: bool = False,
                   add_config: Optional[Dict] = None,
                   remove_config: Optional[Dict] = None) -> str:
        """
        Args:
            input_name: 输入pickle文件名（不含扩展名）
            suffix: 输出文件名后缀
            ratio: 采样比例
            random_select: 是否随机采样
            add_config: 增加订单配置 {'zones': [], 'ranges': [(s, e)], 'count': int}
            remove_config: 减少订单配置 {'zones': [], 'ranges': [(s, e)], 'count': int}
            
        Returns:
            输出pickle文件路径
        """
        input_path = os.path.join(self.input_dir, f"{input_name}.pickle")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        with open(input_path, 'rb') as f:
            data = pickle.load(f)
            
        # 统计修改前
        initial_count = self._count_orders(data)
            
        # 1. 选取数据
        processed_data = self.select_data(data, ratio, random_select)
        
        # 2. 增加订单
        if add_config:
            processed_data = self.modify_orders(
                processed_data, 
                add_config['zones'], 
                add_config['ranges'], 
                add_config['count'], 
                is_add=True
            )
            
        # 3. 减少订单
        if remove_config:
            processed_data = self.modify_orders(
                processed_data, 
                remove_config['zones'], 
                remove_config['ranges'], 
                remove_config['count'], 
                is_add=False
            )
            
        # 统计修改后
        final_count = self._count_orders(processed_data)
        logger.log_statistics("=" * 50, module="preprocessor")
        logger.log_statistics("Preprocessing Stats", module="preprocessor")
        logger.log_statistics(f"Initial Total Orders: {initial_count}", module="preprocessor")
        logger.log_statistics(f"Final Total Orders:   {final_count}", module="preprocessor")
        logger.log_statistics("=" * 50, module="preprocessor")
            
        output_path = os.path.join(self.output_dir, f"{input_name}{suffix}.pickle")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            pickle.dump(processed_data, f)
            
        logger.log_info(f"Preprocessed data saved to: {output_path}", module="preprocessor")
        return output_path

    def preprocess_requests(self, dataset_name: str, **kwargs) -> str:
        """
        预处理订单请求数据
        """
        input_full_name = f"{dataset_name}/all_requests_0.1"
        return self.preprocess(input_full_name, **kwargs)

    def preprocess_drivers(self, dataset_name: str, **kwargs) -> str:
        """
        预处理司机数据
        """
        input_full_name = f"{dataset_name}/df_driver_info_100"
        return self.preprocess(input_full_name, **kwargs)


if __name__ == "__main__":
    # 实例化预处理器
    preprocessor = DataPreprocessor(input_dir="data/large", output_dir="data/large")
    
    
    # 演示：对第一个订单所在的区域及时间，增加10条订单
    # 1. 首先读取原始数据获取第一条订单的信息
    input_file = "data/large/all_requests_0.1.pickle"
    if os.path.exists(input_file):
        with open(input_file, 'rb') as f:
            raw_data = pickle.load(f)
        
        # 获取第一天、第一个时间点的第一条订单
        first_date = sorted(raw_data.keys())[0]
        first_time_key = sorted(raw_data[first_date].keys())[0]
        first_order = raw_data[first_date][first_time_key][0]
        
        target_zone = first_order[1] # PULocationID
        target_time = int(first_time_key)
        
        print(f"Targeting Zone: {target_zone} at Time: {target_time} (Date: {first_date})")
        
        # 2. 执行预处理增加订单
        preprocessor.preprocess(
            input_name="all_requests_0.1",
            suffix="_extra_orders",
            add_config={
                'zones': [target_zone],
                'ranges': [(target_time, target_time)],
                'count': 10
            }
        )
    else:
        print(f"File not found for main demo: {input_file}")
