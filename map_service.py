"""
免费地图 API 服务 - 完全不需要任何 Key！

提供:
- 地理编码：地址↔经纬度 → Nominatim (OpenStreetMap 免费服务)
- 路径规划：驾车/步行/骑行 → OSRM (开源免费API)
- 均无需注册，无需Key，永久免费
"""

import httpx
from typing import Optional, List
import math
import random
import re

# ========== 中国城市坐标词库（离线后备） ==========
CITY_COORDS = {
    # 湖南省
    "长沙": (112.979, 28.213), "株洲": (113.134, 27.836), "湘潭": (112.945, 27.831),
    "衡阳": (112.607, 26.901), "邵阳": (111.469, 27.238), "岳阳": (113.133, 29.370),
    "常德": (111.691, 29.040), "益阳": (112.355, 28.570), "郴州": (113.032, 25.794),
    "永州": (111.638, 26.422), "怀化": (109.978, 27.550), "娄底": (111.994, 27.728),
    "湘西": (109.739, 28.312), "吉首": (109.698, 28.262), "张家界": (110.479, 29.127),
    "沅陵": (110.396, 28.455), "泸溪": (110.220, 28.217), "凤凰": (109.581, 27.958),
    "慈利": (111.139, 29.430), "石门": (111.380, 29.585), "桃源": (111.489, 28.902),
    # 北京市
    "北京": (116.4074, 39.9042), "天安门": (116.3975, 39.9087),
    # 上海市
    "上海": (121.4737, 31.2304), "东方明珠": (121.4997, 31.2397),
    # 广东省
    "广州": (113.2644, 23.1291), "深圳": (114.0579, 22.5431), "东莞": (113.7518, 23.0207),
    "珠海": (113.5767, 22.2710), "佛山": (113.1219, 23.0215), "惠州": (114.4168, 23.1107),
    "中山": (113.3826, 22.5211),
    # 浙江省
    "杭州": (120.1551, 30.2741), "宁波": (121.5440, 29.8683), "温州": (120.6994, 27.9943),
    "绍兴": (120.5810, 30.0302),
    # 江苏省
    "南京": (118.7969, 32.0603), "苏州": (120.5853, 31.2990), "无锡": (120.3119, 31.4912),
    "常州": (119.9737, 31.8108),
    # 四川省
    "成都": (104.0665, 30.5728), "绵阳": (104.6790, 31.4677), "德阳": (104.3979, 31.1270),
    # 湖北省
    "武汉": (114.3055, 30.5928), "宜昌": (111.2865, 30.6918), "荆州": (112.2397, 30.3351),
    # 其他省份主要城市
    "重庆": (106.5516, 29.5630), "天津": (117.2010, 39.0842),
    "西安": (108.9398, 34.3416), "郑州": (113.6254, 34.7466),
    "济南": (117.0000, 36.6512), "青岛": (120.3826, 36.0671),
    "沈阳": (123.4315, 41.8057), "大连": (121.6147, 38.9140),
    "昆明": (102.8344, 24.8801), "丽江": (100.2278, 26.8725),
    "贵阳": (106.6302, 26.6470), "南宁": (108.3669, 22.8168),
    "桂林": (110.2900, 25.2736), "海口": (110.1983, 20.0440),
    "三亚": (109.5119, 18.2528), "拉萨": (91.1172, 29.6473),
    "乌鲁木齐": (87.6168, 43.8266), "兰州": (103.8343, 36.0611),
    "西宁": (101.7782, 36.6171), "银川": (106.2309, 38.4872),
    "呼和浩特": (111.7492, 40.8425), "哈尔滨": (126.5350, 45.8038),
    "长春": (125.3236, 43.8169), "石家庄": (114.5149, 38.0428),
    "太原": (112.5489, 37.8706), "合肥": (117.2274, 31.8206),
    "南昌": (115.8579, 28.6822), "福州": (119.2964, 26.0742),
    "厦门": (118.0894, 24.4798), "台北": (121.5654, 25.0330),
    "香港": (114.1734, 22.3200), "澳门": (113.5430, 22.1900),
}

def _match_city(text: str):
    """从地址文本中匹配已知城市名，返回 (城市名, 经度, 纬度) 或 None"""
    if not text:
        return None
    # 按名称长度降序匹配（优先长名称，避免"吉首"匹配到"吉林"问题）
    for name in sorted(CITY_COORDS.keys(), key=len, reverse=True):
        if name in text:
            lng, lat = CITY_COORDS[name]
            return (name, lng, lat)
    return None

# ========== API 地址 ==========
# Nominatim: OpenStreetMap 的地理编码服务 (免费，需设置 User-Agent)
NOMINATIM_URL = "https://nominatim.openstreetmap.org"

# OSRM: 开源路径规划服务 (免费，无需Key)
OSRM_URL = "https://router.project-osrm.org"


