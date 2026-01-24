import geopandas as gpd
from libpysal.weights import Queen, Rook
import pandas as pd
import numpy as np
import os
import pickle

def generate_adjacency_from_shapefile(shp_path, id_column='LocationID'):
    """
    从 Shapefile 计算邻接矩阵
    
    参数:
    shp_path (str): .shp 文件的路径
    id_column (str): 用作矩阵索引的唯一区域ID列名 (如 'LocationID', 'Zone', 'OBJECTID')
    
    返回:
    adj_df (pd.DataFrame): 邻接矩阵 (0和1组成, 索引和列名为区域ID)
    """
    
    # 1. 读取 Shapefile
    print(f"正在读取文件: {shp_path} ...")
    try:
        gdf = gpd.read_file(shp_path)
    except Exception as e:
        print(f"读取错误: {e}")
        return None

    # 检查 ID 列是否存在
    if id_column not in gdf.columns:
        print(f"错误: 列名 '{id_column}' 不存在。可用列: {gdf.columns.tolist()}")
        return None

    # (可选) 过滤数据：如果你只想计算 Manhattan 区域，可以取消下面注释
    if 'borough' in gdf.columns:
        gdf = gdf[gdf['borough'] == 'Manhattan'].copy()

    # 2. 确保索引唯一且类型正确 (转换为 int 避免混合类型)
    try:
        gdf[id_column] = pd.to_numeric(gdf[id_column], errors='coerce').fillna(-1).astype(int)
    except Exception as e:
        print(f"警告: 转换 {id_column} 为数值时出错: {e}")

    # 检查是否有重复的 ID
    if gdf[id_column].duplicated().any():
        print(f"警告: 发现重复的 {id_column}。正在保留第一个出现的记录并删除重复项。")
        gdf = gdf.drop_duplicates(subset=[id_column])

    # 将指定的 ID 列设为数据框的索引，这样计算出的矩阵会自动使用该 ID 作为行/列标签
    gdf = gdf.set_index(id_column)
    
    # 3. 计算空间权重矩阵 (Spatial Weights Matrix)
    # 使用 Queen 邻接规则 (共享边或点即为邻居)
    # 如果只想共享边才算邻居，改用 Rook.from_dataframe(gdf)
    print("正在计算邻接关系 (Queen Contiguity)...")
    try:
        w = Queen.from_dataframe(gdf, use_index=True)
    except Exception as e:
        # 处理可能出现的孤岛或拓扑错误
        print(f"计算警告 (可能存在孤岛): {e}")
        # 尝试构建非连接的邻接图
        w = Queen.from_dataframe(gdf, use_index=True, silence_warnings=True)

    # 4. 转换为全矩阵 (Full Adjacency Matrix)
    # w.full() 返回一个元组 (矩阵数组, ID列表)
    adj_matrix, ids = w.full()
    
    # 转换为 Pandas DataFrame，便于查看和保存
    # 此时 matrix 中的元素为 0 或 1
    adj_df = pd.DataFrame(
        adj_matrix.astype(int),
        index=ids,
        columns=ids
    )
    
    # 将对角线设为 0 (区域不与自身邻接，通常惯例)
    np.fill_diagonal(adj_df.values, 0)
    
    return adj_df

def print_adjacency_matrix_from_csv(csv_path: str, preview_rows: int = 5):
    """
    从 CSV 文件读取邻接矩阵并打印其内容。

    参数:
    csv_path (str): 邻接矩阵 CSV 文件的路径。
    preview_rows (int): 要打印的行数，默认为 5。
    """
    if not os.path.exists(csv_path):
        print(f"错误: 未找到 CSV 文件: {csv_path}")
        return

    try:
        adj_df = pd.read_csv(csv_path, index_col=0)
        print(f"\n从 {csv_path} 读取邻接矩阵成功! 维度: {adj_df.shape}")
        print("\n邻接矩阵预览 (前 {} 行):\n{}".format(preview_rows, adj_df.head(preview_rows)))
    except Exception as e:
        print(f"读取或打印 CSV 文件时发生错误: {e}")

