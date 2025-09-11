# Federated Learning System for Pest Detection Drones

there are some places where you'll need to give custom values. I've mentioned them here so change them accordingly

## 1. Project Overview

This project is a complete simulation of a Federated Learning (FL) system designed for a fleet of agricultural drones. The system allows each drone to learn from the new pest data it collects and then contributes that learning to a central "global model." This is achieved without ever sending the private image data from the drone to the server, ensuring data privacy and saving network bandwidth.

The architecture consists of three main components:
* **Drone Client (`drone_client.py`):** Simulates a drone in the field. It loads the latest global model, retrains it on new local data, and uploads the improvements (model weights).
* **Cloud Server (`cloud_server.py`):** A simple API server that acts as a central collection point for all the weight updates sent by the drones.
* **Aggregation Script (`monthly_aggregation_script.py`):** The core of the FL system. This script is run periodically on the server to intelligently combine all the drone updates using the Federated Averaging (FedAvg) algorithm, creating a new, smarter global model.

## 2. System Setup (for a new environment)

These steps are for setting up the project from scratch on a Linux-based system (like WSL) with Python 3.

### Step A: Create a Virtual Environment

It is critical to run this project in an isolated virtual environment to manage dependencies.

```bash
# Navigate to the project folder
cd /path/to/your/my_fl_project

# Create the virtual environment
python3 -m venv venv

# Activate the environment (must be done in every new terminal)
source venv/bin/activate
```

### Step B: Install Required Libraries

With the environment active, install all necessary Python libraries.

```bash
pip install tensorflow flwr[simulation] numpy requests flask werkzeug
```

### Step C: Prepare the Initial Model

The FL process needs a starting point. The system is configured to use the `pest_detection_model_fine_tuned.keras` file as the initial model. Ensure this file is present in the main project directory. The scripts have already been modified to look for this exact filename.

## 3. How to Run the Demo

To demonstrate a full cycle of the federated learning process, you will need to run the scripts in a specific order using multiple terminals.

**Prerequisite:** Ensure your virtual environment is active (`source venv/bin/activate`) in each terminal.

### Step 1: Start the Cloud Server

This server listens for updates from the drones.
*In Terminal 1:*
```bash
python cloud_server.py
```
The server will start and indicate that it is running and listening for connections.

### Step 2: Run the Drone Clients

Each command simulates a different drone training on new data and uploading its weights.
*In Terminal 2:*
```bash
python drone_client.py
```
*In Terminal 3:*
```bash
python drone_client.py
```
You will see both clients perform a simulated training cycle and then upload their results to the server. The server terminal will print a message each time it receives an update.

### Step 3: Run the Aggregation Script

After at least two clients have uploaded their updates, you can run the aggregation process to create a new global model.
*In any of the terminals (after a client has finished):*
```bash
python monthly_aggregation_script.py
```
This script will read the files in the `drone_updates` folder, perform the weighted average, and save a new, improved global model in the `global_models` folder.

## 4. Configuration for Real-World Deployment

To adapt this simulation for a real-world scenario, the following parameters in the code need to be reviewed and modified.

### In `drone_client.py`:

* **`SERVER_URL`**: This is the most critical change. The placeholder `http://127.0.0.1:5000/upload_weights` must be replaced with the public IP address or domain name of the production cloud server.
* **`create_dummy_local_data()`**: This entire function must be replaced with the actual logic for loading the new, human-verified image data collected by the drone.
* **`local_model.fit(..., epochs=5, ...)`**: The number of training epochs (currently 5) is a key hyperparameter that may need to be tuned based on real-world performance.

### In `cloud_server.py`:

* **`UPLOAD_FOLDER`**: The directory for storing incoming updates is set to `'drone_updates'`. This can be changed to any path required by the server's infrastructure. If changed, `UPDATES_DIR` in the aggregation script must also be updated.

### In `monthly_aggregation_script.py`:

* **`UPDATES_DIR` & `MODELS_DIR`**: These variables define the storage locations for incoming updates and outgoing global models. They should be configured to point to the correct paths on the production server.