from flask import Flask, request, jsonify
import os
import werkzeug

app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'drone_updates'
# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload_weights', methods=['POST'])
def upload_weights():
    """
    API endpoint for drones to upload their updated .h5 weight files.
    """
    # Check if the post request has the file part
    if 'weights' not in request.files:
        return jsonify({"error": "No weights file found in the request"}), 400

    file = request.files['weights']

    # If the user does not select a file, the browser submits an empty file without a filename.
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.h5'):
        try:
            # Get metadata
            num_samples = int(request.form.get('num_samples', 0))

            # Sanitize filename to prevent security issues
            base_filename = werkzeug.utils.secure_filename(file.filename)

            # Prepend metadata to the filename for easy parsing by the aggregator
            # Format: <num_samples>_<original_filename>
            save_filename = f"{num_samples}_{base_filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)

            file.save(save_path)

            print(f"Received and saved weights: {save_filename} (trained on {num_samples} samples)")
            return jsonify({"message": f"Weights received successfully: {save_filename}"}), 200
        except Exception as e:
            return jsonify({"error": f"An error occurred on the server: {e}"}), 500
    else:
        return jsonify({"error": "Invalid file type. Only .h5 files are accepted."}), 400

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "Server is running"}), 200


if __name__ == '__main__':
    # Run the server to be accessible on the local network
    # Use 0.0.0.0 to listen on all available network interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)