def print_each_region_adjacent_regions_from_csv(csv_path: str):
    """
    从 CSV 文件读取邻接矩阵，并打印每个区域的相邻区域。

    参数:
    csv_path (str): 邻接矩阵 CSV 文件的路径。
    """
    if not os.path.exists(csv_path):
        print(f"错误: 未找到 CSV 文件: {csv_path}")
        return

    try:
        adj_df = pd.read_csv(csv_path, index_col=0)
        print(f"\n从 {csv_path} 读取邻接矩阵成功，正在打印每个区域的相邻区域...")

        # 统一转换为 int，处理可能的字符串索引
        adj_df.index = pd.to_numeric(adj_df.index, errors='coerce').fillna(-1).astype(int)
        adj_df.columns = pd.to_numeric(adj_df.columns, errors='coerce').fillna(-1).astype(int)
        adj_df = adj_df.sort_index(axis=0).sort_index(axis=1)

        for index, row in adj_df.iterrows():
            # 确保行数据也是数值类型
            row_numeric = pd.to_numeric(row, errors='coerce').fillna(0)
            adjacent_regions = sorted(row_numeric[row_numeric == 1].index.tolist())
            
            if adjacent_regions:
                # 显式转换 adjacent_regions 中的元素为字符串用于 join
                adj_str_list = [str(int(r)) for r in adjacent_regions]
                print(f"区域 {index} 的相邻区域: {', '.join(adj_str_list)}")
            else:
                print(f"区域 {index} 没有相邻区域。")

    except Exception as e:
        print(f"读取或处理 CSV 文件时发生错误: {e}")


def connect_regions_in_adjacency_matrix(csv_path: str, region1_id: int, region2_id: int):
    """
    从 CSV 文件读取邻接矩阵，将两个指定区域设为邻接，并保存回 CSV。

    参数:
    csv_path (str): 邻接矩阵 CSV 文件的路径。
    region1_id (int): 第一个区域的ID。
    region2_id (int): 第二个区域的ID。
    """
    if not os.path.exists(csv_path):
        print(f"错误: 未找到 CSV 文件: {csv_path}")
        return

    try:
        # 读取 CSV。注意：由于之前的保存可能包含混合类型，这里先读取再统一转换
        adj_df = pd.read_csv(csv_path, index_col=0)
        
        # 统一将索引和列名转换为 int，并处理可能的空值或无效值
        adj_df.index = pd.to_numeric(adj_df.index, errors='coerce').fillna(-1).astype(int)
        adj_df.columns = pd.to_numeric(adj_df.columns, errors='coerce').fillna(-1).astype(int)
        
        # 确保输入参数为 int
        r1, r2 = int(region1_id), int(region2_id)
        
        # 检查 ID 是否存在
        if r1 not in adj_df.index or r2 not in adj_df.index:
            print(f"错误: 区域ID {r1} 或 {r2} 不存在于邻接矩阵中。")
            # 打印当前可用的索引预览，方便调试
            print(f"可用索引范围: {adj_df.index.min()} 到 {adj_df.index.max()}")
            return

        # 设置邻接关系（统一使用数值 1）
        adj_df.loc[r1, r2] = 1
        adj_df.loc[r2, r1] = 1
        
        # 统一数据类型为 int (防止因为赋值 '1' 导致整列变成 object)
        adj_df = adj_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
        
        # 排序后保存，确保 CSV 文件本身是有序的
        adj_df = adj_df.sort_index(axis=0).sort_index(axis=1)
        
        adj_df.to_csv(csv_path)
        print(f"成功连接区域 {region1_id} 和 {region2_id}，并已更新邻接矩阵文件: {csv_path}")

    except Exception as e:
        print(f"连接区域或处理 CSV 文件时发生错误: {e}")

