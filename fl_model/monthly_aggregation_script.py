import tensorflow as tf
import numpy as np
import os
import time

# --- Configuration ---
UPDATES_DIR = 'drone_updates'
MODELS_DIR = 'global_models'
IMG_HEIGHT = 150
IMG_WIDTH = 150
NUM_CLASSES = 12

# Ensure the global models directory exists
os.makedirs(MODELS_DIR, exist_ok=True)

# --- Model Architecture Definition ---
# This function MUST be identical to the one on the client.
def create_model_structure():
    """
    Creates and returns the Keras model with the same architecture as the trained one.
    """
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
        include_top=False,
        weights=None
    )
    base_model.trainable = True

    fine_tune_at = len(base_model.layers) - 30
    for layer in base_model.layers[:fine_tune_at]:
        layer.trainable = False

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3)),
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

    # We don't need to compile for aggregation, but it's good practice
    model.compile(loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

def run_federated_averaging():
    """
    Performs the federated averaging of all drone updates collected in the UPDATES_DIR.
    """
    print("--- Starting Monthly Federated Averaging ---")

    # 1. Find the most recent global model to use as a base
    existing_models = sorted([f for f in os.listdir(MODELS_DIR) if f.endswith('.weights.h5')])
    if not existing_models:
        print("No existing global model found. Creating initial model.")
        initial_model_path = os.path.join(MODELS_DIR, 'global_model_initial.weights.h5')
        initial_model = create_model_structure()
        initial_model.save_weights(initial_model_path)
        print(f"Created initial model at: {initial_model_path}")
        latest_global_model_path = initial_model_path
    else:
        latest_global_model_path = os.path.join(MODELS_DIR, existing_models[-1])
        print(f"Using latest global model as base: {latest_global_model_path}")

    # 2. Collect all weight updates from the updates directory
    all_updates = []
    total_samples = 0
    update_files = [f for f in os.listdir(UPDATES_DIR) if f.endswith('.weights.h5')]

    if not update_files:
        print("No new drone updates found to process. Exiting.")
        return

    print(f"Found {len(update_files)} updates to process.")

    for filename in update_files:
        try:
            parts = filename.split('_')
            num_samples = int(parts[0])

            temp_model = create_model_structure()
            temp_model.load_weights(os.path.join(UPDATES_DIR, filename))

            all_updates.append((temp_model.get_weights(), num_samples))
            total_samples += num_samples
        except Exception as e:
            print(f"Could not process file {filename}. Skipping. Error: {e}")

    if total_samples == 0:
        print("Total number of samples from updates is zero. Cannot average. Exiting.")
        return

    print(f"Aggregating weights from {len(all_updates)} clients, with a total of {total_samples} new samples.")

    # 3. Perform the weighted average (Federated Averaging)
    # Load the base model to get the structure for the new weights
    global_model = create_model_structure()
    global_model.load_weights(latest_global_model_path)
    base_weights = global_model.get_weights()

    # Initialize a list of numpy arrays with zeros, matching the model's layer shapes
    new_weights = [np.zeros_like(w) for w in base_weights]

    for client_weights, num_samples in all_updates:
        contribution = num_samples / total_samples
        for i in range(len(new_weights)):
            new_weights[i] += client_weights[i] * contribution

    # 4. Set the new averaged weights in the global model and save it
    global_model.set_weights(new_weights)

    timestamp = time.strftime("%Y-%m-%d")
    new_model_filename = os.path.join(MODELS_DIR, f'global_model_{timestamp}.weights.h5')

    global_model.save_weights(new_model_filename)
    print(f"--- Aggregation Complete ---")
    print(f"New global model saved as: {new_model_filename}")

    # 5. Optional: Archive processed updates
    archive_dir = os.path.join(UPDATES_DIR, f'processed_{timestamp}')
    os.makedirs(archive_dir, exist_ok=True)
    for filename in update_files:
        os.rename(os.path.join(UPDATES_DIR, filename), os.path.join(archive_dir, filename))
    print(f"Moved processed updates to {archive_dir}")


if __name__ == "__main__":
    run_federated_averaging()