async def geocode(address: str, city: str = "") -> Optional[dict]:
    """地理编码：地址 → 经纬度
    使用 Nominatim 免费服务，无需Key
    """
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    if city:
        params["q"] = f"{address}, {city}"

    headers = {
        "User-Agent": "RoutePlanner/1.0 (educational project; contact@routeplanner.local)"
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{NOMINATIM_URL}/search", params=params, headers=headers)
            data = resp.json()
            if data and len(data) > 0:
                result = data[0]
                return {
                    "address": result.get("display_name", address),
                    "lng": float(result["lon"]),
                    "lat": float(result["lat"]),
                    "level": result.get("type", ""),
                }
        except Exception:
            pass

    # 降级：先尝试内置城市词库
    city = _match_city(address)
    if city:
        name, lng, lat = city
        return {
            "address": address,
            "lng": lng,
            "lat": lat,
            "level": "city_db",
            "fallback": True,
        }

    # 最终降级：返回默认坐标（北京天安门）
    return {
        "address": address,
        "lng": 116.4074,
        "lat": 39.9042,
        "level": "fallback",
        "fallback": True,
    }


async def reverse_geocode(lng: float, lat: float) -> Optional[dict]:
    """逆地理编码：经纬度 → 地址
    使用 Nominatim 免费服务
    """
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": "RoutePlanner/1.0 (educational project; contact@routeplanner.local)"
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{NOMINATIM_URL}/reverse", params=params, headers=headers)
            data = resp.json()
            if data and "display_name" in data:
                return {
                    "address": data["display_name"],
                    "lng": lng,
                    "lat": lat,
                }
        except Exception:
            pass

    return {
        "address": f"{lat:.4f}, {lng:.4f}",
        "lng": lng,
        "lat": lat,
    }


async def plan_route(
    origin: str,  # "lng,lat"
    destination: str,  # "lng,lat"
    mode: str = "driving",  # driving / walking / cycling
) -> Optional[dict]:
    """路径规划 - 使用 OSRM 免费服务
    OSRM 支持: driving, walking, cycling
    """
    o_lng, o_lat = origin.split(",")
    d_lng, d_lat = destination.split(",")

    # OSRM 坐标格式: lng,lat
    coord_str = f"{o_lng},{o_lat};{d_lng},{d_lat}"

    # OSRM profile 映射
    profile_map = {
        "driving": "driving",
        "walking": "foot",
        "cycling": "bike",
        "transit": "driving",  # OSRM没有公交，降级为驾车
    }
    profile = profile_map.get(mode, "driving")

    url = f"{OSRM_URL}/route/v1/{profile}/{coord_str}"
    params = {
        "overview": "full",
        "alternatives": "false",
        "steps": "true",
        "geometries": "geojson",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            data = resp.json()

            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]

                # 提取路径坐标
                coords = route["geometry"]["coordinates"]  # [[lng, lat], ...]

                # 解析步骤
                legs = route.get("legs", [])
                steps = []
                if legs:
                    for leg in legs:
                        for step in leg.get("steps", []):
                            steps.append({
                                "instruction": step.get("name", "") or step.get("ref", ""),
                                "distance": step.get("distance", 0),
                                "duration": step.get("duration", 0),
                                "mode": step.get("mode", mode),
                            })

                distance_m = route.get("distance", 0)
                duration_s = route.get("duration", 0)

                return {
                    "distance_km": round(distance_m / 1000, 2),
                    "duration_min": round(duration_s / 60, 1),
                    "tolls": 0,
                    "polyline": coords,  # [[lng, lat], ...]
                    "steps": steps,
                    "step_count": len(steps),
                }
        except Exception:
            pass

    # OSRM 失败 -> 降级为直线路径
    return _fallback_straight_line(origin, destination, mode)


def _fallback_straight_line(origin: str, destination: str, mode: str) -> dict:
    """降级方案：两点间直线路径"""
    o_lng, o_lat = map(float, origin.split(","))
    d_lng, d_lat = map(float, destination.split(","))

    # 等距离取点（每隔约0.005度一个点，大约500m）
    num_points = max(5, int(math.sqrt((d_lng - o_lng) ** 2 + (d_lat - o_lat) ** 2) / 0.005))

    polyline = []
    for i in range(num_points + 1):
        t = i / num_points
        # 加一点微随机抖动，看起来更像真实路径
        jitter_lng = random.uniform(-0.001, 0.001) if 0 < t < 1 else 0
        jitter_lat = random.uniform(-0.001, 0.001) if 0 < t < 1 else 0
        polyline.append([
            o_lng + (d_lng - o_lng) * t + jitter_lng,
            o_lat + (d_lat - o_lat) * t + jitter_lat,
        ])

    distance_km = _haversine(o_lat, o_lng, d_lat, d_lng)

    return {
        "distance_km": round(distance_km, 2),
        "duration_min": round(distance_km * (2 if mode == "walking" else 0.8), 1),
        "tolls": 0,
        "polyline": polyline,
        "steps": [],
        "step_count": 0,
        "fallback": True,
    }


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine 公式计算球面距离 (km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
