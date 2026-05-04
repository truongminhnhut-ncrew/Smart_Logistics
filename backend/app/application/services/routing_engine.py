"""
routing_engine.py — Graph-based A* routing engine.

Theo TONGQUAN.md mục 16: Hệ thống tìm đường tối ưu dựa trên đồ thị.

KIẾN TRÚC:
  - Graph representation: adjacency list with weighted edges
  - Node: giao lộ (intersection) = { lat, lon, id }
  - Edge: đoạn đường = { distance_km, traffic_factor, estimated_time_min }
  - A* heuristic: Haversine distance (admissible)

STUB NOTE:
  Đây là cấu trúc khung. Trong production, graph data sẽ được load từ
  OpenStreetMap hoặc file GeoJSON. Hiện tại sử dụng simplified grid.
"""

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Node:
    """Graph node representing an intersection."""
    node_id: str
    lat: float
    lon: float

    def __hash__(self):
        return hash(self.node_id)


@dataclass
class Edge:
    """Weighted edge between two nodes."""
    from_node: str
    to_node: str
    distance_km: float
    traffic_factor: float = 1.0  # 1.0 = normal, 2.0 = heavy traffic
    estimated_time_min: float = 0.0

    @property
    def weight(self) -> float:
        """Effective weight = distance × traffic factor."""
        return self.distance_km * self.traffic_factor


@dataclass(order=True)
class PriorityEntry:
    """Entry for the A* priority queue."""
    priority: float
    node_id: str = field(compare=False)


