"""
模块2：数据预处理器
对pickle文件进行预处理，生成处理后的pickle文件
当前版本：原样传递（不做任何处理）
"""

import pickle
import os
from typing import Any, Dict


class DataPreprocessor:
    """数据预处理器 - 当前版本原样传递"""
    
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
    
    def preprocess(self, input_name: str, output_name: str = None) -> str:
        """
        预处理pickle数据
        
        Args:
            input_name: 输入pickle文件名（不含扩展名，相对于input_dir）
            output_name: 输出pickle文件名（不含扩展名，相对于output_dir）
                        如果为None，则使用input_name
            
        Returns:
            输出pickle文件路径
        """
        input_path = os.path.join(self.input_dir, f"{input_name}.pickle")
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # 读取输入数据
        with open(input_path, 'rb') as f:
            data = pickle.load(f)
        
        # TODO: 实际实现时，这里应该进行数据预处理
        # 当前版本：原样传递
        processed_data = data
        
        # 确定输出路径
        if output_name is None:
            output_name = input_name
        
        output_path = os.path.join(self.output_dir, f"{output_name}.pickle")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存处理后的数据
        with open(output_path, 'wb') as f:
            pickle.dump(processed_data, f)
        
        print(f"Preprocessed data saved to: {output_path}")
        return output_path
    
    def preprocess_requests(self, dataset_name: str, input_name: str = "all_requests_0.1") -> str:
        """
        预处理订单请求数据
        
        Args:
            dataset_name: 数据集名称
            input_name: 输入文件名（不含扩展名）
            
        Returns:
            输出pickle文件路径
        """
        input_full_name = f"{dataset_name}/{input_name}"
        return self.preprocess(input_full_name, input_full_name)
    
    def preprocess_drivers(self, dataset_name: str, input_name: str = "df_driver_info_100") -> str:
        """
        预处理司机数据
        
        Args:
            dataset_name: 数据集名称
            input_name: 输入文件名（不含扩展名）
            
        Returns:
            输出pickle文件路径
        """
        input_full_name = f"{dataset_name}/{input_name}"
        return self.preprocess(input_full_name, input_full_name)

