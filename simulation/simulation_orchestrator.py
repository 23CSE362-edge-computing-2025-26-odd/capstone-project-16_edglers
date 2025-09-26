# Part 4: main runner (imports helpers from parts 1-3)
from edge_part1_fixed import DroneTaskScheduler
from edge_part2_fixed import PrecisionAgricultureStrategy
from edge_part3_fixed import create_precision_agriculture_topology, sanitize_graph_for_gexf, normalize_apps_for_yafs_final

def main(stop_time, iteration, folder_results):
    """Main simulation function"""
    
    # Configuration
    NUM_DRONES = 4
    NUM_SENSORS = 16
    
    # Create topology
    t = create_precision_agriculture_topology(NUM_DRONES, NUM_SENSORS)
    
    # Save topology
    sanitize_graph_for_gexf(t.G)
    nx.write_gexf(t.G, folder_results + f"precision_agri_topology_{iteration}.gexf")
    
    # Create applications
    apps_json = {
        "apps": [
            {
                "id": 0,
                "name": "SensorDataCollection",
                "modules": [
                    {"id": "0_0", "name": "0_0", "type": "sensor_module", 
                     "inst": 10, "cpu": 0.5, "mem": 0.5}
                ],
                "messages": [
                    {"id": "M.SENSOR.DATA", "name": "M.SENSOR.DATA",
                     "src": "None", "dst": "0_0", "size": 100}
                ],
                "loops": []
            },
            {
                "id": 1,
                "name": "DroneProcessing",
                "modules": [
                    {"id": "1_0", "name": "1_0", "type": "drone_module",
                     "inst": 50, "cpu": 2, "mem": 2},
                    {"id": "1_1", "name": "1_1", "type": "mec_module",
                     "inst": 100, "cpu": 5, "mem": 5}
                ],
                "messages": [
                    {"id": "M.DRONE.PROCESS", "name": "M.DRONE.PROCESS",
                     "src": "None", "dst": "1_0", "size": 500},
                    {"id": "M.DRONE.TO.MEC", "name": "M.DRONE.TO.MEC",
                     "src": "1_0", "dst": "1_1", "size": 1000}
                ],
                "loops": [{"src": "1_0", "dst": "1_1", "size": 1000}]
            },
            {
                "id": 2,
                "name": "CloudAnalytics",
                "modules": [
                    {"id": "2_0", "name": "2_0", "type": "cloud_module",
                     "inst": 200, "cpu": 10, "mem": 10}
                ],
                "messages": [
                    {"id": "M.CLOUD.ANALYTICS", "name": "M.CLOUD.ANALYTICS",
                     "src": "None", "dst": "2_0", "size": 2000}
                ],
                "loops": []
            }
        ]
    }
    apps_input = apps_json
    if isinstance(apps_json, dict) and "apps" in apps_json:
        apps_input = apps_json["apps"]

    # If the helper expects a mapping keyed by id, convert list->dict
    if isinstance(apps_input, list):
    # Convert to dict keyed by app id (useful if create_applications_from_json expects mapping)
        try:
            apps_input = {app["id"]: app for app in apps_input}
        except Exception:
        # If conversion fails, just pass the list through
            pass
    apps_input = normalize_apps_for_yafs_final(apps_input if 'apps_input' in globals() else apps_json)

    # Now call the YAFS loader with the normalized apps
    apps = create_applications_from_json(apps_input)
    # Create placement
    placement_json = {
            "initialAllocation": [
    # Sensor modules on all sensors
        *[{"module_name": "0_0", "app": 0, "id_resource": 100 + i} 
      for i in range(NUM_SENSORS)],
    # Drone modules on drones
        *[{"module_name": "1_0", "app": 1, "id_resource": 50 + i}
        for i in range(NUM_DRONES)],
    # MEC module on MEC server
        {"module_name": "1_1", "app": 1, "id_resource": 1},
    # Cloud module on cloud
        {"module_name": "2_0", "app": 2, "id_resource": 0}
        ]

    }
    
    placement = JSONPlacement(name="Placement", json=placement_json)
    
    # Routing
    selector_path = DeviceSpeedAwareRouting()
    
    # Create simulation
    s = Sim(t, default_results_path=folder_results + "sim_trace")
    
    # Deploy applications
    for app_name in apps.keys():
        s.deploy_app(apps[app_name], placement, selector_path)
    
    # Create custom strategy
    strategy = PrecisionAgricultureStrategy(folder_results, NUM_DRONES, NUM_SENSORS)
    
    # Deploy initial sensors and drones
    for i in range(NUM_SENSORS):
        strategy.deploy_sensor_user(s, 100 + i)
    
    for i in range(NUM_DRONES):
        strategy.deploy_drone_user(s, 50 + i)
    
    # Deploy MEC user for cloud communication
    app = next(a for a in s.apps.values() if getattr(a, 'name', None) == "CloudAnalytics")
    msg = app.get_message("M.CLOUD.ANALYTICS")
    dist = deterministic_distribution(500, name="CloudAnalytics")
    s.deploy_source(2, id_node=1, msg=msg, distribution=dist)
    
    # Deploy monitor for dynamic behavior
    dist = deterministicDistributionStartPoint(100, 200, name="DroneScheduler")
    s.deploy_monitor("PrecisionAgricultureMonitor",
                     strategy,
                     dist,
                     **{"sim": s, "routing": selector_path})
    
    # Run simulation
    logging.info(f"Starting simulation iteration {iteration}")
    s.run(stop_time)
    s.print_debug_assignaments()
    
    # Save task scheduling log
    if strategy.data_collection_log:
        df_tasks = pd.DataFrame(strategy.data_collection_log)
        df_tasks.to_csv(folder_results + f"drone_tasks_{iteration}.csv", index=False)
    
    # Save drone scheduling info
    scheduling_info = []
    for drone_id, tasks in strategy.scheduler.assigned_tasks.items():
        for task in tasks:
            scheduling_info.append({
                'drone_id': drone_id,
                'sensor_id': task['sensor'],
                'scheduled_time': task['time'],
                'distance': task['distance']
            })
    
    if scheduling_info:
        df_schedule = pd.DataFrame(scheduling_info)
        df_schedule.to_csv(folder_results + f"task_schedule_{iteration}.csv", index=False)
    
    return strategy


