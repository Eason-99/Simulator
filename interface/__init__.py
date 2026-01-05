"""
算法接口模块
- algorithm_interface: 核心算法接口抽象类
- result_processor: 处理算法返回的方案
"""

from .algorithm_interface import ODDRAlgorithmInterface
from .result_processor import ResultProcessor

__all__ = ['ODDRAlgorithmInterface', 'ResultProcessor']

