"""
路径规划引擎 - 支持多种算法
"""
import math
from typing import List, Tuple, Dict, Optional

# ========== 网格地图 ==========

Grid = List[List[int]]  # 0=空地, 1=障碍物

def create_grid(width: int, height: int) -> Grid:
    """创建空白网格"""
    return [[0] * width for _ in range(height)]


def set_obstacle(grid: Grid, x: int, y: int) -> None:
    """设置障碍物"""
    if 0 <= x < len(grid[0]) and 0 <= y < len(grid):
        grid[y][x] = 1


def set_obstacles(grid: Grid, obstacles: List[Tuple[int, int]]) -> None:
    """批量设置障碍物"""
    for x, y in obstacles:
        set_obstacle(grid, x, y)


# ========== 路径算法 ==========

def neighbors(x: int, y: int, grid: Grid, allow_diagonal: bool = False) -> List[Tuple[int, int]]:
    """获取相邻可通行格子"""
    h, w = len(grid), len(grid[0])
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    if allow_diagonal:
        dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    result = []
    for dx, dy in dirs:
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == 0:
            result.append((nx, ny))
    return result


def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """曼哈顿距离"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(grid: Grid, start: Tuple[int, int], goal: Tuple[int, int],
          allow_diagonal: bool = False) -> Optional[List[Tuple[int, int]]]:
    """
    A* 寻路算法
    返回从 start 到 goal 的路径坐标列表，找不到返回 None
    """
    from heapq import heappush, heappop

    h, w = len(grid), len(grid[0])
    sx, sy = start
    gx, gy = goal

    # 边界检查
    if not (0 <= sx < w and 0 <= sy < h and 0 <= gx < w and 0 <= gy < h):
        return None
    if grid[sy][sx] == 1 or grid[gy][gx] == 1:
        return None

    open_set = [(0, sx, sy)]
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], float] = {(sx, sy): 0}
    f_score: Dict[Tuple[int, int], float] = {(sx, sy): heuristic(start, goal)}

    while open_set:
        _, cx, cy = heappop(open_set)

        if (cx, cy) == (gx, gy):
            # 重建路径
            path = []
            pos = (gx, gy)
            while pos in came_from:
                path.append(pos)
                pos = came_from[pos]
            path.append(start)
            path.reverse()
            return path

        for nx, ny in neighbors(cx, cy, grid, allow_diagonal):
            move_cost = math.sqrt(2) if (nx != cx and ny != cy) else 1.0
            tentative = g_score[(cx, cy)] + move_cost

            if tentative < g_score.get((nx, ny), float('inf')):
                came_from[(nx, ny)] = (cx, cy)
                g_score[(nx, ny)] = tentative
                f = tentative + heuristic((nx, ny), goal)
                f_score[(nx, ny)] = f
                heappush(open_set, (f, nx, ny))

    return None  # 无路径


def bfs(grid: Grid, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """广度优先搜索"""
    from collections import deque

    h, w = len(grid), len(grid[0])
    sx, sy = start
    gx, gy = goal

    if not (0 <= sx < w and 0 <= sy < h and 0 <= gx < w and 0 <= gy < h):
        return None
    if grid[sy][sx] == 1 or grid[gy][gx] == 1:
        return None

    queue = deque([(sx, sy)])
    came_from = {(sx, sy): None}

    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == (gx, gy):
            path = []
            pos = (gx, gy)
            while pos:
                path.append(pos)
                pos = came_from.get(pos)
            path.reverse()
            return path

        for nx, ny in neighbors(cx, cy, grid):
            if (nx, ny) not in came_from:
                came_from[(nx, ny)] = (cx, cy)
                queue.append((nx, ny))

    return None


def dfs(grid: Grid, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """深度优先搜索"""
    h, w = len(grid), len(grid[0])
    sx, sy = start
    gx, gy = goal

    if not (0 <= sx < w and 0 <= sy < h and 0 <= gx < w and 0 <= gy < h):
        return None
    if grid[sy][sx] == 1 or grid[gy][gx] == 1:
        return None

    stack = [(sx, sy)]
    came_from = {(sx, sy): None}

    while stack:
        cx, cy = stack.pop()
        if (cx, cy) == (gx, gy):
            path = []
            pos = (gx, gy)
            while pos:
                path.append(pos)
                pos = came_from.get(pos)
            path.reverse()
            return path

        for nx, ny in neighbors(cx, cy, grid):
            if (nx, ny) not in came_from:
                came_from[(nx, ny)] = (cx, cy)
                stack.append((nx, ny))

    return None


# ========== 路径平滑 ==========

def simplify_path(path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """简化路径：去掉直线上的中间点"""
    if len(path) <= 2:
        return path

    simplified = [path[0]]
    for i in range(1, len(path) - 1):
        prev = path[i - 1]
        curr = path[i]
        nxt = path[i + 1]
        # 如果三点共线则跳过中间点
        if (curr[0] - prev[0]) == (nxt[0] - curr[0]) and \
           (curr[1] - prev[1]) == (nxt[1] - curr[1]):
            continue
        simplified.append(curr)
    simplified.append(path[-1])
    return simplified


# ========== 算法注册表 ==========

ALGORITHMS = {
    "astar": {"name": "A* 算法", "fn": astar, "desc": "启发式搜索，速度最快、路径最优"},
    "bfs":   {"name": "广度优先 BFS", "fn": bfs, "desc": "保证最短路径，适合小地图"},
    "dfs":   {"name": "深度优先 DFS", "fn": dfs, "desc": "内存占用少，但不保证最短"},
}
