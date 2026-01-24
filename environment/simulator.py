"""
核心仿真器
管理仿真环境，调用算法接口，更新状态
"""

import os
import pickle
import pandas as pd
import numpy as np
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

from .state_manager import StateManager
from .utils import distance_array
from config.config import Config # Add this import
from interface.data_structure import Order, OrderContext, OrderStatus, Driver, DriverContext, VehicleStatus # Import Order, OrderContext and Driver classes
from data_processing.map import load_mapping  # 导入映射关系加载函数
from .metrics import MetricsCalculator

# 使用绝对导入（从项目根目录）
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interface.algorithm_interface import ODDRAlgorithmInterface
from interface.result_processor import ResultProcessor

# 导入 Logger
from log_utils.logger import Logger

# 初始化 Logger (单例)
logger = Logger()


class Simulator:
    """环境仿真器"""
    
    def __init__(self,
                 request_all: Dict[str, Dict[str, List[Order]]], # Update type hint to use Order
                 driver_info: List[Driver],
                 algorithm: ODDRAlgorithmInterface,
                 config: Config, # Add config object
                 result_processor: ResultProcessor = None):
        """
        初始化仿真器
        
        Args:
            request_all: 所有订单请求数据（字典，键为日期，内含 Order 对象列表）
            driver_info: 司机信息列表
            algorithm: ODDR算法接口实例
            config: 配置对象
            result_processor: 结果处理器（可选）
        """
        self.config = config # Store config
        
        # 加载区域ID映射关系
        self.mapping_dict = None  # 原始 ID -> 新 ID
        self.reverse_mapping_dict = None  # 新 ID -> 原始 ID
        if config.map_grid_mapping_pickle_path:
            mapping_data = load_mapping(config.map_grid_mapping_pickle_path)
            if mapping_data:
                self.mapping_dict = mapping_data.get('mapping_dict')
                self.reverse_mapping_dict = mapping_data.get('reverse_mapping_dict')
                print(f"成功加载区域ID映射关系，共 {mapping_data.get('num_regions', 0)} 个区域")
                logger.log_info(f"Loaded region ID mapping with {mapping_data.get('num_regions', 0)} regions", module="simulator")

        # 基本参数 (从 config 读取)
        self.start_date = config.start_date
        self.end_date = config.end_date
        self.t_initial = config.start_time
        self.t_end = config.end_time
        self.delta_t = config.delta_t
        self.vehicle_speed = config.vehicle_speed
        self.pickup_dis_threshold = config.pickup_dis_threshold
        self.maximum_wait_time_mean = config.maximum_wait_time_mean
        self.max_idle_time = config.max_idle_time
        
        # 数据
        self.request_all = request_all
        self.driver_info = driver_info
        
        # 算法接口
        self.algorithm = algorithm
        self.result_processor = result_processor or ResultProcessor()
        
        # 状态管理器
        self.state_manager = StateManager()
        self.metrics_calculator = MetricsCalculator()
        
        # 实验日期
        self.experiment_date = None
        # self.curent_experiment_time = None
        
        # 计算步数
        self.finish_run_step = int(self.t_end // self.delta_t)
        
        # 初始化状态
        self.drivers: List[DriverContext] = []
        self.wait_requests = None
        self.matched_requests = None
        self.expired_requests = None
        self.matched_requests_buffer = None
        self.request_databases = None
        self.time = None
        self.current_step = None
        self.num_all_requests = 0
        self.total_gmv = 0.0
        self.total_matched_requests = 0
        self.total_all_requests = 0
    
    def reset(self, experiment_date: str):
        """
        重置环境
        
        Args:
            experiment_date: 实验日期（格式：'YYYY-MM-DD'）
        """
        self.experiment_date = experiment_date
        
        # 初始化请求数据库
        self.request_databases = deepcopy(self.request_all.get(experiment_date, {}))
        
        # 初始化司机
        self.drivers = [
            DriverContext(
                driver=deepcopy(d),
                target_lng=d.lng,
                target_lat=d.lat,
                total_idle_time=0.0
            ) for d in self.driver_info
        ]

        # 初始化订单表
        self.wait_requests: List[OrderContext] = []
        self.matched_requests: List[OrderContext] = []
        self.expired_requests: List[OrderContext] = []
        self.matched_requests_buffer = []

        # 初始化时间
        self.time = deepcopy(self.t_initial)
        self.current_step = int(self.time // self.delta_t)
        self.num_all_requests = 0
        
        # 更新时间字符串
        # result_date = datetime.strptime(self.experiment_date, "%Y-%m-%d") + timedelta(minutes=self.time)
        # self.curent_experiment_time = result_date.strftime("%Y-%m-%d %H:%M:%S")
    
    def step(self):
        """
        执行一个时间步
        """
        # Step 1: 生成新订单
        self._generate_new_orders()

        # Step 2: 获取订单-司机候选对
        # 注意：传给算法的订单信息是一个 Order 列表
        wait_orders = [wr.order for wr in self.wait_requests]
        # 提取 Driver 对象列表传递给算法
        drivers_for_algorithm = [dm.driver for dm in self.drivers]
        
        # Step 2.5: 如果存在映射关系，替换订单和司机中的区域 ID
        if self.mapping_dict is not None:
            # 深拷贝订单列表以避免修改原始数据
            wait_orders = deepcopy(wait_orders)
            # 替换订单中的区域 ID
            for order in wait_orders:
                if order.origin_grid_id in self.mapping_dict:
                    order.origin_grid_id = self.mapping_dict[order.origin_grid_id]
                else:
                    logger.log_info(f"[Error!!!!] Origin grid ID {order.origin_grid_id} not found in mapping_dict", module="simulator")
                if order.dest_grid_id in self.mapping_dict:
                    order.dest_grid_id = self.mapping_dict[order.dest_grid_id]
                else:
                    logger.log_info(f"[Error!!!!] Dest grid ID {order.dest_grid_id} not found in mapping_dict", module="simulator")
            
            # 深拷贝司机列表以避免修改原始数据
            drivers_for_algorithm = deepcopy(drivers_for_algorithm)
            # 替换司机中的区域 ID
            for driver in drivers_for_algorithm:
                if driver.grid_id in self.mapping_dict:
                    driver.grid_id = self.mapping_dict[driver.grid_id]
                else:
                    logger.log_info(f"[Error!!!!] Driver grid ID {driver.grid_id} not found in mapping_dict", module="simulator")
                if driver.target_grid_id in self.mapping_dict:
                    driver.target_grid_id = self.mapping_dict[driver.target_grid_id]
                else:
                    logger.log_info(f"[Error!!!!] Driver target grid ID {driver.target_grid_id} not found in mapping_dict", module="simulator")
        
        # Step 3: 调用算法接口
        # 调用算法进行匹配
        dispatch_plan = self.algorithm.dispatch(
            wait_requests=wait_orders,
            drivers=drivers_for_algorithm # 传递 Driver 对象列表
        )
        
        # 打印返回方案的前3条匹配
        logger.log_debug(f"wait_orders total: {len(wait_orders)} (First 5): {wait_orders[:5]}", module="simulator")
        logger.log_debug(f"drivers total: {len(drivers_for_algorithm)} (First 5): {drivers_for_algorithm[:5]}", module="simulator")
        logger.log_debug(f"Dispatch Plan total: {len(dispatch_plan)} (First 5): {dispatch_plan[:5]}", module="simulator")
        
        # 处理返回方案
        final_plan = self.result_processor.process_dispatch_result(dispatch_plan)
        
        # Step 4: 应用匹配方案
        if len(final_plan) > 0:
            self._apply_dispatch_plan(final_plan)

        # 在 update_time 之前打印调试信息
        num_idle_drivers = sum(1 for d in self.drivers if d.driver.status == VehicleStatus.IDLE)
        logger.log_step_info(
            step_time=self.time,
            num_orders=len(self.wait_requests),
            num_idle_drivers=num_idle_drivers,
            num_matched_orders=len(self.matched_requests_buffer[0]) if self.matched_requests_buffer else 0 # buffer的第一个元素才是这个step匹配的订单
        )
        
        # Step 5: 更新状态
        self._update_state()
        self._update_time()

    def _apply_dispatch_plan(self,
                             dispatch_plan: List[Tuple[str, str]]):
        """
        应用匹配方案
        
        Args:
            dispatch_plan: 匹配方案 [(order_id, driver_id), ...]
        """
        if not dispatch_plan:
            return

        # 1. 预处理：快速构建匹配关系字典
        order_id_to_driver_id = {int(oid): int(did) for oid, did in dispatch_plan}
        driver_id_to_driver_context = {dm.driver.vehicle_id: dm for dm in self.drivers}
        
        # 2. 找到匹配的 OrderContext 对象和对应的 DriverContext 对象
        matched_order_context_list: List[OrderContext] = []
        remaining_wait_requests: List[OrderContext] = []
        
        # 存储匹配成功的 (OrderContext, DriverContext) 元组
        temp_matched_data: List[Tuple[OrderContext, DriverContext]] = []

        for om in self.wait_requests:
            oid = om.order.order_id
            if oid in order_id_to_driver_id:
                driver_id = order_id_to_driver_id[oid]
                driver_context = driver_id_to_driver_context.get(driver_id)
                
                if driver_context:
                    # 计算接客距离和时间
                    pickup_distance = distance_array(
                        np.array([[om.order.origin_lng, om.order.origin_lat]]),
                        np.array([[driver_context.driver.lng, driver_context.driver.lat]])
                    )[0]
                    pickup_time = pickup_distance / self.vehicle_speed

                    # 更新 OrderContext 对象
                    om.driver_id = driver_id
                    om.status = OrderStatus.PICKING_UP
                    om.pickup_time = float(pickup_time)
                    om.t_matched = self.time
                    om.t_end = self.time + om.pickup_time + om.order.trip_time
                    matched_order_context_list.append(om)

                    # 更新 DriverContext 对象
                    driver_context.driver.status = VehicleStatus.PICKING_UP
                    driver_context.target_lng = om.order.dest_lng
                    driver_context.target_lat = om.order.dest_lat
                    driver_context.driver.remaining_travel_time = om.pickup_time + om.order.trip_time
                    driver_context.driver.current_order_id = om.order.order_id
                    driver_context.total_idle_time = 0.0
                    
                    # 收集匹配对
                    temp_matched_data.append((om, driver_context))
                else:
                    remaining_wait_requests.append(om) # 司机未找到，订单仍在等待
            else:
                remaining_wait_requests.append(om)
        
        # 更新订单列表
        self.matched_requests.extend(matched_order_context_list)
        self.wait_requests = remaining_wait_requests
        
        # 将本步匹配成功的元组列表存入 buffer
        if temp_matched_data:
            self.matched_requests_buffer.append(temp_matched_data)


    def _generate_new_orders(self):
        count_interval = int(np.floor(self.time / self.delta_t))
        time_key = str(count_interval * self.delta_t)

        # 取出当前时间点的订单
        current_step_orders: List[Order] = self.request_databases.get(time_key)

        if not current_step_orders:
            return

        self.num_all_requests += len(current_step_orders)

        # 直接用原来的 Order list 构建新的 OrderContext 列表
        for order in current_step_orders:
            order_context = OrderContext(
                order=order,
                order_date=self.experiment_date,
                status=OrderStatus.WAITING
            )
            self.wait_requests.append(order_context)

    
    def _update_state(self):
        """更新状态"""
        # 更新司机状态
        self.state_manager.update_driver_state(
            self.drivers, self.delta_t, self.vehicle_speed
        )
        
        # 更新等待订单状态（处理超时）
        remaining_wait_requests = []
        for om in self.wait_requests:
            # 计算当前等待时间
            wait_time = self.time - om.order.request_time
            if wait_time > om.order.max_wait_time:
                om.status = OrderStatus.EXPIRED
                self.expired_requests.append(om)
            else:
                remaining_wait_requests.append(om)
        self.wait_requests = remaining_wait_requests
        
        # 更新已匹配订单的状态（从 PICKING_UP 到 IN_TRIP 再到 COMPLETED）
        for om in self.matched_requests:
            if om.status == OrderStatus.PICKING_UP:
                if self.time >= om.t_matched + om.pickup_time:
                    om.status = OrderStatus.IN_TRIP
            if om.status == OrderStatus.IN_TRIP:
                if self.time >= om.t_end:
                    om.status = OrderStatus.COMPLETED
        
        # 记录司机状态
        logger.log_debug(f"DriverContext Info: ", self.drivers, module="simulator")

        # 记录进行中的订单状态
        logger.log_debug(f"OrderContext Info(matched): ", self.matched_requests, module="simulator")

    def _update_time(self):
        """更新时间"""
        self.time += self.delta_t
        self.current_step += 1
        
        # result_date = datetime.strptime(self.experiment_date, "%Y-%m-%d") + timedelta(minutes=self.time)
        # self.curent_experiment_time = result_date.strftime("%Y-%m-%d %H:%M:%S")

    # 每天结束时，处理 buffer
    def finalize_run(self):
        """
        在仿真结束或需要获取完整匹配记录时调用
        """
        # 计算并打印当日指标
        gmv, _ = self.metrics_calculator.calculate_and_log_metrics(
            day=self.experiment_date,
            matched_requests=self.matched_requests,
            num_all_requests=self.num_all_requests
        )
        
        # 累积到总指标
        self.total_gmv += gmv
        self.total_matched_requests += len(self.matched_requests)
        self.total_all_requests += self.num_all_requests

        # 如果是最后一天，打印总指标
        # 注意：这里需要外部逻辑判断是否是最后一天，或者在外部循环结束后单独调用
        # 这里仅打印当日
        
        if self.matched_requests_buffer:
            self.matched_requests_buffer = []

    def log_overall_metrics(self):
        """打印所有实验日期的总计指标"""
        total_ocr = self.total_matched_requests / self.total_all_requests if self.total_all_requests > 0 else 0.0
        log_msg = (f"Overall Metrics: "
                   f"Total GMV: {self.total_gmv:.2f}, "
                   f"Total OCR: {total_ocr:.2%}, "
                   f"Total Matched: {self.total_matched_requests}, "
                   f"Total All: {self.total_all_requests}")
        logger.log_info(log_msg, module="simulator")
        print(log_msg)
