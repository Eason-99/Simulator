from dataclasses import dataclass
from typing import Optional

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