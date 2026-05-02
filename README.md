# 🚗 自驾路线规划

交互式路径规划可视化应用 — 网格寻路 + 真实地图路线规划。

## ✨ 特性

### 🧩 网格寻路（4种迷宫预设）
- **A\* 算法** — 启发式搜索，速度最快、路径最优
- **BFS** — 广度优先，保证最短路径
- **DFS** — 深度优先，内存占用少
- 4种预设地图：简单迷宫、复杂障碍、螺旋迷宫、随机迷宫
- 路径平滑（去除直线中间点）
- 障碍物手动编辑

### 🗺️ 真实地图路径规划
- **地理编码** — 输入地址名查经纬度（Nominatim 免费服务）
- **路径规划** — 驾车/步行/骑行路线查询（OSRM 免费服务）
- **多坐标降级** — 内置100+中国城市坐标，API失败自动保底
- OpenStreetMap 底图渲染

### 🎯 零API Key
所有地图服务完全免费，无需注册、无需Key。

## 🖼️ 效果预览

![路径规划首页](./static/screenshot.png)

## 🚀 快速启动

```bash
# 1. 安装依赖
pip install fastapi uvicorn jinja2

# 2. 启动服务
python main.py
# 或 uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 3. 打开浏览器
# http://localhost:8001/
```

## 🏗️ 项目结构

```
route-planner/
├── main.py              # FastAPI 主服务（路由+API）
├── planner.py           # 寻路算法引擎（A*/BFS/DFS）
├── map_service.py       # 真实地图服务（Nominatim+OSRM）
├── requirements.txt     # 依赖清单
├── templates/
│   ├── index.html       # 主页（网格寻路+地图切换）
│   ├── home.html        # 首页
│   └── route.html       # 路线结果页
└── static/
    └── style.css        # 样式
```

## 🗺️ 操作指南

| 模式 | 操作 | 说明 |
|------|------|------|
| 🧩 网格寻路 | 选择预设地图 | 4种迷宫一键加载 |
| | 选择算法 | A*/BFS/DFS对比 |
| | 点击格子 | 切换障碍物 |
| 🗺️ 真实地图 | 输入起点/终点地址 | 自动地理编码 |
| | 选择出行方式 | 驾车/步行/骑行 |
| | 查看路线 | 路径+距离+时间 |

## 🛠️ 技术栈

- **后端**: FastAPI + Uvicorn
- **前端**: Leaflet.js + Vanilla JS
- **地理编码**: Nominatim (OpenStreetMap)
- **路径规划**: OSRM (Open Source Routing Machine)
- **底图**: OpenStreetMap
- **寻路算法**: A\*, BFS, DFS

## 🔌 API 概览

| 端点 | 说明 |
|------|------|
| `GET /api/presets` | 预设地图列表 |
| `GET /api/plan` | 网格路径规划 |
| `GET /api/map/geocode?address=` | 地理编码 |
| `GET /api/map/reverse?lng=&lat=` | 逆地理编码 |
| `GET /api/map/plan` | 真实路径规划 |
| `GET /api/map/status` | 地图服务状态 |

## 🐍 依赖

```bash
pip install fastapi uvicorn jinja2 httpx
```

无需数据库、无需API Key、无需注册。

## 📄 许可证

MIT
