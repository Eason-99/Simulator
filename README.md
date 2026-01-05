# ODDR Simulator

网约车订单-司机匹配（ODDR）仿真器

## 目录结构

```
Simulator/
├── data_processing/      # 数据预处理模块
│   ├── extractor.py     # 模块1：数据提取（当前为空pickle占位）
│   └── preprocessor.py  # 模块2：数据预处理（当前原样传递）
│
├── environment/          # 环境仿真模块
│   ├── simulator.py     # 核心仿真器
│   ├── state_manager.py # 状态管理
│   ├── metrics.py       # 模块5：效果计算
│   └── utils.py         # 工具函数
│
├── interface/            # 算法接口模块
│   ├── algorithm_interface.py  # 核心算法接口抽象类
│   └── result_processor.py    # 模块4：结果处理（当前原样传递）
│
├── config/               # 配置管理
│   └── config.py
│
└── main.py               # 模块3：主程序
```

## 模块说明

### 模块1：数据提取器（extractor.py）
- **当前状态**：创建空的pickle文件占位
- **功能**：从parquet原始数据中提取有效数据，固化为pickle文件
- **TODO**：实现实际的parquet数据提取逻辑

### 模块2：数据预处理器（preprocessor.py）
- **当前状态**：原样传递，不做任何处理
- **功能**：对pickle文件进行预处理，生成处理后的pickle文件
- **TODO**：实现实际的数据预处理逻辑

### 模块3：主程序（main.py）
- **功能**：调用核心算法接口，分批按时间间隔进行仿真
- **流程**：
  1. 加载数据
  2. 初始化仿真器
  3. 按日期循环运行仿真
  4. 每个时间步调用算法接口
  5. 计算并保存效果指标

### 模块4：结果处理器（result_processor.py）
- **当前状态**：原样传递，不做任何处理
- **功能**：处理算法的返回方案，得到最终的方案
- **TODO**：实现方案验证、冲突解决等逻辑

### 模块5：效果计算（metrics.py）
- **功能**：根据最终方案计算效果指标
- **指标**：
  - GMV（总交易额）
  - OCR（订单完成率）
  - 平均每单收益
  - 司机平均完成订单数

## 使用方法

### 1. 实现算法接口

创建自己的算法类，继承 `ODDRAlgorithmInterface`：

```python
from interface.algorithm_interface import ODDRAlgorithmInterface
import pandas as pd
from typing import List, Tuple

class MyAlgorithm(ODDRAlgorithmInterface):
    def dispatch(self, wait_requests, driver_table, driver_reward_table, current_time, **kwargs):
        # 实现订单-司机匹配逻辑
        # 返回: [(order_id, driver_id), ...]
        return []
    
    def reposition(self, idle_drivers, grid_info, current_time, **kwargs):
        # 实现司机重定位逻辑（可选）
        # 返回: [(driver_id, target_grid_id), ...]
        return []
```

### 2. 配置参数

修改 `config/config.py` 或创建配置对象：

```python
from config.config import Config

config = Config(
    start_date='2015-07-27',
    end_date='2015-07-31',
    dataset='large',
    # ... 其他参数
)
```

### 3. 运行仿真

```python
from main import main
from config.config import Config
from your_algorithm import YourAlgorithm

config = Config()
algorithm = YourAlgorithm()
main(config, algorithm)
```

## 数据格式

### 输入数据

仿真器需要以下数据文件（放在 `data/{dataset}/` 目录下）：

1. **请求数据**：`all_requests_0.1.pickle`
   - 字典格式，键为日期（'YYYY-MM-DD'），值为字典
   - 内层字典键为时间间隔（秒），值为请求列表

2. **司机数据**：`df_driver_info_100.pickle`
   - DataFrame格式，包含字段：driver_id, start_time, end_time, lng, lat, grid_id

3. **订单数量数据**：`all_requests_0.1_origin_order_num.csv`
   - CSV格式，包含时间序列的订单数量信息

4. **网格信息**：`hex_updated_r300_info.csv`
   - CSV格式，包含网格ID、中心坐标等信息

5. **网格邻接关系**：`hexo_updated_r300_adj.csv`
   - CSV格式，网格邻接矩阵

## 输出结果

仿真结果保存在 `save/{dataset}/{description}/` 目录下：

- `matched_requests/`: 匹配的订单
- `driver_reward_table/`: 司机奖励表
- `others/`: 其他统计信息
- `overall_result.txt`: 总体效果指标

## 注意事项

1. **模块1、2、4当前为占位实现**，需要根据实际需求完善
2. **算法接口必须实现** `dispatch` 方法，`reposition` 方法可选
3. **数据格式**需要符合要求，否则可能导致错误
4. **时间步长**默认60秒，可根据需要调整

## 开发计划

- [ ] 实现模块1：parquet数据提取
- [ ] 实现模块2：数据预处理
- [ ] 实现模块4：结果验证和处理
- [ ] 添加缓存机制
- [ ] 添加可视化功能

