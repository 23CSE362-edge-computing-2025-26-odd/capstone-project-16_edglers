"""
Precision Agriculture Simulation with Drones, Soil Sensors, MEC Server and Cloud
Using YAFS (Yet Another Fog Simulator)

@author: Based on YAFS examples, adapted for precision agriculture
"""
import os
import time
import json
import random
import logging.config
import math
from collections import defaultdict

import pandas as pd
import numpy as np
import networkx as nx
from pathlib import Path

from yafs.core import Sim
from yafs.application import create_applications_from_json
from yafs.topology import Topology
from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import deterministic_distribution, deterministicDistributionStartPoint


class DroneTaskScheduler:
    """
    Implements efficient task scheduling for drones using a greedy algorithm
    with considerations for:
    - Distance to sensors
    - Battery levels (simulated)
    - Current drone workload
    """
    
    def __init__(self, num_drones, num_sensors):
        self.num_drones = num_drones
        self.num_sensors = num_sensors
        self.drone_positions = {}  # Track drone positions
        self.sensor_positions = {}  # Track sensor positions
        self.drone_battery = {}  # Track drone battery levels
        self.task_queue = []
        self.assigned_tasks = defaultdict(list)
        
        # Initialize positions
        self._initialize_positions()
    
    def _initialize_positions(self):
        """Initialize random positions for drones and sensors in a grid"""
        grid_size = int(math.sqrt(self.num_sensors)) + 2
        
        # Place sensors in a grid pattern
        sensor_idx = 0
        for i in range(grid_size):
            for j in range(grid_size):
                if sensor_idx < self.num_sensors:
                    # Sensor IDs start from 100
                    self.sensor_positions[100 + sensor_idx] = (i * 10, j * 10)
                    sensor_idx += 1
        
        # Place drones at random initial positions
        for i in range(self.num_drones):
            # Drone IDs start from 50
            drone_id = 50 + i
            self.drone_positions[drone_id] = (
                random.randint(0, grid_size * 10),
                random.randint(0, grid_size * 10)
            )
            self.drone_battery[drone_id] = 100.0  # Full battery
    
    def calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance between two positions"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def schedule_task(self, sensor_id, current_time):
        """
        Schedule a drone to collect data from a sensor
        Uses greedy algorithm to find the best drone
        """
        if sensor_id not in self.sensor_positions:
            return None
        
        sensor_pos = self.sensor_positions[sensor_id]
        best_drone = None
        min_cost = float('inf')
        
        for drone_id, drone_pos in self.drone_positions.items():
            # Calculate cost based on distance and battery
            distance = self.calculate_distance(drone_pos, sensor_pos)
            battery_penalty = (100 - self.drone_battery[drone_id]) * 0.5
            
            # Cost function: distance + battery penalty
            cost = distance + battery_penalty
            
            # Check if drone has enough battery (simplified)
            if self.drone_battery[drone_id] > 20 and cost < min_cost:
                min_cost = cost
                best_drone = drone_id
        
        if best_drone:
            self.assigned_tasks[best_drone].append({
                'sensor': sensor_id,
                'time': current_time,
                'distance': self.calculate_distance(
                    self.drone_positions[best_drone],
                    sensor_pos
                )
            })
            
            # Update drone position to sensor location
            self.drone_positions[best_drone] = sensor_pos
            
            # Decrease battery (simplified model)
            self.drone_battery[best_drone] -= min(5, self.drone_battery[best_drone])
            
            return best_drone
        
        return None
    
    def recharge_drone(self, drone_id):
        """Simulate drone recharging"""
        if drone_id in self.drone_battery:
            self.drone_battery[drone_id] = min(100, self.drone_battery[drone_id] + 20)


