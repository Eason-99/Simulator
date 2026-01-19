| 字段名 (English) | 中文名称 | 中文解释 |
| :--- | :--- | :--- |
| order_id | 订单 ID | 代表由 TLC 授权车辆完成的单次行程标识符 。 |
| origin_lng | 起点经度 | 乘客上车地点的经度坐标，对应原始数据中的上车地点 。 |
| origin_lat | 起点纬度 | 乘客上车地点的纬度坐标，对应原始数据中的上车地点 。 |
| dest_lng | 终点经度 | 乘客下车地点的经度坐标，对应原始数据中的下车地点 。 |
| dest_lat | 终点纬度 | 乘客下车地点的纬度坐标，对应原始数据中的下车地点 。 |
| immediate_reward | 即时奖励 | 订单完成后的直接收益，对应原始行程记录中的分项运费 。 |
| trip_distance | 行程距离 | 行程记录中捕获的单次行程实际行驶距离 。 |
| trip_time | 行程时长 | 根据记录中的上车与下车日期/时间计算出的持续秒数 。 |
| designed_reward | 设计奖励 | 用于算法训练的预设奖励值（非 TLC 原始采集字段，需预处理计算）。 |


| 数据来源 (Parquet 列名) | 字段名 (English) | 中文名称 | 中文解释 |
| :--- | :--- | :--- | :--- |
| **df.index** (或自生成) | order_id | 订单 ID | 代表由 TLC 授权车辆完成的单次行程标识符 [cite: 7]。 |
| **PULocationID** (需映射) | origin_lng | 起点经度 | 乘客上车地点的经度坐标。原始数据仅提供 1-263 的区域编号，需通过 Shapefile 转换 [cite: 102]。 |
| **PULocationID** (需映射) | origin_lat | 起点纬度 | 乘客上车地点的纬度坐标。原始数据仅提供 1-263 的区域编号，需通过 Shapefile 转换 [cite: 102]。 |
| **DOLocationID** (需映射) | dest_lng | 终点经度 | 乘客下车地点的经度坐标。原始数据仅提供 1-263 的区域编号，需通过 Shapefile 转换 [cite: 102]。 |
| **DOLocationID** (需映射) | dest_lat | 终点纬度 | 乘客下车地点的纬度坐标。原始数据仅提供 1-263 的区域编号，需通过 Shapefile 转换 [cite: 102]。 |
| **total_amount** | immediate_reward | 即时奖励 | 订单完成后的直接收益，对应原始行程记录中的费用字段。 |
| **trip_distance** | trip_distance | 行程距离 | 行程记录中捕获的单次行程实际行驶距离。 |
| **tpep_pickup_datetime** & **tpep_dropoff_datetime** | trip_time | 行程时长 | 根据记录中的上车与下车日期/时间计算出的持续秒数。 |
| **total_amount** (通常) | designed_reward | 设计奖励 | 用于算法训练的预设奖励值（非 TLC 原始采集字段，需预处理计算）。 |