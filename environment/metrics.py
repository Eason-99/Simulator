"""
模块5：效果计算
仅保留GMV和OCR的统计与打印功能
"""

from typing import List
from interface.data_structure import OrderContext
from log_utils.logger import Logger

# 初始化 Logger (单例)
logger = Logger()

class MetricsCalculator:
    """效果计算器"""
    
    def __init__(self):
        """初始化效果计算器"""
        pass
    
    def calculate_and_log_metrics(self, 
                                  day: str, 
                                  matched_requests: List[OrderContext], 
                                  num_all_requests: int):
        """
        计算并记录每日指标
        
        Args:
            day: 实验日期
            matched_requests: 已匹配的订单上下文列表
            num_all_requests: 该日总订单请求数
        """
        # GMV: 总交易额，这里定义为所有已匹配订单的 fare 之和
        gmv = sum(om.order.fare for om in matched_requests)
        
        # OCR: 订单完成率 (Order Completion Rate / Order Response Rate)
        num_matched = len(matched_requests)
        ocr = num_matched / num_all_requests if num_all_requests > 0 else 0.0
        
        # 打印到日志
        log_msg = (f"Daily Metrics for {day}: "
                   f"GMV: {gmv:.2f}, "
                   f"OCR: {ocr:.2%}, "
                   f"Matched: {num_matched}, "
                   f"Total: {num_all_requests}")
        
        logger.log_info(log_msg, module="metrics")
        print(log_msg)
        
        return gmv, ocr
