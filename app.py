from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
from datetime import datetime
import serial
import requests
import threading
import time
import os

# ============== CONFIG ==============
ARDUINO_PORT = 'COM4'
BAUD_RATE = 9600

# ============== FLASK SETUP ==============
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============== DATABASE ==============
DB_FILE = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS alerts 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lat REAL,
                     lon REAL,
                     time TEXT,
                     status TEXT,
                     device_id TEXT)''')
    conn.close()

init_db()

# ============== GET LAPTOP LOCATION ==============
def get_location():
    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        data = response.json()
        if data['status'] == 'success':
            return {
                'latitude': data['lat'],
                'longitude': data['lon'],
                'city': data.get('city', 'Unknown'),
                'country': data.get('country', 'Unknown')
            }
    except Exception as e:
        print(f"Location fetch error: {e}")
    
    return {
        'latitude': 30.3753,
        'longitude': 69.3451,
        'city': 'Default',
        'country': 'Pakistan'
    }

# ============== PROCESS ALERT (FIXED) ==============
def process_sos_alert(is_sos=True):
    location = get_location()
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    device_id = 'Arduino-Nano-Laptop'
    status = 'SOS ACTIVE' if is_sos else 'Tracking'
    
    # Save to database
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO alerts (lat, lon, time, status, device_id) VALUES (?, ?, ?, ?, ?)",
        (location['latitude'], location['longitude'], time_now, status, device_id),
    )
    conn.commit()
    conn.close()
    
    event_payload = {
        'lat': location['latitude'],
        'lon': location['longitude'],
        'time': time_now,
        'status': status,
        'device_id': device_id,
        'is_sos': is_sos,
        'city': location.get('city', ''),
        'country': location.get('country', ''),
        'message': '🚨 WOMEN SAFETY ALERT! Emergency Button Pressed!' if is_sos else 'Live tracking update',
    }
    
    # ✅ FIX: Simple emit without broadcast parameter
    socketio.emit('new_alert', event_payload)
    socketio.emit('location_update', event_payload)
    
    print(f"\n{'='*50}")
    print(f"🚨 ALERT SENT TO DASHBOARD!")
    print(f"📍 Location: {location['city']}, {location['country']}")
    print(f"   Lat: {location['latitude']}, Lon: {location['longitude']}")
    print(f"{'='*50}\n")

# ============== ARDUINO READER THREAD ==============
def arduino_reader():
    print("🔌 Connecting to Arduino...")
    
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"✅ Connected to {ARDUINO_PORT}")
    except Exception as e:
        print(f"❌ Failed to connect to Arduino: {e}")
        return

    print("🚀 Waiting for SOS button press...\n")
    
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"Serial: {line}")
                
                if line == "SOS_TRIGGER":
                    print("🚨 SOS TRIGGERED FROM ARDUINO!")
                    process_sos_alert(is_sos=True)
                    
                elif line == "SOS_OFF":
                    print("🛑 SOS turned off\n")
                    
        except Exception as e:
            print(f"Arduino read error: {e}")
            time.sleep(1)

# ============== FLASK ROUTES ==============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/alert', methods=['POST'])
def receive_alert():
    try:
        data = request.get_json() or {}
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        device_id = data.get('device_id', 'unknown-device')
        is_sos = bool(data.get('is_sos', True))
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        status = 'SOS ACTIVE' if is_sos else 'Tracking'
        conn = sqlite3.connect(DB_FILE)
        conn.execute(
            "INSERT INTO alerts (lat, lon, time, status, device_id) VALUES (?, ?, ?, ?, ?)",
            (lat, lon, time_now, status, device_id),
        )
        conn.commit()
        conn.close()
        
        event_payload = {
            'lat': lat,
            'lon': lon,
            'time': time_now,
            'status': status,
            'device_id': device_id,
            'is_sos': is_sos,
            'message': '🚨 WOMEN SAFETY ALERT! Emergency Button Pressed!' if is_sos else 'Live tracking update',
        }

        socketio.emit('new_alert', event_payload)
        socketio.emit('location_update', event_payload)
        
        return jsonify({"status": "success", "message": "Alert received"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/alerts/recent', methods=['GET'])
def get_recent_alerts():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.execute(
        "SELECT lat, lon, time, status, device_id FROM alerts ORDER BY id DESC LIMIT 20"
    )
    rows = cursor.fetchall()
    conn.close()

    payload = [
        {'lat': row[0], 'lon': row[1], 'time': row[2], 'status': row[3], 'device_id': row[4] or '-'}
        for row in rows
    ]
    return jsonify(payload)

@socketio.on('connect')
def handle_connect():
    print("✅ Dashboard client connected")

# ============== MAIN ==============
if __name__ == '__main__':
    # Start Arduino reader in background thread
    arduino_thread = threading.Thread(target=arduino_reader, daemon=True)
    arduino_thread.start()
    
    print("\n🌐 Starting Flask server...")
    print("📱 Open browser: http://127.0.0.1:5000")
    print("🔘 Press Arduino button to trigger SOS\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)