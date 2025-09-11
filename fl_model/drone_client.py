import tensorflow as tf
import requests
import os
import numpy as np
import time

# --- Configuration ---
SERVER_URL = "http://127.0.0.1:5000/upload_weights" # IMPORTANT: Change to your server's IP
IMG_HEIGHT = 150
IMG_WIDTH = 150
NUM_CLASSES = 12 # As per your original model
DRONE_ID = f"drone_{np.random.randint(1000, 9999)}"

# --- Model Architecture Definition ---
# This function MUST exactly replicate the architecture of your trained model.
def create_model_structure():
    """
    Creates and returns the Keras model with the same architecture as the trained one.
    Weights are not loaded here.
    """
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
        include_top=False,
        weights=None # We only need the structure, not pre-trained weights
    )
    base_model.trainable = True

    # Fine-tune from the same layer as the original model
    fine_tune_at = len(base_model.layers) - 30
    for layer in base_model.layers[:fine_tune_at]:
        layer.trainable = False

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3)),
        # Data augmentation layers are part of the model itself
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.2),
        tf.keras.layers.RandomZoom(0.2),
        tf.keras.layers.Rescaling(1./127.5, offset=-1),
        base_model,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(NUM_CLASSES, activation='softmax')
    ])

    # Compile with the same fine-tuning optimizer and settings
    optimizer = tf.keras.optimizers.Adam(learning_rate=1e-5)
    model.compile(optimizer=optimizer,
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    return model

# --- Simulation & Core Logic ---
def create_dummy_local_data():
    """
    This function simulates the drone collecting new, labeled data.
    In a real system, this data would come from the drone's camera and a
    human-in-the-loop labeling process.
    """
    print("Simulating collection of new local data...")
    dummy_data_dir = "temp_drone_data"
    os.makedirs(dummy_data_dir, exist_ok=True)

    # Create a few dummy class directories
    for i in range(3): # Assume drone sees 3 classes
        class_dir = os.path.join(dummy_data_dir, f"class_{i}")
        os.makedirs(class_dir, exist_ok=True)
        # Create a few dummy images
        for j in range(10): # 10 images per class
            dummy_image = np.random.rand(IMG_HEIGHT, IMG_WIDTH, 3) * 255
            tf.keras.preprocessing.image.save_img(
                os.path.join(class_dir, f"img_{j}.png"),
                dummy_image,
                scale=False
            )
    return dummy_data_dir, 30 # Return path and number of samples

def local_training_and_upload(global_weights_path):
    """
    The main function for the drone's federated learning client role.
    """
    print(f"\n--- Starting Local Training on {DRONE_ID} ---")

    # 1. Create the model structure
    local_model = create_model_structure()

    # 2. Load the latest global weights downloaded from the server
    try:
        local_model.load_weights(global_weights_path)
        print(f"Successfully loaded global weights from {global_weights_path}")
    except Exception as e:
        print(f"Could not load global weights: {e}. Starting with initial weights.")
        # In a real scenario, you'd handle this by re-downloading or waiting.

    # 3. Get the new locally collected data
    local_data_path, num_samples = create_dummy_local_data()

    # 4. Create a dataset from the new images
    # Use a small batch size for on-device training to conserve memory
    new_dataset = tf.keras.utils.image_dataset_from_directory(
        local_data_path,
        image_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=8,
        label_mode='int'
    )

    # 5. Fine-tune the model on the new data for a few epochs
    print("Starting local fine-tuning...")
    local_model.fit(new_dataset, epochs=5, verbose=1)
    print("Local fine-tuning complete.")

    # 6. Save the updated weights to a file
    timestamp = int(time.time())
    updated_weights_path = f"{DRONE_ID}_update_{timestamp}.weights.h5"
    local_model.save_weights(updated_weights_path)
    print(f"Saved updated weights to {updated_weights_path}")

    # 7. Upload the new weights to the server
    print(f"Uploading {updated_weights_path} to server...")
    try:
        with open(updated_weights_path, 'rb') as f:
            files = {'weights': (os.path.basename(updated_weights_path), f)}
            data = {'num_samples': num_samples}
            response = requests.post(SERVER_URL, files=files, data=data, timeout=60)

            if response.status_code == 200:
                print("Successfully uploaded weights to the server.")
            else:
                print(f"Failed to upload. Server responded with: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"An error occurred during upload: {e}")
    finally:
        # Clean up local files
        os.remove(updated_weights_path)
        # tf.io.gfile.rmtree(local_data_path) # remove dummy data


if __name__ == "__main__":
    # In a real workflow, the drone would download this file from the server.
    # We simulate this by assuming the initial model is available locally.
    initial_model_path = 'global_model_initial.weights.h5'

    # Create a dummy initial model file if it doesn't exist
    if not os.path.exists(initial_model_path):
        print(f"Initial model '{initial_model_path}' not found. Creating a placeholder.")
        model = create_model_structure()
        model.save_weights(initial_model_path)

    # Run the main federated learning process for the drone
    local_training_and_upload(global_weights_path=initial_model_path)
