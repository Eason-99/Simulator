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
                 request_all: Dict[str, Any],
                 driver_info: pd.DataFrame,
                 order_num_origin: pd.DataFrame,
                 algorithm: ODDRAlgorithmInterface,
                 result_processor: ResultProcessor = None,
                 start_date: str = '2015-07-27',
                 end_date: str = '2015-07-31',
                 start_time: float = 0,
                 end_time: float = 86400,
                 delta_t: float = 60,
                 vehicle_speed: float = 6.33,
                 pickup_dis_threshold: float = 950,
                 maximum_wait_time_mean: float = 300,
                 max_idle_time: float = 300,
                 request_interval: float = 60):
        """
        初始化仿真器
        
        Args:
            request_all: 所有订单请求数据（字典，键为日期）
            driver_info: 司机信息DataFrame
            order_num_origin: 订单数量数据
            algorithm: ODDR算法接口实例
            result_processor: 结果处理器（可选）
            start_date: 开始日期
            end_date: 结束日期
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            delta_t: 时间步长（秒）
            vehicle_speed: 车辆速度（米/秒）
            pickup_dis_threshold: 接单距离阈值（米）
            maximum_wait_time_mean: 最大等待时间均值（秒）
            max_idle_time: 最大空闲时间（秒）
            request_interval: 订单生成间隔（秒）
        """
        # 基本参数
        self.start_date = start_date
        self.end_date = end_date
        self.t_initial = start_time
        self.t_end = end_time
        self.delta_t = delta_t
        self.vehicle_speed = vehicle_speed
        self.pickup_dis_threshold = pickup_dis_threshold
        self.maximum_wait_time_mean = maximum_wait_time_mean
        self.max_idle_time = max_idle_time
        self.request_interval = request_interval
        
        # 数据
        self.request_all = request_all
        self.driver_info = driver_info
        self.order_num_origin = order_num_origin
        
        # 算法接口
        self.algorithm = algorithm
        self.result_processor = result_processor or ResultProcessor()
        
        # 状态管理器
        self.state_manager = StateManager()
        
        # 实验日期
        self.experiment_date = None
        self.curent_experiment_time = None
        
        # 计算步数
        self.finish_run_step = int(self.t_end // self.delta_t)
        
        # 初始化状态
        self.driver_table = None
        self.driver_reward_table = None
        self.wait_requests = None
        self.matched_requests = None
        self.matched_requests_buffer = None
        self.request_databases = None
        self.time = None
        self.current_step = None
        self.num_all_requests = None
        
        # 统计表
        self.matched_requests_arrive_num = None
        self.matched_requests_origin = None
    
    def reset(self, experiment_date: str):
        """
        重置环境
        
        Args:
            experiment_date: 实验日期（格式：'YYYY-MM-DD'）
        """
        self.experiment_date = experiment_date
        
        # 初始化请求数据库
        self.request_databases = deepcopy(self.request_all.get(experiment_date, {}))
        
        # 初始化司机表
        self.driver_table = self.state_manager.initialize_driver_table(self.driver_info)
        # 强制将数值列转换为 float，防止 int/float 混合赋值告警
        cols_to_float = ['remaining_time', 'target_loc_lng', 'target_loc_lat', 'total_idle_time']
        for col in cols_to_float:
            if col in self.driver_table.columns:
                self.driver_table[col] = self.driver_table[col].astype(float)
        # 强制将 matched_order_id 设为 object 类型，以便存入字符串
        # if 'matched_order_id' in self.driver_table.columns:
        self.driver_table['matched_order_id'] = self.driver_table['matched_order_id'].astype(object)

        # 初始化订单表
        request_tables = self.state_manager.initialize_request_tables()
        self.wait_requests = request_tables['wait_requests']
        self.matched_requests = request_tables['matched_requests']
        self.matched_requests_buffer = []

        # 初始化司机奖励表
        self.driver_reward_table = self.state_manager.initialize_driver_reward_table(self.driver_table)
        # 强制将奖励列转换为 float
        if 'current_overall_reward' in self.driver_reward_table.columns:
            self.driver_reward_table['current_overall_reward'] = \
                self.driver_reward_table['current_overall_reward'].astype(float)

        # 初始化统计表
        time_index = pd.date_range(start=self.start_date, end=self.end_date, freq='min')
        columns = ['time'] + [f'{i}' for i in range(263)]
        zero_data = np.zeros((len(time_index), 263))
        self.matched_requests_arrive_num = pd.DataFrame(zero_data, columns=columns[1:])
        self.matched_requests_arrive_num.insert(0, 'time', time_index)
        self.matched_requests_origin = deepcopy(self.matched_requests_arrive_num)

        # 初始化时间
        self.time = deepcopy(self.t_initial)
        self.current_step = int(self.time // self.delta_t)
        self.num_all_requests = 0
        
        # 更新时间字符串
        result_date = datetime.strptime(self.experiment_date, "%Y-%m-%d") + timedelta(minutes=self.current_step)
        self.curent_experiment_time = result_date.strftime("%Y-%m-%d %H:%M:%S")

    
    def get_order_driver_pairs(self, wait_requests: pd.DataFrame, driver_table: pd.DataFrame) -> pd.DataFrame:
        """
        获取订单-司机候选对
        
        Args:
            wait_requests: 等待订单
            driver_table: 司机表
            
        Returns:
            DataFrame: 订单-司机候选对
        """
        idle_driver_table = driver_table[driver_table['status'] == 0]
        num_wait_request = len(wait_requests)
        num_idle_driver = len(idle_driver_table)
        
        if num_wait_request == 0 or num_idle_driver == 0:
            return pd.DataFrame()
        
        # 构建候选对
        request_array = wait_requests.loc[:, [
            'order_id', 'trip_time', 'origin_lng', 'origin_lat', 'dest_lng', 'dest_lat',
            'immediate_reward', 'wait_time', 'maximum_wait_time',
            'origin_order_num_1h_ago', 'dest_order_num_1h_ago'
        ]].values
        request_array = np.repeat(request_array, num_idle_driver, axis=0)
        
        driver_loc_array = idle_driver_table.loc[:, ['lng', 'lat', 'driver_id']].values
        driver_loc_array = np.tile(driver_loc_array, (num_wait_request, 1))
        
        # 计算距离
        dis_array = distance_array(request_array[:, 2:4], driver_loc_array[:, :2])
        
        # 过滤距离阈值
        flag = np.where(dis_array <= self.pickup_dis_threshold)[0]
        
        if len(flag) == 0:
            return pd.DataFrame()
        
        # 构建DataFrame
        columns_name = [
            'driver_id', 'order_id', 'trip_time', 'origin_lng', 'origin_lat', 'dest_lng', 'dest_lat',
            'immediate_reward', 'wait_time', 'maximum_wait_time', 'origin_order_num_1h_ago', 'dest_order_num_1h_ago', 'order_driver_distance'
        ]
        order_driver_pair = np.hstack((
            driver_loc_array[flag, 2].reshape(-1, 1),
            request_array[flag, 0:11].reshape(-1, 11),
            dis_array[flag].reshape(-1, 1)
        ))
        
        return pd.DataFrame(order_driver_pair, columns=columns_name)
    
    def step(self):
        """
        执行一个时间步
        """
        # Step 1: 生成新订单
        self._generate_new_orders()

        # Step 2: 获取订单-司机候选对
        wait_requests = deepcopy(self.wait_requests)
        driver_table = deepcopy(self.driver_table)
        
        # 添加历史订单数（如果需要）
        # TODO: 实现历史订单数计算

        # 调试打印订单-司机候选对信息
        logger.log_order_driver_info(wait_requests, driver_table, module="simulator")
        
        # Step 3: 调用算法接口
        # 调用算法进行匹配
        dispatch_plan = self.algorithm.dispatch(
            wait_requests=wait_requests,
            driver_table=driver_table,
            driver_reward_table=self.driver_reward_table,
            current_time=self.curent_experiment_time
        )
        
        # 打印返回方案的前3条匹配
        print("Dispatch Plan (First 3):", dispatch_plan[:3])
        
        # 处理返回方案
        final_plan = self.result_processor.process_dispatch_result(dispatch_plan)
        
        # Step 4: 应用匹配方案
        if len(final_plan) > 0:
            self._apply_dispatch_plan(final_plan, wait_requests, driver_table)

        # 在 update_time 之前打印调试信息
        logger.log_step_info(
            step_time=self.curent_experiment_time,
            num_orders=len(self.wait_requests),
            num_idle_drivers=len(self.driver_table[self.driver_table['status'] == 0]),
            num_matched_orders=len(self.matched_requests_buffer[0]) if self.matched_requests_buffer else 0 # buffer的第一个元素才是这个step匹配的订单
        )
        
        # Step 5: 更新状态
        self._update_state()
        self._update_time()

    def _apply_dispatch_plan(self,
                             dispatch_plan: List[Tuple[str, str]],
                             wait_requests: pd.DataFrame,
                             driver_table: pd.DataFrame):
        if len(dispatch_plan) == 0:
            return

        # 1. 预处理：快速构建匹配关系表
        matched_pairs = pd.DataFrame(dispatch_plan, columns=['order_id', 'driver_id'])
        
        # 2. 向量化计算距离 (替代原本的 iterrows 循环)
        # 将订单坐标 merge 进来
        matched_pairs = matched_pairs.merge(
            wait_requests[['order_id', 'origin_lng', 'origin_lat']], 
            on='order_id', how='left'
        )
        # 将司机坐标 merge 进来
        matched_pairs = matched_pairs.merge(
            driver_table[['driver_id', 'lng', 'lat']], 
            on='driver_id', how='left'
        )
        
        # 批量计算距离 (假设 distance_array 支持 numpy 数组输入)
        # 注意：这里需要确保 inputs 是 float 类型的 numpy array
        coords_o = matched_pairs[['origin_lng', 'origin_lat']].values
        coords_d = matched_pairs[['lng', 'lat']].values
        # 假设您的 distance_array 可以接收 (N,2) 的数组并返回 (N,) 的距离
        matched_pairs['pickup_distance'] = distance_array(coords_o, coords_d)
        
        # 3. 筛选有效订单 (逻辑保持不变，但利用 merge 的结果更安全)
        valid_mask = (
            self.wait_requests['order_id'].isin(matched_pairs['order_id']) & 
            (self.wait_requests['wait_time'] <= self.wait_requests['maximum_wait_time'])
        )
        df_matched = self.wait_requests[valid_mask].copy()
        
        if len(df_matched) == 0:
            return

        # 确保 df_matched 和 matched_pairs 对齐
        # 只保留那些还在 df_matched 里的 pair
        matched_pairs = matched_pairs[matched_pairs['order_id'].isin(df_matched['order_id'])].reset_index(drop=True)
        # 重新对齐 df_matched 的顺序以匹配 matched_pairs
        df_matched = df_matched.set_index('order_id').loc[matched_pairs['order_id']].reset_index()

        # 4. 批量更新司机状态 (替代原本的 for 循环查找索引)
        driver_ids = matched_pairs['driver_id'].values
        # 找到这些司机在 driver_table 中的 index
        # 假设 driver_table 的 driver_id 是唯一的
        driver_indices = self.driver_table[self.driver_table['driver_id'].isin(driver_ids)].index
        
        if len(driver_indices) == 0:
            return

        # 5. 构建新订单数据 new_matched_requests
        new_matched_requests = df_matched.copy()
        new_matched_requests['t_matched'] = self.time
        new_matched_requests['pickup_distance'] = matched_pairs['pickup_distance'].values
        new_matched_requests['pickup_time'] = new_matched_requests['pickup_distance'].values / self.vehicle_speed
        new_matched_requests['t_end'] = self.time + new_matched_requests['pickup_time'].values + \
                                        new_matched_requests['trip_time'].values
        new_matched_requests['status'] = 1
        new_matched_requests['driver_id'] = matched_pairs['driver_id'].values

        # 6. 批量更新 driver_table (向量化更新)
        self.driver_table.loc[driver_indices, 'status'] = 1
        # 注意：这里需要确保 loc 的顺序和 new_matched_requests 的顺序一致
        # 为了严谨，建议通过 driver_id 映射，但如果上面是对齐的，可以直接赋值
        # 这里简化处理，直接用 map 映射回去更新
        driver_id_to_idx = dict(zip(self.driver_table.loc[driver_indices, 'driver_id'], driver_indices))
        sorted_indices = [driver_id_to_idx[did] for did in new_matched_requests['driver_id']]
        
        self.driver_table.loc[sorted_indices, 'target_loc_lng'] = new_matched_requests['dest_lng'].values
        self.driver_table.loc[sorted_indices, 'target_loc_lat'] = new_matched_requests['dest_lat'].values
        self.driver_table.loc[sorted_indices, 'remaining_time'] = (
            new_matched_requests['t_end'].values - new_matched_requests['t_matched'].values
        ).astype(float)
        self.driver_table.loc[sorted_indices, 'matched_order_id'] = new_matched_requests['order_id'].values
        self.driver_table.loc[sorted_indices, 'total_idle_time'] = 0

        # 7. 批量更新奖励 (替代原本的 iterrows)
        # 使用 groupby 统计每个司机的新增奖励和单数
        rewards_sum = new_matched_requests.groupby('driver_id')['immediate_reward'].sum()
        counts_sum = new_matched_requests.groupby('driver_id').size()
        
        # 利用 map 更新
        mask_reward = self.driver_reward_table['driver_id'].isin(rewards_sum.index)
        if mask_reward.any():
            # 这种写法比循环快得多
            self.driver_reward_table.loc[mask_reward, 'current_overall_reward'] += \
                self.driver_reward_table.loc[mask_reward, 'driver_id'].map(rewards_sum).fillna(0)
            self.driver_reward_table.loc[mask_reward, 'num_finished_order'] += \
                self.driver_reward_table.loc[mask_reward, 'driver_id'].map(counts_sum).fillna(0)

        # 8. 【核心修改】解决 Concat 告警和性能问题
        # 不再直接 concat DataFrame，而是存入列表
        self.matched_requests_buffer.append(new_matched_requests)
        
        # 9. 更新等待队列
        con_matched = self.wait_requests['order_id'].isin(new_matched_requests['order_id'])
        con_keep_wait = self.wait_requests['wait_time'] <= self.wait_requests['maximum_wait_time']
        self.wait_requests = self.wait_requests[~con_matched & con_keep_wait].reset_index(drop=True)


    def _generate_new_orders(self):
        """生成新订单"""
        count_interval = int(np.floor(self.time / self.request_interval))
        time_key = str(count_interval * self.request_interval)

        if time_key not in self.request_databases:
            return

        request_database = self.request_databases[time_key]
        self.num_all_requests += len(request_database)

        if len(request_database) == 0:
            return

        # 解析订单数据
        order_id = [request[0] for request in request_database]
        requests = np.array([request[1:] for request in request_database])

        column_name = [
            'origin_lng', 'origin_lat', 'dest_lng', 'dest_lat', 'immediate_reward',
            'trip_distance', 'trip_time', 'designed_reward'
        ]

        wait_info = pd.DataFrame(requests, columns=column_name)
        wait_info['order_id'] = order_id
        wait_info['t_start'] = self.time
        wait_info['wait_time'] = 0
        wait_info['status'] = 0
        wait_info['maximum_wait_time'] = self.maximum_wait_time_mean
        wait_info['cancel_prob'] = 0
        wait_info['weight'] = 1.0

        # 添加缺失的列
        for col in self.state_manager.request_columns:
            if col not in wait_info.columns:
                wait_info[col] = None

        # 显式设置列的数据类型
        for col in wait_info.columns:
            if wait_info[col].isna().all():
                wait_info[col] = wait_info[col].astype(object)

        # 【修改点】在拼接前检查是否为空
        if not wait_info.empty:
            # 如果累积池(self.wait_requests)是空的，直接赋值，不要 concat
            if self.wait_requests.empty:
                self.wait_requests = wait_info
            else:
                # 只有当两边都有数据时，才进行 concat
                self.wait_requests = pd.concat([self.wait_requests, wait_info], ignore_index=True)
    
    def _update_state(self):
        """更新状态"""
        # 更新司机状态
        self.driver_table = self.state_manager.update_driver_state(
            self.driver_table, self.delta_t, self.vehicle_speed
        )
        
        # 更新等待订单等待时间
        self.wait_requests = self.state_manager.update_request_wait_time(
            self.wait_requests, self.delta_t
        )
        
        # TODO：理论上应该每天整合，但是debug需要每个step看一下订单状态
        self.finalize_run()
        
        # 记录司机状态
        logger.log_driver_states(self.driver_table, module="simulator")

        # 记录进行中的订单状态
        logger.log_in_progress_orders(self.matched_requests, module="simulator")

    def _update_time(self):
        """更新时间"""
        self.time += self.delta_t
        self.current_step += 1
        
        result_date = datetime.strptime(self.experiment_date, "%Y-%m-%d") + timedelta(minutes=self.current_step)
        self.curent_experiment_time = result_date.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            Dict: 当前状态字典
        """
        return {
            'wait_requests': self.wait_requests,
            'driver_table': self.driver_table,
            'driver_reward_table': self.driver_reward_table,
            'current_time': self.curent_experiment_time,
            'time': self.time,
            'current_step': self.current_step
        }

    # 每天结束时，将列表合并回 DataFrame
    def finalize_run(self):
        """
        在仿真结束或需要获取完整 matched_requests 时调用
        将列表中的数据合并回 DataFrame
        """
        if self.matched_requests_buffer:
            # 1. 批量合并 list 中的所有 DataFrame
            new_matches = pd.concat(self.matched_requests_buffer, axis=0, ignore_index=True)
            
            # 2. 如果原始 matched_requests 是空的，直接赋值
            if self.matched_requests.empty:
                self.matched_requests = new_matches
            else:
                # 3. 如果不为空（极少情况），拼接到后面
                self.matched_requests = pd.concat(
                    [self.matched_requests, new_matches], 
                    axis=0, 
                    ignore_index=True
                )
            
            # 4. 清空列表，防止重复合并
            self.matched_requests_buffer = []