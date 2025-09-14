def create_precision_agriculture_topology(num_drones=4, num_sensors=16):
    """
    Create the precision agriculture topology:
    - Cloud layer (1 node)
    - MEC/Fog server (1 node)
    - Drones (edge nodes)
    - Soil sensors with LoRaWAN
    """
    t = Topology()
    t.G = nx.Graph()
    
    # Node 0: Cloud server
    cloud_attr = {"IPT": 10000, "type": "cloud"}
    t.G.add_node(0, **cloud_attr)
    
    # Node 1: MEC/Fog server (Farm server)
    mec_attr = {"IPT": 5000, "type": "mec"}
    t.G.add_node(1, **mec_attr)
    
    # Cloud-MEC connection (high bandwidth)
    t.G.add_edge(0, 1, BW=1000, PR=50)
    
    # Add drones (starting from node 50)
    for i in range(num_drones):
        drone_id = 50 + i
        drone_attr = {
            "IPT": 500,
            "type": "drone",
            "components": ["rpi", "gps", "camera", "lorawan_gateway"]
        }
        t.G.add_node(drone_id, **drone_attr)
        
        # Connect drone to MEC server
        t.G.add_edge(1, drone_id, BW=200, PR=20)
    
    # Add soil sensors (starting from node 100)
    for i in range(num_sensors):
        sensor_id = 100 + i
        sensor_attr = {
            "IPT": 10,
            "type": "soil_sensor",
            "lorawan": True
        }
        t.G.add_node(sensor_id, **sensor_attr)
        
        # Initially connect some sensors to nearby drones
        if i < num_drones:
            drone_id = 50 + i
            t.G.add_edge(drone_id, sensor_id, BW=50, PR=5)  # LoRaWAN connection
    
    return t
def sanitize_graph_for_gexf(G):
    """
    Convert attribute values that GEXF can't handle (lists, dicts, numpy types)
    into JSON-serializable scalars/strings.
    """
    for n, attrs in G.nodes(data=True):
        for k, v in list(attrs.items()):
            # Convert numpy types to Python scalars
            if isinstance(v, (np.generic,)):
                attrs[k] = v.item()
            # Convert lists/dicts/tuples/ndarrays to JSON string
            elif isinstance(v, (list, dict, tuple, np.ndarray)):
                attrs[k] = json.dumps(v)
            # If value is not a basic scalar, stringify it
            elif not isinstance(v, (str, int, float, bool, type(None))):
                attrs[k] = str(v)

    for u, v, attrs in G.edges(data=True):
        for k, val in list(attrs.items()):
            if isinstance(val, (np.generic,)):
                attrs[k] = val.item()
            elif isinstance(val, (list, dict, tuple, np.ndarray)):
                attrs[k] = json.dumps(val)
            elif not isinstance(val, (str, int, float, bool, type(None))):
                attrs[k] = str(val)
