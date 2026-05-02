"""
路径规划可视化 Web 应用
- 网格寻路 (A*/BFS/DFS)
- 真实地图路径规划 (免费 OSRM + Nominatim，不需要任何Key)
"""
from pathlib import Path
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from planner import (
    create_grid, set_obstacles, astar, bfs, dfs,
    simplify_path, ALGORITHMS
)
from map_service import (
    geocode, reverse_geocode, plan_route,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="路径规划可视化", description="交互式路径规划演示")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def render(name: str, request: Request, **context):
    return templates.TemplateResponse(request, name, context)


# ========== 预设网格地图 ==========
PRESET_MAPS = {
    "simple": {
        "name": "简单迷宫", "width": 15, "height": 10,
        "start": [1, 1], "goal": [13, 8],
        "obstacles": [
            (3, 0), (3, 1), (3, 2), (3, 3), (3, 4),
            (6, 4), (6, 5), (6, 6), (6, 7), (6, 8),
            (9, 1), (9, 2), (9, 3), (9, 4), (9, 5),
            (12, 5), (12, 6), (12, 7), (12, 8),
        ]
    },
    "complex": {
        "name": "复杂障碍", "width": 20, "height": 15,
        "start": [0, 0], "goal": [19, 14],
        "obstacles": [
            (2, 0), (2, 1), (2, 2), (5, 2), (5, 3), (5, 4), (5, 5),
            (8, 1), (8, 2), (8, 3), (10, 5), (10, 6), (10, 7),
            (3, 7), (3, 8), (3, 9), (3, 10), (7, 9), (7, 10), (7, 11),
            (12, 10), (12, 11), (12, 12), (14, 3), (14, 4), (14, 5),
            (16, 7), (16, 8), (13, 13), (14, 13), (15, 13), (16, 13), (17, 13),
            (4, 12),
        ]
    },
    "spiral": {
        "name": "螺旋迷宫", "width": 18, "height": 14,
        "start": [1, 1], "goal": [16, 12],
        "obstacles": [
            (2,1),(3,1),(4,1),(5,1),(6,1),(7,1),(8,1),(9,1),(10,1),(11,1),(12,1),(13,1),(14,1),(15,1),
            (15,2),(15,3),(15,4),(15,5),(15,6),(15,7),(15,8),(15,9),(15,10),(15,11),
            (14,11),(13,11),(12,11),(11,11),(10,11),(9,11),(8,11),(7,11),(6,11),(5,11),
            (5,10),(5,9),(5,8),(5,7),(5,6),(5,5),(5,4),(5,3),
            (6,3),(7,3),(8,3),(9,3),(10,3),(10,4),(10,5),(10,6),(10,7),(10,8),(10,9),
            (9,9),(8,9),(7,9),(7,8),(7,7),
        ]
    },
    "maze": {
        "name": "随机迷宫", "width": 16, "height": 12,
        "start": [0, 0], "goal": [15, 11],
        "obstacles": [
            (1,0),(3,0),(5,0),(7,0),(9,0),(11,0),(13,0),(2,1),(6,1),(10,1),(14,1),
            (0,2),(4,2),(8,2),(12,2),(2,3),(6,3),(10,3),(14,3),
            (1,4),(5,4),(9,4),(13,4),(2,5),(4,5),(6,5),(8,5),(10,5),(12,5),(14,5),
            (1,6),(5,6),(9,6),(13,6),(0,7),(4,7),(8,7),(12,7),
            (2,8),(6,8),(10,8),(14,8),(1,9),(5,9),(9,9),(13,9),
            (2,10),(4,10),(6,10),(8,10),(10,10),(12,10),(14,10),(3,11),(7,11),(11,11),
        ]
    },
}


# ========== 页面路由 ==========

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return render("index.html", request=request,
                  algorithms=ALGORITHMS,
                  presets=PRESET_MAPS)


# ========== 网格相关 API ==========

@app.get("/api/presets")
async def api_presets():
    return {"presets": {k: {"name": v["name"], "width": v["width"], "height": v["height"]}
                        for k, v in PRESET_MAPS.items()}}


@app.get("/api/preset/{name}")
async def api_preset(name: str):
    if name not in PRESET_MAPS:
        return JSONResponse({"error": "预设地图不存在"}, status_code=404)
    return PRESET_MAPS[name]


