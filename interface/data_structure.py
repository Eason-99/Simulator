from dataclasses import dataclass
from enum import Enum
from typing import Optional

# 传给算法的Order类
@dataclass
class Order:
    order_id: int
    origin_grid_id: int
    dest_grid_id: int
    request_time: float
    max_wait_time: float
    trip_time: float
    price: float
    origin_lng: Optional[float] = None
    origin_lat: Optional[float] = None
    dest_lng: Optional[float] = None
    dest_lat: Optional[float] = None

class OrderStatus(Enum):
    WAITING = 0           # 等待匹配
    PICKING_UP = 1        # 司机前往接客
    IN_TRIP = 2           # 行程中
    COMPLETED = 3         # 已完成
    EXPIRED = 4           # 超时失效

# 在simulator中维护的Order类，包含状态等信息
@dataclass
class OrderContext:
    order: Order
    order_date: str       # 订单日期 (YYYY-MM-DD)
    status: OrderStatus
    driver_id: Optional[int] = None
    # 仿真过程中需要的额外属性
    pickup_time: Optional[float] = None
    t_matched: Optional[float] = None   # 订单匹配成功的时间
    t_end: Optional[float] = None

class VehicleStatus(Enum):
    IDLE = 0              # 空闲 (可接单)
    PICKING_UP = 1        # 前往接客
    IN_TRIP = 2           # 载客行程中
    REPOSITIONING = 3     # 空驶调度中
    OFFLINE = 4           # 离线

@dataclass
class Driver:
    vehicle_id: int
    grid_id: int
    lng: float
    lat: float
    status: VehicleStatus
    current_order_id: Optional[int] = None
    target_grid_id: Optional[int] = None
    remaining_travel_time: Optional[float] = None
    total_earnings: Optional[float] = None
    completed_orders: Optional[int] = None

@dataclass
class DriverContext:
    driver: Driver
    target_lng: Optional[float] = None
    target_lat: Optional[float] = None
    total_idle_time: float = 0.0

@dataclass
class GridInfo:
    grid_num: int = 0
    neighbor_grids: Optional[list] = None