def generate_hop_adjacency_matrix(csv_path: str, output_hop_csv_path: str, max_hops: int = 70):
    """
    读取当前的邻接矩阵，并生成 HOP 邻接矩阵。
    
    参数:
    csv_path (str): 原始邻接矩阵 CSV 文件的路径。
    output_hop_csv_path (str): 生成的 HOP 邻接矩阵保存路径。
    max_hops (int): 最大跳数。
    """
    if not os.path.exists(csv_path):
        print(f"错误: 未找到 CSV 文件: {csv_path}")
        return

    try:
        # 1. 读取原始邻接矩阵 (0/1)
        adj_df = pd.read_csv(csv_path, index_col=0)
        adj_df.index = pd.to_numeric(adj_df.index, errors='coerce').fillna(-1).astype(int)
        adj_df.columns = pd.to_numeric(adj_df.columns, errors='coerce').fillna(-1).astype(int)
        
        # 转换为 numpy 数组进行矩阵运算
        # A 是邻接矩阵
        A = adj_df.values
        n = A.shape[0]
        
        # 初始化 HOP 矩阵，初始值为 0
        # 我们使用 float('inf') 或较大的数表示不可达，或者 0 表示未探索
        hop_matrix = np.zeros((n, n), dtype=int)
        
        # 1-hop 就是原始邻接矩阵
        hop_matrix[A == 1] = 1
        
        # 计算 power 矩阵
        # current_power = A^k
        # 如果 (A^k)_{ij} > 0 且 hop_matrix_{ij} 仍为 0 (且 i != j)，则 hop_matrix_{ij} = k
        current_power = A.copy()
        
        for k in range(2, max_hops + 1):
            print(f"正在计算 {k}-hop 邻接关系...")
            # 计算 A^k
            current_power = np.dot(current_power, A)
            
            # 找到新到达的区域：在 A^k 中大于 0，但在 hop_matrix 中仍为 0，且不是对角线
            mask = (current_power > 0) & (hop_matrix == 0)
            np.fill_diagonal(mask, False) # 排除自身
            
            hop_matrix[mask] = k
            
            # 如果没有新的跳数增加，可以提前结束
            if not mask.any():
                print(f"在 {k}-hop 时已涵盖所有可达区域。")
                break
                
        # 转换为 DataFrame
        hop_df = pd.DataFrame(hop_matrix, index=adj_df.index, columns=adj_df.columns)
        
        # 保存结果
        hop_df.to_csv(output_hop_csv_path)
        print(f"成功生成 HOP 邻接矩阵，并已保存至: {output_hop_csv_path}")
        return hop_df

    except Exception as e:
        print(f"生成 HOP 邻接矩阵时发生错误: {e}")
        import traceback
        traceback.print_exc()