def normalize_messages(msgs, app_name=None):
    """
    Return a list of message dicts with keys required by YAFS loader:
      - 'name' (string)
      - 's' (source)
      - 'd' (destination)
      - 'bytes' (int)
      - 'instructions' (int)
    Heuristics:
      - map size/sz/length -> bytes
      - map instr/instructions -> instructions
      - if instructions missing and bytes available -> instructions = bytes * 1000
      - fallback defaults: bytes=0, instructions=1000
    """
    normalized = []
    for msg in msgs:
        if not isinstance(msg, dict):
            raise ValueError(f"Message must be dict in app {app_name}: {msg}")
        mm = dict(msg)

        # Ensure name
        if "name" not in mm:
            if "id" in mm:
                mm["name"] = str(mm["id"])
            else:
                raise ValueError(f"Message missing 'name' or 'id' in app {app_name}: {mm}")

        # Source / dest mapping (keep whatever you already have)
        if "s" not in mm:
            if "src" in mm:
                mm["s"] = mm.pop("src")
            elif "source" in mm:
                mm["s"] = mm.pop("source")
            else:
                mm["s"] = mm.get("s", "None")

        if "d" not in mm:
            if "dst" in mm:
                mm["d"] = mm.pop("dst")
            elif "dest" in mm:
                mm["d"] = mm.pop("dest")
            else:
                mm["d"] = mm.get("d", "None")

        # Bytes: map size-like keys to 'bytes'
        if "bytes" not in mm:
            if "size" in mm:
                mm["bytes"] = mm.pop("size")
            elif "sz" in mm:
                mm["bytes"] = mm.pop("sz")
            elif "length" in mm:
                mm["bytes"] = mm.pop("length")
            elif "size_bytes" in mm:
                mm["bytes"] = mm.pop("size_bytes")
            else:
                mm["bytes"] = 0

        # Coerce bytes to int if possible
        try:
            # sometimes users put strings like "1000" or floats like 100.5
            mm["bytes"] = int(float(mm["bytes"]))
        except Exception:
            # if can't convert, fallback to 0
            mm["bytes"] = 0

        # Instructions: prefer explicit keys, then fall back to heuristic (bytes * factor)
        if "instructions" not in mm:
            if "instr" in mm:
                mm["instructions"] = mm.pop("instr")
            elif "cpu_cycles" in mm:
                mm["instructions"] = mm.pop("cpu_cycles")
            else:
                # Heuristic: 1000 CPU cycles per byte (adjust if you want different granularity)
                mm["instructions"] = max(1000, int(mm["bytes"]) * 1000) if mm["bytes"] > 0 else 1000

        # Coerce instructions to int if possible
        try:
            mm["instructions"] = int(float(mm["instructions"]))
        except Exception:
            mm["instructions"] = 1000

        normalized.append(mm)
    return normalized
