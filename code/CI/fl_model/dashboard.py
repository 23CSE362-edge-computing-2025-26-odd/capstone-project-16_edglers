from flask import Flask, render_template_string
import os
import time

app = Flask(__name__)

# --- Configuration ---
UPDATES_DIR = 'drone_updates'
MODELS_DIR = 'global_models'

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Dashboard</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

    body {
        font-family: 'Roboto', sans-serif;
        background: linear-gradient(to right, #e0eafc, #cfdef3);
        margin: 0;
        padding: 20px;
        color: #333;
    }
    h1 {
        text-align: center;
        font-size: 2.5em;
        color: #0d47a1;
        margin-bottom: 40px;
    }
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }
    .card {
        background: #fff;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        text-align: center;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(0,0,0,0.25);
    }
    .card h2 {
        margin: 0 0 15px 0;
        font-size: 1.4em;
        color: #0d47a1;
        border-bottom: 2px solid #0d47a1;
        display: inline-block;
        padding-bottom: 3px;
    }
    .card .value {
        font-size: 2em;
        font-weight: bold;
        margin-top: 10px;
        color: #333;
    }
    .badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1em;
        color: #fff;
        margin-top: 10px;
    }
    .green { background: #28a745; }
    .orange { background: #fd7e14; }
    .red { background: #dc3545; }
    ul { padding-left: 20px; margin: 0; max-height: 200px; overflow-y: auto; text-align: left; }
    li { margin-bottom: 8px; font-size: 1em; }
    .progress-container { background: #ddd; border-radius: 15px; overflow: hidden; height: 25px; margin-top: 10px; }
    .progress-bar { background: #0d47a1; height: 100%; width: 0%; text-align: center; color: #fff; font-size: 14px; line-height: 25px; transition: width 0.5s ease; }
    footer { text-align: center; margin-top: 50px; color: #555; font-size: 0.9em; }
</style>
<meta http-equiv="refresh" content="5">
</head>
<body>
<h1AI Dashboard</h1>

<div class="dashboard-grid">
    <div class="card">
        <h2>Pending Updates</h2>
        <div class="value"><span class="badge {{ badge_color }}">{{ pending_count }}</span></div>
    </div>
    <div class="card">
        <h2>Total Updates Processed</h2>
        <div class="value">{{ total_processed }}</div>
    </div>
    <div class="card">
        <h2>Total Drones Participated</h2>
        <div class="value">{{ total_drones }}</div>
    </div>
    <div class="card">
        <h2>Last Aggregation</h2>
        <div class="value">{{ last_update_time if last_update_time else 'N/A' }}</div>
    </div>
</div>

<div class="card">
    <h2>Pending Drone Updates</h2>
    {% if pending_files %}
    <ul>
        {% for f in pending_files %}
        <li>📦 {{ f }}</li>
        {% endfor %}
    </ul>
    <div class="progress-container">
        <div class="progress-bar" style="width: {{ progress_percent }}%;">{{ progress_percent }}%</div>
    </div>
    {% else %}
    <p>No pending updates! 🎉</p>
    {% endif %}
</div>

<footer>
    ⚡ Auto-refreshes every 5 seconds | Developed with Flask & Python
</footer>
</body>
</html>
"""

@app.route('/')
def dashboard():
    # Pending updates
    pending_files = [f for f in os.listdir(UPDATES_DIR) if f.endswith('.weights.h5')]
    pending_count = len(pending_files)
    
    # Total processed
    processed_dirs = [d for d in os.listdir(UPDATES_DIR) if d.startswith('processed_')]
    total_processed = sum(len(os.listdir(os.path.join(UPDATES_DIR, d))) for d in processed_dirs)
    
    # Total drones (unique drone IDs from filenames)
    drone_ids = set()
    for f in pending_files:
        drone_ids.add(f.split('_')[1])
    for d in processed_dirs:
        for f in os.listdir(os.path.join(UPDATES_DIR, d)):
            drone_ids.add(f.split('_')[1])
    total_drones = len(drone_ids)
    
    # Last aggregation time
    global_models = sorted([f for f in os.listdir(MODELS_DIR) if f.endswith('.weights.h5')])
    if global_models:
        last_update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(os.path.join(MODELS_DIR, global_models[-1]))))
    else:
        last_update_time = None
    
    # Progress %
    total_updates = total_processed + pending_count
    progress_percent = int((total_processed / total_updates) * 100) if total_updates > 0 else 0
    
    # Badge color
    if pending_count == 0:
        badge_color = 'green'
    elif pending_count < 5:
        badge_color = 'orange'
    else:
        badge_color = 'red'
    
    return render_template_string(HTML_TEMPLATE,
                                  pending_files=pending_files,
                                  pending_count=pending_count,
                                  total_processed=total_processed,
                                  total_drones=total_drones,
                                  last_update_time=last_update_time,
                                  progress_percent=progress_percent,
                                  badge_color=badge_color)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

