# ODDR Simulator

网约车订单-司机匹配（ODDR）仿真器

## 目录结构

```
Simulator/
├── data_processing/      # 数据处理模块
│   ├── extractor.py     # 模块1：数据提取。从Parquet原始数据提取并过滤订单请求，生成二级字典结构的Pickle文件（日期 -> 时间戳）。
│   ├── preprocessor.py  # 模块2：数据预处理。支持对Pickle数据进行采样（比例/随机）以及在特定区域和时段增减订单，支持Debug日志打印。
│   ├── taxi_zone_processor.py # 出租车分区处理，处理地理区域信息。
│   └── data_colums.md   # 数据列定义文档。
│
├── environment/          # 环境仿真模块
│   ├── simulator.py     # 核心仿真器。负责模拟时间推进、订单生成和状态更新。
│   ├── state_manager.py # 状态管理。管理司机状态、订单池等。
│   ├── metrics.py       # 模块5：效果计算。计算GMV、OCR等核心指标。
│   └── utils.py         # 工具函数。
│
├── interface/            # 算法接口模块
│   ├── algorithm_interface.py  # 核心算法接口抽象类，定义 dispatch 和 reposition 接口。
│   └── result_processor.py    # 模块4：结果处理。验证算法返回方案的有效性。
│
├── config/               # 配置管理
│   └── config.py        # 全局配置参数，包括日期范围、数据集路径、仿真步长等。
│
├── debug/                # 调试辅助
│   ├── debug_logger.py  # 调试日志记录工具。
│   └── inspect_data.py  # 数据检查脚本。
│
├── main.py               # 模块3：主程序。连接各模块，驱动整个仿真流程。
├── example_algorithm.py  # 示例算法实现。
├── generate_demo_data.py # 演示数据生成脚本。
└── requirements.txt      # 项目依赖。
```

## 核心文件说明

### 1. 数据提取器 ([`data_processing/extractor.py`](data_processing/extractor.py))
- **功能**：从原始的 Parquet 格式（如 `yellow_tripdata`）中提取有效订单请求，并将其固化为仿真器所需的 Pickle 文件。
- **输入**：
  - `parquet_path`: 原始 Parquet 文件路径（例如 `yellow_tripdata_2025-01.parquet`）。
- **输出**：
  - `data/*.pickle`: 嵌套字典格式的 Pickle 文件。
- **数据结构**：
  - 格式：`{ 'YYYY-MM-DD': { 'seconds_from_start': [order_data_list], ... }, ... }`
  - `order_data_list` 包含：`[order_id, origin_lng, origin_lat, dest_lng, dest_lat, immediate_reward, trip_distance, trip_time, designed_reward]`。
- **特点**：支持限制读取行数（`n_rows`），自动将时间戳转换为当天偏移秒数，并按 60s 步长取整。

### 2. 数据预处理器 ([`data_processing/preprocessor.py`](data_processing/preprocessor.py))
- **功能**：对提取后的 Pickle 文件进行采样或模拟增减订单，用于构造不同的实验场景。
- **输入**：
  - `input_name`: `data/` 目录下已有的 Pickle 文件名。
- **输出**：
  - `data/*_processed.pickle`: 处理后的 Pickle 文件。
- **主要操作**：
  - **数据采样**：支持按比例（`ratio`）从头选取或随机选取订单。
  - **订单干预**：支持在特定区域（`target_zones`）和特定时间段（`time_ranges`）内增加（复制现有订单模板并修改 ID）或减少订单。
- **Debug 控制**：
  - `DEBUG_LEVEL = 1`：打印总数对比。
  - `DEBUG_LEVEL = 2`：打印详细的订单增减日志。

### 3. 出租车区域处理器 ([`data_processing/taxi_zone_processor.py`](data_processing/taxi_zone_processor.py))
- **功能**：处理纽约市出租车分区的地理信息（Shapefile）。
- **输入**：
  - `shapefile_dir`: 包含 `taxi_zones.shp` 等文件的目录。
- **输出**：
  - `zone_centroids.pkl`: 包含各区域 `LocationID` 到经纬度质心映射的缓存文件。
- **主要功能**：
  - 将投影坐标系转换为 WGS84 经纬度。
  - 计算每个分区的地理质心。
  - 提供 `get_coordinates(zone_id)` 接口查询指定区域的中心坐标。

### 4. 主仿真程序 ([`main.py`](main.py))
- **功能**：整个仿真系统的入口，负责加载配置、驱动仿真循环、调用算法并统计结果。
- **输入**：
  - `config/config.py`: 仿真参数配置。
  - `data/`: 订单请求、司机信息等 Pickle 文件。
- **输出**：
  - `save/`: 包含每日匹配详情（`matched_requests_*.csv`）、司机收益表（`driver_reward_table_*.csv`）及总体性能报告（`overall_result.txt`）。
- **核心流程**：
  1. **初始化**：加载订单、司机数据，初始化 `Simulator`。
  2. **仿真循环**：按日期和时间步长推进，每步调用算法接口的 `dispatch` 和 `reposition`。
  3. **指标统计**：通过 `MetricsCalculator` 计算 GMV、OCR（订单成交率）等指标并持久化。


## 使用方法

### 1. 实现算法接口

继承 `ODDRAlgorithmInterface` 实现 `dispatch`（必选）和 `reposition`（可选）：

```python
class MyAlgorithm(ODDRAlgorithmInterface):
    def dispatch(self, wait_requests, driver_table, driver_reward_table, current_time, **kwargs):
        # wait_requests: 当前待匹配订单
        # driver_table: 可用司机信息
        return [("order_1", "driver_A"), ...]
```

### 2. 数据准备与预处理

1. 使用 `extractor.py` 从原始 Parquet 提取数据。
2. (可选) 使用 `preprocessor.py` 调整数据分布。

### 3. 运行仿真

```bash
python main.py
```

## 数据格式

### 输入 Pickle 结构
- **请求数据**：二级嵌套字典。
  - `Key 1`: 日期字符串 `'2015-07-27'`
  - `Key 2`: 秒数时间戳字符串 `'3600'`
  - `Value`: 列表 `[order_id, origin_lng, origin_lat, dest_lng, dest_lat, reward, distance, time, ...]`

## 开发计划

- [x] 实现模块1：Parquet 数据精确提取与转换
- [x] 实现模块2：支持增减订单的动态预处理逻辑
- [ ] 模块4：完善复杂的冲突解决策略
- [ ] 添加实时可视化监控面板