# ---- begin: comprehensive normalizer for YAFS create_applications_from_json ----
def normalize_apps_for_yafs_final(apps_input):
    """
    Normalize an 'apps' structure into the exact schema expected by the
    YAFS create_applications_from_json loader.

    Accepts:
      - apps_input: either {"apps": [...]} or a list of app dicts.

    Produces a list of apps where each app contains:
      - 'module': list of dicts with 'name' and 'RAM' (MB)
      - 'message': list of normalized message dicts
      - 'transmission': list derived from 'message' (with 'module' & 'message_in')
      - 'loop': list (if any)
    """
    # Helper coercions
    def coerce_int(v, default=0):
        try:
            return int(float(v))
        except Exception:
            return default

    # Unwrap wrapper if provided
    if isinstance(apps_input, dict) and "apps" in apps_input:
        apps_list = apps_input["apps"]
    else:
        apps_list = apps_input

    if apps_list is None:
        return []

    def normalize_messages(msgs, app_name=None):
        normalized = []
        for msg in msgs:
            if not isinstance(msg, dict):
                raise ValueError(f"Message must be a dict in app {app_name}: {msg}")
            mm = dict(msg)

            # Ensure name
            if "name" not in mm:
                mm["name"] = str(mm.get("id", "unnamed"))

            # Source (s) mapping: src/source/from -> s
            if "s" not in mm:
                for k in ("src", "source", "from"):
                    if k in mm:
                        mm["s"] = mm.pop(k)
                        break
                else:
                    mm["s"] = mm.get("s", "None")

            # Destination (d) mapping: dst/dest/to -> d
            if "d" not in mm:
                for k in ("dst", "dest", "to"):
                    if k in mm:
                        mm["d"] = mm.pop(k)
                        break
                else:
                    mm["d"] = mm.get("d", "None")

            # bytes mapping: size/sz/length/size_bytes -> bytes
            if "bytes" not in mm:
                for k in ("size", "sz", "length", "size_bytes"):
                    if k in mm:
                        mm["bytes"] = mm.pop(k)
                        break
                else:
                    mm["bytes"] = mm.get("bytes", 0)
            mm["bytes"] = coerce_int(mm["bytes"], 0)

            # instructions mapping and heuristic:
            # prefer explicit keys, else heuristic bytes * 1000, min 1000
            if "instructions" not in mm:
                for k in ("instr", "cpu_cycles"):
                    if k in mm:
                        mm["instructions"] = mm.pop(k)
                        break
                else:
                    mm["instructions"] = max(1000, mm["bytes"] * 1000) if mm["bytes"] > 0 else 1000
            mm["instructions"] = coerce_int(mm["instructions"], 1000)

            normalized.append(mm)
        return normalized

    normalized_apps = []
    for app in apps_list:
        if not isinstance(app, dict):
            raise ValueError(f"App entry must be a dict: {app}")
        a = dict(app)  # shallow copy

        # Plural -> singular keys
        if "modules" in a and "module" not in a:
            a["module"] = a.pop("modules")
        if "messages" in a and "message" not in a:
            a["message"] = a.pop("messages")
        if "loops" in a and "loop" not in a:
            a["loop"] = a.pop("loops")

        # dict->list conversions
        if isinstance(a.get("module"), dict):
            a["module"] = list(a["module"].values())
        if isinstance(a.get("message"), dict):
            a["message"] = list(a["message"].values())
        if isinstance(a.get("loop"), dict):
            a["loop"] = list(a["loop"].values())

        # Ensure module list exists and normalize RAM
        if "module" not in a or not isinstance(a["module"], (list, tuple)):
            raise ValueError(f"App entry missing 'module' list or wrong type: {a.get('name', a.get('id'))}")
        for m in a["module"]:
            if not isinstance(m, dict):
                raise ValueError(f"Module entry must be a dict, got: {m}")
            # Ensure name
            if "name" not in m:
                m["name"] = str(m.get("id", "unnamed"))
            # Normalize RAM from mem/ram/memory to integer MB
            if "RAM" not in m:
                if "mem" in m:
                    try:
                        mem_val = float(m["mem"])
                        # Heuristic: mem <= 16 -> GB to MB ; else assume MB
                        m["RAM"] = int(mem_val * 1024) if mem_val <= 16 else int(mem_val)
                    except Exception:
                        try:
                            m["RAM"] = int(m.get("mem", 128))
                        except Exception:
                            m["RAM"] = 128
                elif "ram" in m:
                    m["RAM"] = coerce_int(m["ram"], 128)
                elif "memory" in m:
                    m["RAM"] = coerce_int(m["memory"], 128)
                else:
                    m["RAM"] = 128
            try:
                m["RAM"] = int(m["RAM"])
            except Exception:
                m["RAM"] = 128

        # Normalize messages
        msgs = a.get("message", [])
        if msgs is None:
            msgs = []
        a["message"] = normalize_messages(msgs, app_name=a.get("name"))

        # Build transmission list if missing (and include required fields)
        if "transmission" not in a or not isinstance(a["transmission"], (list, tuple)):
            transmissions = []
            # default module for transmission entries: first module of the app
            if isinstance(a.get("module"), (list, tuple)) and len(a["module"]) > 0:
                default_module_name = a["module"][0].get("name", str(a["module"][0].get("id", "mod_0")))
            else:
                default_module_name = a.get("name", "app_unnamed") + "_mod"

            for mm in a["message"]:
                t = {
                    "name": mm.get("name"),
                    "s": mm.get("s", "None"),
                    "d": mm.get("d", "None"),
                    "instructions": mm.get("instructions", 1000),
                    "bytes": mm.get("bytes", 0),
                    # required by YAFS loader:
                    "module": mm.get("module", default_module_name),
                    "message_in": mm.get("message_in", mm.get("name"))
                }
                transmissions.append(t)
            a["transmission"] = transmissions
        else:
            # If transmission exists, ensure each entry includes module & message_in & numeric fields
            new_trans = []
            for t in a["transmission"]:
                tt = dict(t)
                if "module" not in tt:
                    if isinstance(a.get("module"), (list, tuple)) and len(a["module"]) > 0:
                        tt["module"] = a["module"][0].get("name")
                    else:
                        tt["module"] = a.get("name", "app_unnamed") + "_mod"
                if "message_in" not in tt:
                    # try to set it to a message name if possible
                    tt["message_in"] = tt.get("message_in", tt.get("name", None))
                tt["instructions"] = coerce_int(tt.get("instructions", 1000), 1000)
                tt["bytes"] = coerce_int(tt.get("bytes", 0), 0)
                new_trans.append(tt)
            a["transmission"] = new_trans

        # Ensure loop exists as list
        if "loop" not in a or a["loop"] is None:
            a["loop"] = a.get("loop", [])

        normalized_apps.append(a)

    return normalized_apps
