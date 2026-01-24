import os
import pickle
import geopandas as gpd
from typing import Tuple, Optional, Dict
from config.config import Config

class TaxiZoneSpatialIndexer:
    """
    处理纽约市出租车区域 Shapefile 数据。
    功能：读取几何数据，转换为经纬度坐标，计算区域质心，并提供查询接口。
    """

    def __init__(self, config: Config):
        """
        初始化处理器。

        :param config: 配置对象
        """
        self.config = config
        self.shapefile_path = os.path.join(
            config.taxi_zone_shapefile_dir, config.taxi_zone_shapefile_name
        )
        self.pickle_path = os.path.join(
            config.extractor_output_data_dir, config.taxi_zone_centroids_pickle_filename
        )
        self.boundary_pickle_path = os.path.join(
            config.extractor_output_data_dir, config.taxi_zone_boundary_pickle_filename
        )
        self.centroid_map: Dict[int, Tuple[float, float]] = {}
        self.boundary: Dict[str, float] = {} # {'min_lng': ..., 'max_lng': ..., 'min_lat': ..., 'max_lat': ...}
        
        # 如果 pickle 文件不存在，自动执行处理流程
        if not os.path.exists(self.pickle_path) or not os.path.exists(self.boundary_pickle_path):
            print(f"[Info] taxi_zone 缓存文件未找到或不完整，开始处理 Shapefile: {self.shapefile_path}")
            self._process_and_cache_data()
        else:
            print(f"[Info] 检测到 taxi_zone 缓存文件，准备就绪。")

    def _process_and_cache_data(self):
        """
        内部方法：读取 Shapefile，转换坐标系，计算质心并序列化存储。
        """
        if not os.path.exists(self.shapefile_path):
            raise FileNotFoundError(f"未在指定目录找到 'taxi_zones.shp'。请确认路径: {self.shapefile_path}")

        try:
            # 1. 读取 Shapefile
            gdf = gpd.read_file(self.shapefile_path)

            # 2. 坐标系转换 (关键步骤)
            # 原始数据通常是投影坐标 (如 State Plane)，必须转换为 WGS84 (EPSG:4326) 才能获取经纬度
            if gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)

            # 3. 计算质心 (Centroid)
            # 在 WGS84 坐标系下计算质心时，geopandas 会抛出 UserWarning
            # 因为 WGS84 是地理坐标系（度），而非投影坐标系（米）。
            # 为了更精确的质心计算，我们可以先临时转换到适用于纽约的投影坐标系 (例如 EPSG:2263)
            # 但对于城市区域，直接在 WGS84 上计算误差在可接受范围内。
            # 为了消除警告并提高严谨性，建议在投影坐标系计算：
            gdf_projected = gdf.to_crs(epsg=2263) # New York Long Island projection
            centroids_projected = gdf_projected.geometry.centroid
            # 再转回经纬度
            gdf['centroid_geom'] = centroids_projected.to_crs(epsg=4326)

            # 4. 构建字典映射: LocationID -> (Longitude, Latitude)
            # 根据文档，LocationID 是区域的唯一标识符
            for _, row in gdf.iterrows():
                try:
                    loc_id = int(row['LocationID'])
                    # Point 对象属性 .x 为经度, .y 为纬度
                    lon = row['centroid_geom'].x
                    lat = row['centroid_geom'].y
                    self.centroid_map[loc_id] = (lon, lat)
                except KeyError:
                    continue

            # 5. 计算总体边界范围
            # 使用转换后的经纬度计算全局范围
            all_lons = [coords[0] for coords in self.centroid_map.values()]
            all_lats = [coords[1] for coords in self.centroid_map.values()]
            
            if all_lons and all_lats:
                self.boundary = {
                    'min_lng': min(all_lons),
                    'max_lng': max(all_lons),
                    'min_lat': min(all_lats),
                    'max_lat': max(all_lats)
                }

            # 6. 存入 Pickle 文件
            with open(self.pickle_path, 'wb') as f:
                pickle.dump(self.centroid_map, f)
            
            with open(self.boundary_pickle_path, 'wb') as f:
                pickle.dump(self.boundary, f)
            
            print(f"[Success] 处理完成。")
            print(f"  - 已缓存 {len(self.centroid_map)} 个区域坐标至 {self.pickle_path}")
            print(f"  - 已缓存边界范围至 {self.boundary_pickle_path}: {self.boundary}")

        except Exception as e:
            print(f"[Error] 处理 Shapefile 时发生错误: {e}")
            raise

    def get_coordinates(self, zone_id: int) -> Optional[Tuple[float, float]]:
        """
        接口：输入区域序号，输出经纬度。

        :param zone_id: 出租车区域编号 (LocationID, e.g., 1-263)
        :return: (经度, 纬度) 元组，如果未找到则返回 None
        """
        # 懒加载：如果内存中没有数据，先从 pickle 读取
        if not self.centroid_map:
            if os.path.exists(self.pickle_path):
                with open(self.pickle_path, 'rb') as f:
                    self.centroid_map = pickle.load(f)
            else:
                # 理论上 __init__ 已经处理过，这里是双重保险
                self._process_and_cache_data()

        return self.centroid_map.get(zone_id)

    def get_boundary(self) -> Dict[str, float]:
        """
        接口：返回整个数据集的经纬度边界范围。

        :return: 包含 min_lng, max_lng, min_lat, max_lat 的字典
        """
        if not self.boundary:
            if os.path.exists(self.boundary_pickle_path):
                with open(self.boundary_pickle_path, 'rb') as f:
                    self.boundary = pickle.load(f)
            else:
                self._process_and_cache_data()
        
        return self.boundary

    def get_all_zone_ids(self) -> list[int]:
        """
        接口：返回所有已知的出租车区域编号。

        :return: 包含所有区域编号的列表
        """
        if not self.centroid_map:
            if os.path.exists(self.pickle_path):
                with open(self.pickle_path, 'rb') as f:
                    self.centroid_map = pickle.load(f)
            else:
                self._process_and_cache_data()
        
        return list(self.centroid_map.keys())
