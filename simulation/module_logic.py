# Part 2: PrecisionAgricultureStrategy (imports DroneTaskScheduler from part1)
from edge_part1_fixed import DroneTaskScheduler

class PrecisionAgricultureStrategy:
    """
    Custom strategy for precision agriculture simulation
    Handles drone movement, data collection, and task scheduling
    """
    def __init__(self, path_results, num_drones, num_sensors):
        self.activations = 0
        self.path_results = path_results
        self.scheduler = DroneTaskScheduler(num_drones, num_sensors)
        self.data_collection_log = []
        self.drone_users = {}  # Track drone DES processes
        self.sensor_users = {}  # Track sensor DES processes
        
    def resolve_app(self,sim, key, fallback_name=None): 
    # 1) exact key present
        if key in sim.apps:
            return sim.apps[key]
    # 2) fallback_name as key
        if fallback_name and fallback_name in sim.apps:
            return sim.apps[fallback_name]
    # 3) try stringified numeric key
        try:
            if str(key) in sim.apps:
                return sim.apps[str(key)]
        except Exception:
            pass
    # 4) try matching by app.name attribute
        for app_obj in sim.apps.values():
            if hasattr(app_obj, "name") and app_obj.name == fallback_name:
                return app_obj
    # 5) fallback: return first app object (or raise if none)
        try:
            return next(iter(sim.apps.values()))
        except StopIteration:
            raise KeyError("sim.apps is empty — no applications were deployed.")
    def deploy_sensor_user(self, sim, sensor_id):
        """Deploy a soil sensor as a user generating data (robust app lookup)"""
        # prefer numeric index 0, but tolerate name-based mappings
        app_key = 0
        fallback_name = "SensorDataCollection"  # adjust if your app name differs
        app = self.resolve_app(sim, app_key, fallback_name=fallback_name)

        # Build message name as you had
        try:
            msg = app.get_message("M.SENSOR.DATA")
        except Exception:
            # fallback: try the first message in the app
            msgs = list(app.messages.values()) if hasattr(app, "messages") else []
            if msgs:
                msg = msgs[0]
            else:
                raise RuntimeError(f"No messages found in application {app}")

        # Deploy sensor at its node
        dist = deterministic_distribution(200, name="SensorData")  # Generate data every 200 time units
        idDES = sim.deploy_source(app.name if hasattr(app, "name") else app, id_node=sensor_id, msg=msg, distribution=dist)
        self.sensor_users[sensor_id] = idDES

        logging.info(f"Deployed soil sensor {sensor_id} with DES {idDES} using app key/name {getattr(app, 'name', app)}")
        return idDES


    
    def deploy_drone_user(self, sim, drone_id):
        """Deploy a drone as a mobile user that collects and processes data (robust app lookup)"""
        app_key = 1
        fallback_name = "DroneProcessing"
        app = self.resolve_app(sim, app_key, fallback_name=fallback_name)

        # Get standard message
        try:
            msg = app.get_message("M.DRONE.PROCESS")
        except Exception:
            msgs = list(app.messages.values()) if hasattr(app, "messages") else []
            if msgs:
                msg = msgs[0]
            else:
                raise RuntimeError(f"No messages found in application {app}")

        # Deploy drone at its node
        dist = deterministic_distribution(150, name="DroneProcess")
        idDES = sim.deploy_source(app.name if hasattr(app, "name") else app, id_node=drone_id, msg=msg, distribution=dist)
        self.drone_users[drone_id] = idDES

        logging.info(f"Deployed drone {drone_id} with DES {idDES} using app key/name {getattr(app, 'name', app)}")
        return idDES

    
    def move_drone_to_sensor(self, sim, drone_id, sensor_id):
        """Move drone to sensor location for data collection"""
        if drone_id in self.drone_users:
            drone_des = self.drone_users[drone_id]
            
            # Create edge between drone and sensor if not exists
            if not sim.topology.G.has_edge(drone_id, sensor_id):
                # LoRaWAN connection attributes
                att = {"BW": 50, "PR": 5}  # Lower bandwidth for LoRaWAN
                sim.topology.G.add_edge(drone_id, sensor_id, **att)
            
            # Log data collection
            self.data_collection_log.append({
                'time': sim.env.now,
                'drone_id': drone_id,
                'sensor_id': sensor_id,
                'action': 'collect_data',
                'battery': self.scheduler.drone_battery.get(drone_id, 0)
            })
            
            logging.info(f"Drone {drone_id} collecting data from sensor {sensor_id}")
    
    def __call__(self, sim, routing):
        """Main strategy execution - called periodically"""
        self.activations += 1
        routing.invalid_cache_value = True
        
        current_time = sim.env.now
        
        # Every activation, schedule drone tasks
        if self.activations % 2 == 0:
            # Select random sensors for data collection
            num_tasks = min(3, len(self.scheduler.sensor_positions))
            selected_sensors = random.sample(
                list(self.scheduler.sensor_positions.keys()),
                num_tasks
            )
            
            for sensor_id in selected_sensors:
                drone_id = self.scheduler.schedule_task(sensor_id, current_time)
                if drone_id:
                    self.move_drone_to_sensor(sim, drone_id, sensor_id)
                    logging.info(f"Scheduled drone {drone_id} to collect from sensor {sensor_id}")
        
        # Recharge drones with low battery
        for drone_id, battery in self.scheduler.drone_battery.items():
            if battery < 30:
                self.scheduler.recharge_drone(drone_id)
                # Move drone to MEC server (node 1) for recharging
                if drone_id in self.drone_users:
                    if not sim.topology.G.has_edge(drone_id, 1):
                        att = {"BW": 100, "PR": 10}
                        sim.topology.G.add_edge(drone_id, 1, **att)
                    logging.info(f"Drone {drone_id} returning to base for recharge")