def remap_region_ids(hop_csv_path: str, output_remapped_csv_path: str, output_mapping_path: str):
    """
    读取 HOP 矩阵，将区域 ID 按大小重新映射为 0~n-1，保存重映射后的矩阵和映射关系。
    
    参数:
    hop_csv_path (str): 原始 HOP 邻接矩阵 CSV 文件的路径。
    output_remapped_csv_path (str): 重映射后的 HOP 矩阵保存路径。
    output_mapping_path (str): 映射关系保存路径 (pickle 格式)。
    
    返回:
    remapped_df (pd.DataFrame): 重映射后的 HOP 矩阵
    mapping_dict (dict): 原始 ID 到新 ID 的映射关系
    reverse_mapping_dict (dict): 新 ID 到原始 ID 的映射关系
    """
    if not os.path.exists(hop_csv_path):
        print(f"错误: 未找到 CSV 文件: {hop_csv_path}")
        return None, None, None
    
    try:
        # 1. 读取原始 HOP 矩阵
        print(f"正在从 {hop_csv_path} 加载 HOP 矩阵...")
        hop_df = pd.read_csv(hop_csv_path, index_col=0)
        
        # 统一转换索引和列名为 int
        hop_df.index = pd.to_numeric(hop_df.index, errors='coerce').fillna(-1).astype(int)
        hop_df.columns = pd.to_numeric(hop_df.columns, errors='coerce').fillna(-1).astype(int)
        
        # 2. 获取所有唯一的区域 ID 并按大小排序
        unique_ids = sorted(set(hop_df.index.tolist() + hop_df.columns.tolist()))
        print(f"发现 {len(unique_ids)} 个唯一区域 ID")
        
        # 3. 创建映射关系：原始 ID -> 新 ID (0~n-1)
        mapping_dict = {old_id: new_id for new_id, old_id in enumerate(unique_ids)}
        reverse_mapping_dict = {new_id: old_id for old_id, new_id in mapping_dict.items()}
        
        # 4. 重命名索引和列
        remapped_df = hop_df.rename(index=mapping_dict, columns=mapping_dict)
        
        # 5. 保存重映射后的矩阵
        remapped_df.to_csv(output_remapped_csv_path)
        print(f"成功保存重映射后的 HOP 矩阵至: {output_remapped_csv_path}")
        
        # 6. 保存映射关系
        mapping_data = {
            'mapping_dict': mapping_dict,  # 原始 ID -> 新 ID
            'reverse_mapping_dict': reverse_mapping_dict,  # 新 ID -> 原始 ID
            'num_regions': len(unique_ids)
        }
        with open(output_mapping_path, 'wb') as f:
            pickle.dump(mapping_data, f)
        print(f"成功保存映射关系至: {output_mapping_path}")
        
        return remapped_df, mapping_dict, reverse_mapping_dict
        
    except Exception as e:
        print(f"重映射区域 ID 时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def load_mapping(mapping_path: str):
    """
    从文件加载映射关系。
    
    参数:
    mapping_path (str): 映射关系文件路径 (pickle 格式)。
    
    返回:
    mapping_data (dict): 包含映射关系的字典
    """
    if not os.path.exists(mapping_path):
        print(f"错误: 未找到映射文件: {mapping_path}")
        return None
    
    try:
        with open(mapping_path, 'rb') as f:
            mapping_data = pickle.load(f)
        print(f"成功从 {mapping_path} 加载映射关系")
        return mapping_data
    except Exception as e:
        print(f"加载映射关系时发生错误: {e}")
        return None

def query_hops_from_csv(hop_csv_path: str, query_times: int = 10):
    """
    从 CSV 读取 HOP 矩阵，并根据用户输入的两个 ID 查询跳数。
    
    参数:
    hop_csv_path (str): HOP 邻接矩阵 CSV 文件的路径。
    query_times (int): 循环查询的次数。
    """
    if not os.path.exists(hop_csv_path):
        print(f"错误: 未找到 CSV 文件: {hop_csv_path}")
        return

    try:
        # 读取 HOP 矩阵
        print(f"正在从 {hop_csv_path} 加载跳数矩阵...")
        hop_df = pd.read_csv(hop_csv_path, index_col=0)
        
        # 统一转换索引和列名为 int
        hop_df.index = pd.to_numeric(hop_df.index, errors='coerce').fillna(-1).astype(int)
        hop_df.columns = pd.to_numeric(hop_df.columns, errors='coerce').fillna(-1).astype(int)

        print(f"矩阵加载完成。开始查询（共 {query_times} 次机会）：")

        for i in range(query_times):
            print(f"\n--- 第 {i+1}/{query_times} 次查询 ---")
            try:
                user_input = input("请输入两个区域 ID (用空格分隔，或输入 'q' 退出): ").strip()
                if user_input.lower() == 'q':
                    print("已退出查询。")
                    break
                
                parts = user_input.split()
                if len(parts) != 2:
                    print("输入格式错误，请输入两个数字。")
                    continue
                
                id1, id2 = int(parts[0]), int(parts[1])
                
                if id1 not in hop_df.index or id2 not in hop_df.index:
                    print(f"错误: 区域 ID {id1} 或 {id2} 不在矩阵中。")
                    continue
                
                hops = hop_df.loc[id1, id2]
                if id1 == id2:
                    print(f"区域 {id1} 到自身跳数为 0")
                elif hops == 0:
                    print(f"区域 {id1} 与区域 {id2} 不可达 (跳数为 0)")
                else:
                    print(f"区域 {id1} 到区域 {id2} 的跳数为: {int(hops)}")
                    
            except ValueError:
                print("输入无效，请输入整数。")
            except Exception as e:
                print(f"查询过程中出错: {e}")

        print("\n查询结束。")

    except Exception as e:
        print(f"读取 HOP 矩阵时出错: {e}")

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)
    shp_file_path = os.path.join(script_dir, "..", "data", "data_raw", "taxi_zones", "taxi_zones.shp")
    zone_id_col = "LocationID"
    output_csv_path = os.path.join(script_dir, "adjacency_matrix.csv")

    # # 1. 生成邻接矩阵并保存为 CSV
    # print("\n--- 任务: 生成邻接矩阵并保存为 CSV ---")
    # matrix = generate_adjacency_from_shapefile(shp_file_path, zone_id_col)
    # if matrix is not None:
    #     print(f"\n计算成功! 矩阵维度: {matrix.shape}")
    #     matrix.to_csv(output_csv_path)
    #     print(f"\n已保存至 {output_csv_path}")

    # # 2. 从 CSV 读取邻接矩阵并打印预览
    # print("\n--- 任务: 从 CSV 读取邻接矩阵并打印预览 ---")
    # print_adjacency_matrix_from_csv(output_csv_path)

    # # 3. 连接两个指定区域
    # print("\n--- 任务: 连接两个指定区域 ---")
    # # 请将 region1_id 和 region2_id 替换为你要连接的区域ID
    # # connect_regions_in_adjacency_matrix(output_csv_path, region1_id=194, region2_id=75)
    # # connect_regions_in_adjacency_matrix(output_csv_path, region1_id=202, region2_id=140)
    # # connect_regions_in_adjacency_matrix(output_csv_path, region1_id=153, region2_id=127)
    # connect_regions_in_adjacency_matrix(output_csv_path, region1_id=103, region2_id=12)

    # 4. 从 CSV 读取邻接矩阵并打印每个区域的相邻区域
    # print("\n--- 任务: 从 CSV 读取邻接矩阵并打印每个区域的相邻区域 ---")
    # print_each_region_adjacent_regions_from_csv(output_csv_path)

    # 5. 生成 HOP 邻接矩阵
    print("\n--- 任务: 生成 HOP 邻接矩阵 ---")
    output_hop_csv_path = os.path.join(script_dir, "hop_adjacency_matrix.csv")
    generate_hop_adjacency_matrix(output_csv_path, output_hop_csv_path, max_hops=70)

    # 6. 重映射区域 ID
    print("\n--- 任务: 重映射区域 ID ---")
    output_remapped_csv_path = os.path.join(script_dir, "hop_adjacency_matrix_remapped.csv")
    output_mapping_path = os.path.join(script_dir, "region_id_mapping.pkl")
    remapped_df, mapping_dict, reverse_mapping_dict = remap_region_ids(
        output_hop_csv_path, output_remapped_csv_path, output_mapping_path
    )
    
    if remapped_df is not None:
        print("\n" + "="*50)
        print("验证结果:")
        print("="*50)
        print(f"重映射后矩阵形状: {remapped_df.shape}")
        print(f"索引范围: {remapped_df.index.min()} - {remapped_df.index.max()}")
        print(f"列范围: {remapped_df.columns.min()} - {remapped_df.columns.max()}")
        print(f"\n重映射后矩阵预览 (前5x5):")
        print(remapped_df.iloc[:5, :5])

    # 7. 查询跳数
    print("\n--- 任务: 查询区域间跳数 ---")
    # query_hops_from_csv(output_hop_csv_path, query_times=10)
    query_hops_from_csv(output_remapped_csv_path, query_times=10)