class RoutingGraph:
    """
    Graph-based routing engine using A* algorithm.

    Usage:
        graph = RoutingGraph()
        graph.add_node("N1", 10.80, 106.71)
        graph.add_node("N2", 10.81, 106.72)
        graph.add_edge("N1", "N2", distance_km=1.5)
        path = graph.find_shortest_path("N1", "N2")
    """

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.adjacency: Dict[str, List[Edge]] = {}

    def add_node(self, node_id: str, lat: float, lon: float) -> None:
        """Add an intersection node."""
        self.nodes[node_id] = Node(node_id=node_id, lat=lat, lon=lon)
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        distance_km: float,
        traffic_factor: float = 1.0,
        bidirectional: bool = True,
    ) -> None:
        """Add a road segment edge."""
        speed_kmh = 30.0 / traffic_factor
        time_min = (distance_km / speed_kmh) * 60 if speed_kmh > 0 else float("inf")

        edge = Edge(
            from_node=from_id,
            to_node=to_id,
            distance_km=distance_km,
            traffic_factor=traffic_factor,
            estimated_time_min=time_min,
        )
        self.adjacency.setdefault(from_id, []).append(edge)

        if bidirectional:
            reverse = Edge(
                from_node=to_id,
                to_node=from_id,
                distance_km=distance_km,
                traffic_factor=traffic_factor,
                estimated_time_min=time_min,
            )
            self.adjacency.setdefault(to_id, []).append(reverse)

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in km — admissible A* heuristic."""
        radius_km = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return radius_km * 2 * math.asin(math.sqrt(a))

    def _heuristic(self, node_id: str, goal_id: str) -> float:
        """A* heuristic: straight-line distance to goal."""
        n1 = self.nodes[node_id]
        n2 = self.nodes[goal_id]
        return self.haversine(n1.lat, n1.lon, n2.lat, n2.lon)

    def find_shortest_path(self, start_id: str, goal_id: str) -> Optional[dict]:
        """
        A* algorithm to find shortest path.

        Returns:
            {
                "path": ["N1", "N2", "N3"],
                "total_distance_km": 3.5,
                "total_time_min": 12.0,
                "waypoints": [{"lat": ..., "lon": ...}, ...]
            }
        """
        if start_id not in self.nodes or goal_id not in self.nodes:
            return None

        open_set: List[PriorityEntry] = []
        heapq.heappush(open_set, PriorityEntry(0, start_id))

        came_from: Dict[str, str] = {}
        g_score: Dict[str, float] = {start_id: 0}
        time_score: Dict[str, float] = {start_id: 0}

        while open_set:
            current = heapq.heappop(open_set).node_id

            if current == goal_id:
                path = []
                node = goal_id
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.append(start_id)
                path.reverse()

                waypoints = [{"lat": self.nodes[nid].lat, "lon": self.nodes[nid].lon} for nid in path]

                return {
                    "path": path,
                    "total_distance_km": round(g_score[goal_id], 2),
                    "total_time_min": round(time_score[goal_id], 1),
                    "waypoints": waypoints,
                }

            for edge in self.adjacency.get(current, []):
                tentative_g = g_score[current] + edge.weight
                tentative_time = time_score[current] + edge.estimated_time_min

                if tentative_g < g_score.get(edge.to_node, float("inf")):
                    came_from[edge.to_node] = current
                    g_score[edge.to_node] = tentative_g
                    time_score[edge.to_node] = tentative_time
                    f_score = tentative_g + self._heuristic(edge.to_node, goal_id)
                    heapq.heappush(open_set, PriorityEntry(f_score, edge.to_node))

        return None

    def update_traffic(self, from_id: str, to_id: str, factor: float) -> None:
        """Update traffic factor on an edge (real-time)."""
        for edge in self.adjacency.get(from_id, []):
            if edge.to_node == to_id:
                edge.traffic_factor = factor
                speed_kmh = 30.0 / factor
                edge.estimated_time_min = (edge.distance_km / speed_kmh) * 60

    def find_nearest_node(self, lat: float, lon: float) -> str:
        """Return nearest graph node to a GPS coordinate."""
        if not self.nodes:
            raise ValueError("Routing graph has no nodes")
        return min(
            self.nodes.keys(),
            key=lambda node_id: self.haversine(lat, lon, self.nodes[node_id].lat, self.nodes[node_id].lon),
        )

    def get_node_coordinate(self, node_id: str) -> Tuple[float, float]:
        """Return node coordinate as (lat, lon)."""
        node = self.nodes[node_id]
        return node.lat, node.lon

    def find_route_waypoints(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
    ) -> List[Tuple[float, float]]:
        """
        Snap start/end GPS points to graph nodes and route with A*.

        Theo TONGQUAN.md:
        - shipper và destination được snap vào node gần nhất
        - A* tìm path ngắn nhất trên graph
        - simulation đi node-by-node / edge-by-edge
        """
        start_id = self.find_nearest_node(from_lat, from_lon)
        goal_id = self.find_nearest_node(to_lat, to_lon)
        result = self.find_shortest_path(start_id, goal_id)
        if not result:
            return []
        return [(item["lat"], item["lon"]) for item in result["waypoints"]]


def build_hcmc_sample_graph() -> RoutingGraph:
    """
    Build a 200-500 node demo road graph around 02 Võ Oanh, Bình Thạnh.

    In production, this graph should be replaced by OSRM/OSM extracted nodes.
    """
    graph = RoutingGraph()

    center_lat = 10.8051
    center_lon = 106.7144
    radius_km = 5.0
    grid_size = 21  # 21 x 21 = 441 cells, actual nodes are those inside 5km circle

    lat_step = (radius_km * 2 / (grid_size - 1)) / 111.32
    lon_step = (radius_km * 2 / (grid_size - 1)) / (111.32 * math.cos(math.radians(center_lat)))

    node_ids: List[List[Optional[str]]] = []
    for row in range(grid_size):
        row_ids: List[Optional[str]] = []
        for col in range(grid_size):
            lat = center_lat + (row - grid_size // 2) * lat_step
            lon = center_lon + (col - grid_size // 2) * lon_step
            if RoutingGraph.haversine(center_lat, center_lon, lat, lon) <= radius_km:
                node_id = "WH" if row == grid_size // 2 and col == grid_size // 2 else f"N{row:02d}_{col:02d}"
                graph.add_node(node_id, lat, lon)
                row_ids.append(node_id)
            else:
                row_ids.append(None)
        node_ids.append(row_ids)

    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for row in range(grid_size):
        for col in range(grid_size):
            from_id = node_ids[row][col]
            if not from_id:
                continue
            from_node = graph.nodes[from_id]
            for drow, dcol in directions:
                nr, nc = row + drow, col + dcol
                if not (0 <= nr < grid_size and 0 <= nc < grid_size):
                    continue
                to_id = node_ids[nr][nc]
                if not to_id:
                    continue
                to_node = graph.nodes[to_id]
                distance_km = graph.haversine(from_node.lat, from_node.lon, to_node.lat, to_node.lon)
                traffic_factor = 1.25 if (row + col + nr + nc) % 11 == 0 else 1.0
                graph.add_edge(from_id, to_id, distance_km, traffic_factor=traffic_factor)

    return graph


# Singleton instance
routing_graph = build_hcmc_sample_graph()