def analyze_results(folder_results):
    """Analyze simulation results"""
    
    # Read simulation traces
    try:
        df = pd.read_csv(folder_results + "sim_trace.csv")
        df_link = pd.read_csv(folder_results + "sim_trace_link.csv")
        
        print("\n=== SIMULATION RESULTS ===")
        print(f"Total messages processed: {len(df)}")
        print(f"Total network transmissions: {len(df_link)}")
        
        # Analyze by application
        for app_id in df['app'].unique():
            df_app = df[df['app'] == app_id]
            print(f"\nApp {app_id} Statistics:")
            print(f"  - Messages processed: {len(df_app)}")
            
            if len(df_app) > 0:
                df_app.loc[:, 'transmission_time'] = df_app['time_emit'] - df_app['time_reception']
                df_app.loc[:, 'service_time'] = df_app['time_out'] - df_app['time_in']
                
                print(f"  - Avg transmission time: {df_app['transmission_time'].mean():.2f}")
                print(f"  - Avg service time: {df_app['service_time'].mean():.2f}")
                print(f"  - Deployed on nodes: {df_app['TOPO.dst'].unique()}")
        
        # Analyze drone tasks
        task_files = list(Path(folder_results).glob("drone_tasks_*.csv"))
        if task_files:
            df_tasks = pd.read_csv(task_files[0])
            print(f"\n=== DRONE OPERATIONS ===")
            print(f"Total data collections: {len(df_tasks)}")
            
            for drone_id in df_tasks['drone_id'].unique():
                drone_tasks = df_tasks[df_tasks['drone_id'] == drone_id]
                print(f"\nDrone {drone_id}:")
                print(f"  - Collections: {len(drone_tasks)}")
                print(f"  - Sensors visited: {drone_tasks['sensor_id'].nunique()}")
                print(f"  - Avg battery: {drone_tasks['battery'].mean():.2f}%")
        
        # Analyze task scheduling
        schedule_files = list(Path(folder_results).glob("task_schedule_*.csv"))
        if schedule_files:
            df_schedule = pd.read_csv(schedule_files[0])
            print(f"\n=== TASK SCHEDULING ===")
            print(f"Total scheduled tasks: {len(df_schedule)}")
            print(f"Average distance to sensor: {df_schedule['distance'].mean():.2f}")
            
            # Efficiency metrics
            for drone_id in df_schedule['drone_id'].unique():
                drone_schedule = df_schedule[df_schedule['drone_id'] == drone_id]
                print(f"\nDrone {drone_id} schedule:")
                print(f"  - Tasks assigned: {len(drone_schedule)}")
                print(f"  - Total distance: {drone_schedule['distance'].sum():.2f}")
                print(f"  - Sensors covered: {drone_schedule['sensor_id'].unique()}")
                
    except Exception as e:
        print(f"Error analyzing results: {e}")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create results folder
    folder_results = Path("results/")
    folder_results.mkdir(parents=True, exist_ok=True)
    folder_results = str(folder_results) + "/"
    
    # Simulation parameters
    n_iterations = 1
    simulation_duration = 10000
    
    # Run simulations
    for iteration in range(n_iterations):
        random.seed(iteration)
        logging.info(f"Running simulation iteration {iteration}")
        
        start_time = time.time()
        strategy = main(
            stop_time=simulation_duration,
            iteration=iteration,
            folder_results=folder_results
        )
        
        print(f"\n--- Iteration {iteration} completed in {time.time() - start_time:.2f} seconds ---")
    
    print("\n" + "="*50)
    print("SIMULATION COMPLETED!")
    print("="*50)
    
    # Analyze results
    analyze_results(folder_results)
    
    print(f"\nResults saved in: {folder_results}")
    print("Files generated:")
    print("  - sim_trace.csv: Main simulation trace")
    print("  - sim_trace_link.csv: Network link transmissions")
    print("  - drone_tasks_*.csv: Drone data collection log")
    print("  - task_schedule_*.csv: Task scheduling assignments")
    print("  - precision_agri_topology_*.gexf: Network topology")

