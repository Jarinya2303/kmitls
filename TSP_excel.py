import numpy as np
from mip import Model, xsum, BINARY, minimize, OptimizationStatus
from math import radians, sin, cos, sqrt, atan2
from itertools import product
import pandas as pd

# ฟังก์ชันคำนวณระยะทาง Euclidean
def euclidean_distance(point1, point2):
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

# ฟังก์ชันคำนวณระยะทาง Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the Earth in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# ฟังก์ชันคำนวณระยะทางทั้งหมด
def calculate_distance_matrix(coordinates, use_haversine=True):
    n = len(coordinates)
    dist_matrix = np.zeros((n, n))  
    for i in range(n):
        for j in range(i + 1, n):
            lat1, lon1 = coordinates[i]
            lat2, lon2 = coordinates[j]
            if use_haversine:
                dist = haversine(lat1, lon1, lat2, lon2)
            else:
                dist = euclidean_distance((lat1, lon1), (lat2, lon2))
            dist_matrix[i][j] = dist_matrix[j][i] = dist
    return dist_matrix

# ฟังก์ชันทำ K-means clustering
def assign_clusters(data, centroids):
    clusters = {i: [] for i in range(len(centroids))}
    for item in data:
        point = item["coords"]
        distances = [euclidean_distance(point, centroid) for centroid in centroids]
        closest_centroid = np.argmin(distances)
        clusters[closest_centroid].append(item)
    return clusters

def update_centroids(clusters):
    new_centroids = []
    for points in clusters.values():
        if points:
            coords = [item["coords"] for item in points]
            new_centroid = np.mean(coords, axis=0)
            new_centroids.append(tuple(new_centroid))
    return new_centroids

def kmeans(data, centroids, max_iters=100, tol=1e-4):
    for _ in range(max_iters):
        clusters = assign_clusters(data, centroids)
        new_centroids = update_centroids(clusters)
        shifts = [euclidean_distance(old, new) for old, new in zip(centroids, new_centroids)]
        if max(shifts) < tol:
            break
        centroids = new_centroids
    return clusters, centroids

# ฟังก์ชัน TSP ที่ใช้ MIP
def solve_tsp(places, coordinates, start_point):
    coordinates = [start_point] + coordinates
    places = ['Start'] + places
    dists = calculate_distance_matrix(coordinates, use_haversine=True)
    n, V = len(dists), set(range(len(dists)))
    model = Model()
    x = [[model.add_var(var_type=BINARY) for j in V] for i in V]
    y = [model.add_var() for i in V]
    model.objective = minimize(xsum(dists[i][j] * x[i][j] for i in V for j in V))
    for i in V:
        model += xsum(x[i][j] for j in V - {i}) == 1
        model += xsum(x[j][i] for j in V - {i}) == 1
    for (i, j) in product(V - {0}, V - {0}):
        if i != j:
            model += y[i] - (n + 1) * x[i][j] >= y[j] - n
    model.optimize()
    if model.status == OptimizationStatus.OPTIMAL:
        route = [0]
        nc = 0
        while True:
            nc = [i for i in V if x[nc][i].x >= 0.99][0]
            route.append(nc)
            if nc == 0:
                break
        route_places = [places[i] for i in route]
        total_distance = sum(dists[route[i]][route[i+1]] for i in range(len(route)-1))
        return route_places, total_distance  # คืนค่าเส้นทางและระยะทาง
    else:
        print("No feasible solution found.")
        return [], 0

# ฟังก์ชันที่คำนวณ K-means และ TSP
def kmeans_and_tsp(data):
    k = 2  # จำนวนกลุ่มที่ต้องการ
    coordinates = [item["coords"] for item in data]
    start_point = [13.74164416, 100.0839788]  # ใช้พิกัดของจุดเริ่มต้นจากจุดแรกในข้อมูล
    initial_centroids = [coordinates[i] for i in np.random.choice(len(coordinates), k, replace=False)]
    
    # คำนวณ K-means clustering
    clusters, final_centroids = kmeans(data, initial_centroids)
    
    # สร้าง dictionary สำหรับเก็บเส้นทางของแต่ละกลุ่ม
    routes = {}

    # คำนวณ TSP สำหรับแต่ละกลุ่ม
    for cluster_id, group in clusters.items():
        cluster_places = [item['first_name'] for item in group]  # ใช้ first_name เป็น place
        cluster_coordinates = [item['coords'] for item in group]
        print(f"Cluster {cluster_id + 1}: {cluster_places}")
        
        # คำนวณ TSP สำหรับแต่ละกลุ่ม
        route_places, total_distance = solve_tsp(cluster_places, cluster_coordinates, start_point)
        routes[cluster_id + 1] = {
            "route": route_places,
            "total_distance": total_distance
        }  # เก็บเส้นทางและระยะทางรวมของแต่ละกลุ่ม

    return clusters, routes

# ฟังก์ชัน CalculateRoutesExcel ที่รับข้อมูลจาก Excel และคำนวณเส้นทาง
def CalculateRoutesExcel(data):
    # เพิ่มคีย์ 'coords' ให้กับแต่ละ item โดยใช้ latitude และ longitude
    for item in data:
        item['coords'] = (item['latitude'], item['longitude'])
    
    # คำนวณ K-means clustering และ TSP
    clusters, routes = kmeans_and_tsp(data)

    # สร้าง dictionary สำหรับเก็บเส้นทางและระยะทางของแต่ละกลุ่ม
    result = {}

    # เก็บผลลัพธ์จากแต่ละกลุ่ม
    for cluster_id, route_info in routes.items():
        result[cluster_id] = {
            "route": route_info["route"],  # เส้นทางของกลุ่ม
            "total_distance": route_info["total_distance"]  # ระยะทางรวมของกลุ่ม
        }
    
    return result

