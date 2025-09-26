#!/usr/bin/env python3
"""
Agriculture Edge Computing Simulation using YAFS
Simulates drone-based data collection from LoRaWAN soil sensors
with MEC server task scheduling and cloud connectivity
"""

import json
import csv
import random
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

class AgricultureTopology:
    """Creates the agriculture edge topology"""
    
    def __init__(self, num_sensors=12, num_drones=3):
        self.num_sensors = num_sensors
        self.num_drones = num_drones
        self.nodes = {}
        self.edges = []
        self.sensor_positions = []
        self.drone_positions = []
        
    def create_topology(self):
        """Build the complete topology"""
        # Create cloud layer
        cloud_id = "cloud_server"
        self.nodes[cloud_id] = {
            "type": "cloud",
            "IPT": 1000, 
            "RAM": 32000, 
            "STORAGE": 100000,
            "coordinates": (0, 100)
        }
        
        # Create MEC/Fog server
        fog_id = "mec_server"
        self.nodes[fog_id] = {
            "type": "fog",
            "IPT": 500,
            "RAM": 16000,
            "STORAGE": 50000,
            "coordinates": (0, 50)
        }
        
        # Connect cloud and fog
        self.edges.append((cloud_id, fog_id, {"BW": 1000, "PR": 10}))
        self.edges.append((fog_id, cloud_id, {"BW": 1000, "PR": 10}))
        
        # Create LoRaWAN gateway
        gateway_id = "lorawan_gateway"
        self.nodes[gateway_id] = {
            "type": "gateway",
            "IPT": 50,
            "RAM": 1000,
            "STORAGE": 5000,
            "coordinates": (0, 25)
        }
        
        # Connect gateway to fog server
        self.edges.append((gateway_id, fog_id, {"BW": 100, "PR": 20}))
        self.edges.append((fog_id, gateway_id, {"BW": 100, "PR": 20}))
        
        # Create soil sensors in a grid pattern
        sensor_ids = []
        grid_size = int(np.sqrt(self.num_sensors))
        for i in range(self.num_sensors):
            x = (i % grid_size) * 20 - 40
            y = (i // grid_size) * 20 - 40
            sensor_id = f"soil_sensor_{i}"
            self.nodes[sensor_id] = {
                "type": "sensor",
                "IPT": 1,
                "RAM": 64,
                "STORAGE": 128,
                "coordinates": (x, y)
            }
            sensor_ids.append(sensor_id)
            self.sensor_positions.append((x, y, sensor_id))
            
            # Connect sensor to gateway (LoRaWAN)
            self.edges.append((sensor_id, gateway_id, {"BW": 1, "PR": 100}))
            self.edges.append((gateway_id, sensor_id, {"BW": 1, "PR": 100}))
        
        # Create drones (edge nodes)
        drone_ids = []
        for i in range(self.num_drones):
            x = random.uniform(-60, 60)
            y = random.uniform(-60, 60)
            drone_id = f"drone_{i}"
            self.nodes[drone_id] = {
                "type": "drone",
                "IPT": 100,
                "RAM": 4000,
                "STORAGE": 10000,
                "coordinates": (x, y)
            }
            drone_ids.append(drone_id)
            self.drone_positions.append((x, y, drone_id))
            
            # Connect drone to fog server (WiFi/Cellular)
            self.edges.append((drone_id, fog_id, {"BW": 50, "PR": 50}))
            self.edges.append((fog_id, drone_id, {"BW": 50, "PR": 50}))
        
        return self.nodes, self.edges, sensor_ids, drone_ids, fog_id, cloud_id, gateway_id

class TaskScheduler:
    """Implements efficient task scheduling algorithm for drones"""
    
    def __init__(self, drones, sensors):
        self.drones = drones
        self.sensors = sensors
        self.assignments = {}
        
    def calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance between two positions"""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def k_means_clustering_assignment(self, drone_positions, sensor_positions):
        """Use K-means inspired algorithm for optimal drone-sensor assignment"""
        # Initialize centroids (drone positions)
        centroids = [(pos[0], pos[1]) for pos in drone_positions]
        assignments = {i: [] for i in range(len(centroids))}
        
        # Assign each sensor to nearest drone
        for sensor in sensor_positions:
            distances = [self.calculate_distance(centroid, sensor) 
                        for centroid in centroids]
            closest_drone = distances.index(min(distances))
            assignments[closest_drone].append(sensor)
        
        return assignments
    
    def genetic_algorithm_optimization(self, drone_positions, sensor_positions):
        """Use genetic algorithm for optimal task scheduling"""
        population_size = 50
        generations = 100
        mutation_rate = 0.1
        
        # Initialize population with random assignments
        population = []
        for _ in range(population_size):
            assignment = {i: [] for i in range(len(drone_positions))}
            for sensor in sensor_positions:
                drone_idx = random.randint(0, len(drone_positions) - 1)
                assignment[drone_idx].append(sensor)
            population.append(assignment)
        
        def fitness(assignment):
            """Calculate fitness based on total distance and load balancing"""
            total_distance = 0
            load_variance = 0
            
            distances = []
            for drone_idx, sensors in assignment.items():
                drone_distance = 0
                for sensor in sensors:
                    drone_distance += self.calculate_distance(
                        drone_positions[drone_idx], sensor
                    )
                distances.append(drone_distance)
                total_distance += drone_distance
            
            # Penalize unbalanced loads
            if distances:
                load_variance = np.var(distances)
            
            return 1 / (total_distance + load_variance + 1)
        
        # Evolve population
        for generation in range(generations):
            # Calculate fitness for all assignments
            fitness_scores = [(assignment, fitness(assignment)) for assignment in population]
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Select top 50% for reproduction
            survivors = [assignment for assignment, _ in fitness_scores[:population_size//2]]
            
            # Create new population
            new_population = survivors[:]
            
            while len(new_population) < population_size:
                parent1 = random.choice(survivors)
                parent2 = random.choice(survivors)
                
                # Crossover
                child = {i: [] for i in range(len(drone_positions))}
                for sensor in sensor_positions:
                    # Choose parent randomly for each sensor
                    if random.random() < 0.5:
                        # Find which drone has this sensor in parent1
                        for drone_idx, sensors in parent1.items():
                            if sensor in sensors:
                                child[drone_idx].append(sensor)
                                break
                    else:
                        # Find which drone has this sensor in parent2
                        for drone_idx, sensors in parent2.items():
                            if sensor in sensors:
                                child[drone_idx].append(sensor)
                                break
                
                # Mutation
                if random.random() < mutation_rate:
                    sensor_to_move = random.choice(sensor_positions)
                    # Remove sensor from current drone
                    for drone_idx, sensors in child.items():
                        if sensor_to_move in sensors:
                            sensors.remove(sensor_to_move)
                            break
                    # Assign to random drone
                    new_drone = random.randint(0, len(drone_positions) - 1)
                    child[new_drone].append(sensor_to_move)
                
                new_population.append(child)
            
            population = new_population
        
        # Return best assignment
        final_fitness = [(assignment, fitness(assignment)) for assignment in population]
        final_fitness.sort(key=lambda x: x[1], reverse=True)
        return final_fitness[0][0]
    
    def generate_schedule(self, drone_positions, sensor_positions, algorithm="kmeans"):
        """Generate efficient task schedule using specified algorithm"""
        if algorithm == "genetic":
            assignments = self.genetic_algorithm_optimization(drone_positions, sensor_positions)
        else:
            assignments = self.k_means_clustering_assignment(drone_positions, sensor_positions)
        
        schedule = []
        
        for drone_idx, sensors in assignments.items():
            total_distance = 0
            for sensor in sensors:
                distance = self.calculate_distance(drone_positions[drone_idx], sensor)
                total_distance += distance
                schedule.append({
                    'drone_id': drone_idx,
                    'sensor_id': sensor[2],  # sensor node id
                    'distance': distance,
                    'collection_time': distance / 10 + 2,  # Travel time + collection time
                    'energy_cost': distance * 0.1 + 5  # Energy for travel + operation
                })
        
        return schedule, assignments

class SimulationLogger:
    """Logs simulation results to CSV files"""
    
    def __init__(self):
        self.messages = []
        self.node_metrics = []
        self.task_assignments = []
        self.energy_consumption = []
        self.network_performance = []
        self.latency_analysis = []
        
    def log_message(self, time, src, dst, message_size, latency, message_type="data"):
        """Log message transmission"""
        self.messages.append({
            'timestamp': time,
            'source': src,
            'destination': dst,
            'message_size': message_size,
            'latency': latency,
            'message_type': message_type
        })
    
    def log_node_metrics(self, time, node_id, cpu_usage, ram_usage, network_usage, node_type="unknown"):
        """Log node resource usage"""
        self.node_metrics.append({
            'timestamp': time,
            'node_id': node_id,
            'node_type': node_type,
            'cpu_usage': cpu_usage,
            'ram_usage': ram_usage,
            'network_usage': network_usage
        })
    
    def log_task_assignment(self, drone_id, sensor_id, distance, collection_time, energy_cost):
        """Log task assignments"""
        self.task_assignments.append({
            'drone_id': drone_id,
            'sensor_id': sensor_id,
            'distance': distance,
            'collection_time': collection_time,
            'energy_cost': energy_cost
        })
    
    def log_energy_consumption(self, time, node_id, energy_consumed, total_energy, battery_level):
        """Log energy consumption"""
        self.energy_consumption.append({
            'timestamp': time,
            'node_id': node_id,
            'energy_consumed': energy_consumed,
            'total_energy': total_energy,
            'battery_level': battery_level
        })
    
    def log_network_performance(self, time, link, throughput, packet_loss, jitter):
        """Log network performance metrics"""
        self.network_performance.append({
            'timestamp': time,
            'link': link,
            'throughput': throughput,
            'packet_loss': packet_loss,
            'jitter': jitter
        })
    
    def log_latency_analysis(self, time, operation, end_to_end_latency, processing_time, transmission_time):
        """Log latency analysis"""
        self.latency_analysis.append({
            'timestamp': time,
            'operation': operation,
            'end_to_end_latency': end_to_end_latency,
            'processing_time': processing_time,
            'transmission_time': transmission_time
        })
    
    def save_to_csv(self):
        """Save all logs to CSV files"""
        datasets = [
            ('agriculture_messages.csv', self.messages),
            ('agriculture_node_metrics.csv', self.node_metrics),
            ('agriculture_task_assignments.csv', self.task_assignments),
            ('agriculture_energy_consumption.csv', self.energy_consumption),
            ('agriculture_network_performance.csv', self.network_performance),
            ('agriculture_latency_analysis.csv', self.latency_analysis)
        ]
        
        for filename, data in datasets:
            if data:
                with open(filename, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                print(f"Generated: {filename}")

def run_simulation():
    """Main simulation function"""
    print("Starting Agriculture Edge Computing Simulation...")
    print("=" * 60)
    
    # Configuration parameters
    NUM_SENSORS = 12
    NUM_DRONES = 3
    SIMULATION_TIME = 1000
    TIME_STEP = 10
    
    # Initialize components
    print(f"Initializing topology with {NUM_SENSORS} sensors and {NUM_DRONES} drones...")
    topo_builder = AgricultureTopology(num_sensors=NUM_SENSORS, num_drones=NUM_DRONES)
    nodes, edges, sensor_ids, drone_ids, fog_id, cloud_id, gateway_id = topo_builder.create_topology()
    
    # Create task scheduler and generate optimal assignments
    print("Generating optimal task assignments using genetic algorithm...")
    scheduler = TaskScheduler(drone_ids, sensor_ids)
    schedule, assignments = scheduler.generate_schedule(
        topo_builder.drone_positions, 
        topo_builder.sensor_positions,
        algorithm="genetic"
    )
    
    # Initialize logger
    logger = SimulationLogger()
    
    # Log task assignments
    print("Logging task assignments...")
    for task in schedule:
        logger.log_task_assignment(
            task['drone_id'], task['sensor_id'], 
            task['distance'], task['collection_time'], 
            task['energy_cost']
        )
    
    print(f"Running simulation for {SIMULATION_TIME} time units...")
    print("=" * 60)
    
    # Simulate message flows and resource usage
    simulation_time = 0
    drone_energy = {i: 1000 for i in range(NUM_DRONES)}  # Initial battery
    
    while simulation_time < SIMULATION_TIME:
        # Print progress
        if simulation_time % 100 == 0:
            print(f"Simulation progress: {simulation_time}/{SIMULATION_TIME} ({(simulation_time/SIMULATION_TIME)*100:.1f}%)")
        
        # Simulate sensor data collection
        for i, drone_id in enumerate(drone_ids):
            assigned_sensors = assignments.get(i, [])
            
            for sensor in assigned_sensors:
                # Simulate sensor reading
                sensor_data_size = random.randint(50, 200)
                sensor_latency = random.uniform(10, 50)
                
                # Log message from sensor to drone (via gateway)
                logger.log_message(
                    simulation_time, sensor[2], 
                    f"drone_{i}", sensor_data_size, sensor_latency, "sensor_data"
                )
                
                # Simulate image capture
                image_size = random.randint(2000, 8000)
                capture_time = random.uniform(1, 3)
                
                # Aggregate data on drone
                aggregated_size = sensor_data_size + image_size
                processing_time = random.uniform(2, 8)
                
                # Log drone to fog server message
                fog_latency = random.uniform(20, 80)
                logger.log_message(
                    simulation_time, f"drone_{i}", 
                    "mec_server", aggregated_size, fog_latency, "aggregated_data"
                )
                
                # Log latency analysis
                end_to_end_latency = sensor_latency + processing_time + fog_latency
                logger.log_latency_analysis(
                    simulation_time, f"sensor_to_cloud_via_drone_{i}",
                    end_to_end_latency, processing_time, sensor_latency + fog_latency
                )
                
                # Update drone energy
                energy_consumed = random.uniform(5, 15)
                drone_energy[i] -= energy_consumed
                battery_level = (drone_energy[i] / 1000) * 100
                
                logger.log_energy_consumption(
                    simulation_time, f"drone_{i}", 
                    energy_consumed, drone_energy[i], battery_level
                )
        
        # Simulate fog to cloud communication
        cloud_message_size = random.randint(1000, 5000)
        cloud_latency = random.uniform(50, 150)
        logger.log_message(
            simulation_time, "mec_server", 
            "cloud_server", cloud_message_size, cloud_latency, "analytics_data"
        )
        
        # Log node metrics for all nodes
        node_types = {
            "cloud_server": "cloud",
            "mec_server": "fog",
            "lorawan_gateway": "gateway"
        }
        
        for node_id, node_type in node_types.items():
            if node_type == "cloud":
                cpu_usage = random.uniform(10, 40)
                ram_usage = random.uniform(5000, 15000)
                network_usage = random.uniform(30, 80)
            elif node_type == "fog":
                cpu_usage = random.uniform(30, 70)
                ram_usage = random.uniform(2000, 8000)
                network_usage = random.uniform(20, 60)
            else:  # gateway
                cpu_usage = random.uniform(15, 45)
                ram_usage = random.uniform(200, 600)
                network_usage = random.uniform(10, 30)
            
            logger.log_node_metrics(
                simulation_time, node_id, cpu_usage, ram_usage, network_usage, node_type
            )
        
        # Log drone metrics
        for i, drone_id in enumerate(drone_ids):
            cpu_usage = random.uniform(20, 80)
            ram_usage = random.uniform(1000, 3000)
            network_usage = random.uniform(10, 40)
            logger.log_node_metrics(
                simulation_time, f"drone_{i}", 
                cpu_usage, ram_usage, network_usage, "drone"
            )
        
        # Log sensor metrics
        for i, sensor_id in enumerate(sensor_ids):
            cpu_usage = random.uniform(5, 20)
            ram_usage = random.uniform(20, 60)
            network_usage = random.uniform(1, 5)
            logger.log_node_metrics(
                simulation_time, sensor_id,
                cpu_usage, ram_usage, network_usage, "sensor"
            )
        
        # Log network performance for key links
        links = [
            ("sensors", "gateway"),
            ("gateway", "fog"),
            ("drones", "fog"),
            ("fog", "cloud")
        ]
        
        for link in links:
            if link[0] == "sensors":
                throughput = random.uniform(0.5, 2.0)  # LoRaWAN is low bandwidth
                packet_loss = random.uniform(0, 5)
                jitter = random.uniform(10, 50)
            elif link[0] == "drones":
                throughput = random.uniform(20, 50)  # WiFi/Cellular
                packet_loss = random.uniform(0, 2)
                jitter = random.uniform(5, 20)
            else:
                throughput = random.uniform(50, 200)  # High-speed links
                packet_loss = random.uniform(0, 1)
                jitter = random.uniform(1, 10)
            
            logger.log_network_performance(
                simulation_time, f"{link[0]}_to_{link[1]}",
                throughput, packet_loss, jitter
            )
        
        simulation_time += TIME_STEP
    
    print("\nSimulation completed!")
    print("=" * 60)
    
    # Save results to CSV
    print("Saving results to CSV files...")
    logger.save_to_csv()
    
    print("\nGenerated CSV files:")
    print("- agriculture_messages.csv: Message transmission logs")
    print("- agriculture_node_metrics.csv: Node resource usage")
    print("- agriculture_task_assignments.csv: Drone-sensor assignments")
    print("- agriculture_energy_consumption.csv: Energy consumption logs")
    print("- agriculture_network_performance.csv: Network performance metrics")
    print("- agriculture_latency_analysis.csv: End-to-end latency analysis")
    
    # Print comprehensive summary statistics
    print(f"\nSimulation Summary:")
    print("=" * 40)
    print(f"Network Configuration:")
    print(f"  - Sensors: {NUM_SENSORS}")
    print(f"  - Drones: {NUM_DRONES}")
    print(f"  - Simulation time: {SIMULATION_TIME} units")
    print(f"  - Time step: {TIME_STEP} units")
    
    print(f"\nData Collection Statistics:")
    print(f"  - Total messages logged: {len(logger.messages)}")
    print(f"  - Total task assignments: {len(logger.task_assignments)}")
    print(f"  - Total energy logs: {len(logger.energy_consumption)}")
    print(f"  - Network performance samples: {len(logger.network_performance)}")
    
    # Calculate and display optimization results
    print(f"\nTask Assignment Optimization Results:")
    print("-" * 40)
    total_system_distance = 0
    for drone_idx, sensors in assignments.items():
        drone_distance = sum(scheduler.calculate_distance(
            topo_builder.drone_positions[drone_idx], sensor
        ) for sensor in sensors)
        total_system_distance += drone_distance
        
        print(f"  Drone {drone_idx}:")
        print(f"    - Assigned sensors: {len(sensors)}")
        print(f"    - Total travel distance: {drone_distance:.2f} units")
        print(f"    - Average distance per sensor: {(drone_distance/len(sensors) if sensors else 0):.2f} units")
    
    print(f"\n  System totals:")
    print(f"    - Total system travel distance: {total_system_distance:.2f} units")
    print(f"    - Average distance per assignment: {(total_system_distance/len(schedule) if schedule else 0):.2f} units")
    
    # Energy analysis
    print(f"\nEnergy Analysis:")
    print("-" * 40)
    for i in range(NUM_DRONES):
        final_energy = drone_energy[i]
        energy_consumed = 1000 - final_energy
        efficiency = (final_energy / 1000) * 100
        print(f"  Drone {i}:")
        print(f"    - Energy consumed: {energy_consumed:.2f} units")
        print(f"    - Remaining battery: {efficiency:.1f}%")
    
    # Message type analysis
    message_types = {}
    total_data_transferred = 0
    for msg in logger.messages:
        msg_type = msg['message_type']
        if msg_type not in message_types:
            message_types[msg_type] = {'count': 0, 'total_size': 0, 'avg_latency': 0}
        message_types[msg_type]['count'] += 1
        message_types[msg_type]['total_size'] += msg['message_size']
        message_types[msg_type]['avg_latency'] += msg['latency']
        total_data_transferred += msg['message_size']
    
    print(f"\nData Transfer Analysis:")
    print("-" * 40)
    for msg_type, stats in message_types.items():
        avg_latency = stats['avg_latency'] / stats['count'] if stats['count'] > 0 else 0
        avg_size = stats['total_size'] / stats['count'] if stats['count'] > 0 else 0
        print(f"  {msg_type.replace('_', ' ').title()}:")
        print(f"    - Messages: {stats['count']}")
        print(f"    - Total data: {stats['total_size']:,} bytes")
        print(f"    - Avg message size: {avg_size:.1f} bytes")
        print(f"    - Avg latency: {avg_latency:.1f} ms")
    
    print(f"\n  Total data transferred: {total_data_transferred:,} bytes ({total_data_transferred/1024/1024:.2f} MB)")
    
    # Network performance summary
    if logger.network_performance:
        print(f"\nNetwork Performance Summary:")
        print("-" * 40)
        
        link_stats = {}
        for perf in logger.network_performance:
            link = perf['link']
            if link not in link_stats:
                link_stats[link] = {'throughput': [], 'packet_loss': [], 'jitter': []}
            link_stats[link]['throughput'].append(perf['throughput'])
            link_stats[link]['packet_loss'].append(perf['packet_loss'])
            link_stats[link]['jitter'].append(perf['jitter'])
        
        for link, stats in link_stats.items():
            avg_throughput = np.mean(stats['throughput'])
            avg_packet_loss = np.mean(stats['packet_loss'])
            avg_jitter = np.mean(stats['jitter'])
            print(f"  {link.replace('_', ' ').title()}:")
            print(f"    - Avg throughput: {avg_throughput:.2f} Mbps")
            print(f"    - Avg packet loss: {avg_packet_loss:.2f}%")
            print(f"    - Avg jitter: {avg_jitter:.2f} ms")
    
    print(f"\nSimulation completed successfully!")
    print(f"All results saved to CSV files for further analysis.")
    print("=" * 60)

if __name__ == "__main__":
    run_simulation()