@app.post("/api/plan")
@app.get("/api/plan")
async def api_plan(
    algorithm: str = Query("astar"),
    width: int = Query(15, ge=3, le=50),
    height: int = Query(10, ge=3, le=50),
    start_x: int = Query(0),
    start_y: int = Query(0),
    goal_x: int = Query(...),
    goal_y: int = Query(...),
    obstacles: str = Query(""),
    simplify: bool = Query(True),
):
    """网格路径规划"""
    if algorithm not in ALGORITHMS:
        return JSONResponse({"error": f"未知算法，可选: {list(ALGORITHMS.keys())}"}, status_code=400)

    grid = create_grid(width, height)
    obs_list = []
    if obstacles:
        for part in obstacles.split(";"):
            part = part.strip()
            if not part: continue
            try:
                x, y = map(int, part.split(","))
                obs_list.append((x, y))
            except ValueError:
                return JSONResponse({"error": f"障碍物格式错误: {part}"}, status_code=400)
    set_obstacles(grid, obs_list)

    start = (start_x, start_y)
    goal = (goal_x, goal_y)
    algo_fn = ALGORITHMS[algorithm]["fn"]
    path = algo_fn(grid, start, goal)

    if path is None:
        return {"success": False, "error": "无法找到路径！起点或终点被阻挡，或没有通路。",
                "algorithm": algorithm, "start": list(start), "goal": list(goal),
                "obstacles": obs_list, "width": width, "height": height}

    raw_len = len(path)
    if simplify:
        path = simplify_path(path)

    return {
        "success": True, "algorithm": algorithm,
        "start": list(start), "goal": list(goal),
        "path": path, "path_length": len(path), "raw_length": raw_len,
        "width": width, "height": height, "obstacles": obs_list,
    }


@app.get("/api/algorithms")
async def api_algorithms():
    return {"algorithms": {k: {"name": v["name"], "desc": v["desc"]}
                           for k, v in ALGORITHMS.items()}}


# ========== 真实地图 API ==========

@app.get("/api/map/geocode")
async def api_geocode(address: str = Query(..., description="地址"),
                      city: str = Query("", description="所在城市")):
    """地理编码：地址 → 经纬度"""
    result = await geocode(address, city)
    if result:
        return {"success": True, "data": result}
    return {"success": False, "error": "未找到该地址"}


@app.get("/api/map/reverse")
async def api_reverse(lng: float = Query(...), lat: float = Query(...)):
    """逆地理编码：经纬度 → 地址"""
    result = await reverse_geocode(lng, lat)
    if result:
        return {"success": True, "data": result}
    return {"success": False, "error": "逆地理编码失败"}


@app.get("/api/map/plan")
async def api_map_plan(
    origin: str = Query(..., description="起点坐标 lng,lat"),
    destination: str = Query(..., description="终点坐标 lng,lat"),
    mode: str = Query("driving", description="driving/walking/cycling"),
    strategy: int = Query(0),
    city: str = Query(""),
):
    """统一路径规划接口 - 使用免费 OSRM API"""
    # OSRM 不支持 transit，映射为 driving
    osrm_mode = mode
    if mode == "transit":
        osrm_mode = "driving"

    result = await plan_route(origin, destination, osrm_mode)

    if result:
        return {
            "success": True,
            "mode": mode,
            "data": result,
            "is_fallback": result.get("fallback", False),
        }
    return {"success": False, "error": "路径规划失败"}


@app.get("/api/map/driving")
async def api_driving(
    origin: str = Query(..., description="起点坐标 lng,lat"),
    destination: str = Query(..., description="终点坐标 lng,lat"),
    strategy: int = Query(0),
):
    """驾车路径规划"""
    result = await plan_route(origin, destination, "driving")
    if result:
        return {"success": True, "data": result}
    return {"success": False, "error": "驾车路径规划失败"}


@app.get("/api/map/walking")
async def api_walking(
    origin: str = Query(..., description="起点坐标 lng,lat"),
    destination: str = Query(..., description="终点坐标 lng,lat"),
):
    """步行路径规划"""
    result = await plan_route(origin, destination, "walking")
    if result:
        return {"success": True, "data": result}
    return {"success": False, "error": "步行路径规划失败"}


@app.get("/api/map/status")
async def api_map_status():
    """检查 API 状态"""
    return {
        "configured": True,
        "message": "✅ 免费地图服务已就绪（OSRM + Nominatim，无需Key）",
        "services": {
            "geocoding": "Nominatim (OpenStreetMap)",
            "routing": "OSRM (Open Source Routing Machine)",
            "basemap": "OpenStreetMap",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
