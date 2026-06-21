import os
import sqlite3
import time
from threading import Lock
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'harbornet-secret-dev-key-9922')
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'harbornet.db')

# Prometheus Metrics Definition
REQUEST_COUNT = Counter(
    'harbornet_http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'harbornet_http_request_latency_seconds',
    'HTTP Request Latency',
    ['method', 'endpoint']
)
UPTIME_GAUGE = Gauge(
    'harbornet_uptime_seconds',
    'Application uptime in seconds'
)
ERROR_COUNT = Counter(
    'harbornet_errors_total',
    'Total number of application errors',
    ['method', 'endpoint', 'http_status']
)
ACTIVE_USERS = Gauge(
    'harbornet_active_users',
    'Number of active users in the last 5 minutes'
)
DB_QUERIES = Counter(
    'harbornet_db_queries_total',
    'Total number of database queries executed'
)

APP_START_TIME = time.time()
ACTIVE_USERS_TRACKER = {}  # user_id -> last_active_timestamp
tracker_lock = Lock()

# Custom sqlite3 Connection class to instrument query counting
class InstrumentedConnection(sqlite3.Connection):
    def execute(self, *args, **kwargs):
        DB_QUERIES.inc()
        return super().execute(*args, **kwargs)
        
    def executemany(self, *args, **kwargs):
        DB_QUERIES.inc()
        return super().executemany(*args, **kwargs)
        
    def executescript(self, *args, **kwargs):
        DB_QUERIES.inc()
        return super().executescript(*args, **kwargs)

def get_db_connection():
    conn = sqlite3.connect(DATABASE, factory=InstrumentedConnection)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vessels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vessel_name TEXT NOT NULL,
        imo_number TEXT UNIQUE NOT NULL,
        port_name TEXT NOT NULL,
        berth_number TEXT NOT NULL,
        cargo_type TEXT NOT NULL,
        status TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cargo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        container_id TEXT UNIQUE NOT NULL,
        vessel_name TEXT NOT NULL,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        current_location TEXT NOT NULL,
        status TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        container_id TEXT UNIQUE NOT NULL,
        clearance_status TEXT NOT NULL,
        officer_name TEXT NOT NULL,
        remarks TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        port_name TEXT UNIQUE NOT NULL,
        country TEXT NOT NULL,
        operational_status TEXT NOT NULL,
        congestion_level TEXT NOT NULL
    )
    ''')
    
    conn.commit()

    # Seed data if database is empty
    # Check users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        hashed_pw = generate_password_hash("admin123")
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                       ("admin", "admin@harbornet.org", hashed_pw))
    
    # Check ports
    cursor.execute("SELECT COUNT(*) FROM ports")
    if cursor.fetchone()[0] == 0:
        ports_data = [
            ("Port of Singapore", "Singapore", "Active", "Low"),
            ("Port of Rotterdam", "Netherlands", "Active", "Medium"),
            ("Port of Los Angeles", "United States", "Active", "High"),
            ("Port of Shanghai", "China", "Active", "Medium")
        ]
        cursor.executemany("INSERT INTO ports (port_name, country, operational_status, congestion_level) VALUES (?, ?, ?, ?)", ports_data)
        
    # Check vessels
    cursor.execute("SELECT COUNT(*) FROM vessels")
    if cursor.fetchone()[0] == 0:
        vessels_data = [
            ("Oceanic Voyager", "IMO 9876543", "Port of Singapore", "Berth A12", "Dry Bulk", "In Transit"),
            ("Pacific Explorer", "IMO 9765432", "Port of Los Angeles", "Berth B4", "Containers", "Docked"),
            ("Atlantic Vanguard", "IMO 9654321", "Port of Rotterdam", "Berth C1", "LNG Carrier", "Anchored")
        ]
        cursor.executemany("INSERT INTO vessels (vessel_name, imo_number, port_name, berth_number, cargo_type, status) VALUES (?, ?, ?, ?, ?, ?)", vessels_data)
        
    # Check cargo
    cursor.execute("SELECT COUNT(*) FROM cargo")
    if cursor.fetchone()[0] == 0:
        cargo_data = [
            ("CO-77812", "Oceanic Voyager", "Shanghai, CN", "Rotterdam, NL", "Indian Ocean", "In Transit"),
            ("CO-99214", "Pacific Explorer", "Singapore, SG", "Los Angeles, US", "Port of Los Angeles", "Loaded"),
            ("CO-55610", "Atlantic Vanguard", "Port of Rotterdam", "Hamburg, DE", "Port of Rotterdam", "Held")
        ]
        cursor.executemany("INSERT INTO cargo (container_id, vessel_name, origin, destination, current_location, status) VALUES (?, ?, ?, ?, ?, ?)", cargo_data)
        
    # Check customs
    cursor.execute("SELECT COUNT(*) FROM customs")
    if cursor.fetchone()[0] == 0:
        customs_data = [
            ("CO-77812", "Pending", "Officer Martinez", "Awaiting physical container inspection and seal validation."),
            ("CO-99214", "Cleared", "Officer Henderson", "Approved documentation matching manifest cargo description."),
            ("CO-55610", "Rejected", "Officer Davis", "Held due to missing dangerous goods licensing certificates.")
        ]
        cursor.executemany("INSERT INTO customs (container_id, clearance_status, officer_name, remarks) VALUES (?, ?, ?, ?)", customs_data)
        
    conn.commit()
    conn.close()

# Initialize DB on import/start
init_db()

# Middleware Hooks for Metrics Collection
@app.before_request
def before_request():
    g.start_time = time.time()
    if 'user_id' in session:
        user_id = session['user_id']
        with tracker_lock:
            ACTIVE_USERS_TRACKER[user_id] = time.time()

@app.after_request
def after_request(response):
    if request.path == '/metrics':
        return response
        
    latency = time.time() - g.get('start_time', time.time())
    endpoint = request.endpoint or 'unknown'
    method = request.method
    status = str(response.status_code)
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
    
    if response.status_code >= 500:
        ERROR_COUNT.labels(method=method, endpoint=endpoint, http_status=status).inc()
        
    return response

# Metrics Endpoint
@app.route('/metrics')
def metrics():
    # Update uptime gauge
    UPTIME_GAUGE.set(time.time() - APP_START_TIME)
    
    # Calculate active users (active in the last 5 minutes)
    now = time.time()
    with tracker_lock:
        inactive = [uid for uid, last_seen in ACTIVE_USERS_TRACKER.items() if now - last_seen > 300]
        for uid in inactive:
            del ACTIVE_USERS_TRACKER[uid]
        active_count = len(ACTIVE_USERS_TRACKER)
    ACTIVE_USERS.set(active_count)
    
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# Decorator/helper to protect routes
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Authorization required. Please authenticate.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Health check (unauthenticated)
@app.route('/health')
def health():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome back, Operator {username}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid operator credentials. Please retry.", "danger")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('signup.html')
            
        conn = get_db_connection()
        user_exists = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if user_exists:
            flash("Operator username already registered.", "danger")
            conn.close()
            return render_template('signup.html')
            
        hashed_pw = generate_password_hash(password)
        try:
            conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                         (username, email, hashed_pw))
            conn.commit()
            flash("Operator account registered successfully. Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error registering user: {str(e)}", "danger")
        finally:
            conn.close()
            
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Session terminated. Operator logged out.", "info")
    return redirect(url_for('login'))

# Core Dashboard
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    
    # Counts
    v_count = conn.execute("SELECT COUNT(*) FROM vessels").fetchone()[0]
    c_count = conn.execute("SELECT COUNT(*) FROM cargo WHERE status != 'Unloaded'").fetchone()[0]
    cu_count = conn.execute("SELECT COUNT(*) FROM customs WHERE clearance_status = 'Pending'").fetchone()[0]
    p_count = conn.execute("SELECT COUNT(*) FROM ports WHERE operational_status = 'Active'").fetchone()[0]
    
    # Generate system alerts dynamically
    system_alerts = []
    
    # Highly congested ports
    congested_ports = conn.execute("SELECT port_name, congestion_level FROM ports WHERE congestion_level = 'High'").fetchall()
    for port in congested_ports:
        system_alerts.append({
            "severity": "High",
            "target": port['port_name'],
            "message": f"Port is experiencing high traffic flow and container backlog.",
            "action_url": url_for('ports')
        })
        
    # Rejected customs declarations
    rejected_customs = conn.execute("SELECT container_id, officer_name, remarks FROM customs WHERE clearance_status = 'Rejected'").fetchall()
    for rc in rejected_customs:
        system_alerts.append({
            "severity": "Critical",
            "target": rc['container_id'],
            "message": f"Customs clearance REJECTED by {rc['officer_name']}: {rc['remarks']}",
            "action_url": url_for('customs')
        })
        
    # Pending customs declarations
    pending_customs = conn.execute("SELECT container_id, remarks FROM customs WHERE clearance_status = 'Pending'").fetchall()
    for pc in pending_customs:
        system_alerts.append({
            "severity": "Moderate",
            "target": pc['container_id'],
            "message": f"Awaiting review: {pc['remarks']}",
            "action_url": url_for('customs')
        })
        
    conn.close()
    
    return render_template('dashboard.html', 
                           vessels_count=v_count, 
                           cargo_count=c_count, 
                           customs_count=cu_count, 
                           ports_count=p_count,
                           system_alerts=system_alerts,
                           alerts_count=len(system_alerts))

# Vessels Registry Route
@app.route('/vessels', methods=['GET', 'POST'])
@login_required
def vessels():
    conn = get_db_connection()
    if request.method == 'POST':
        vessel_name = request.form['vessel_name']
        imo_number = request.form['imo_number']
        port_name = request.form['port_name']
        berth_number = request.form['berth_number']
        cargo_type = request.form['cargo_type']
        status = request.form['status']
        
        try:
            conn.execute("INSERT INTO vessels (vessel_name, imo_number, port_name, berth_number, cargo_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                         (vessel_name, imo_number, port_name, berth_number, cargo_type, status))
            conn.commit()
            flash(f"Vessel '{vessel_name}' registered successfully.", "success")
        except sqlite3.IntegrityError:
            flash(f"Error: A vessel with IMO number '{imo_number}' is already registered.", "danger")
        except Exception as e:
            flash(f"Database Error: {str(e)}", "danger")
            
        return redirect(url_for('vessels'))
        
    vessels_list = conn.execute("SELECT * FROM vessels ORDER BY vessel_name").fetchall()
    ports_list = conn.execute("SELECT port_name, country FROM ports WHERE operational_status = 'Active'").fetchall()
    conn.close()
    return render_template('vessels.html', vessels=vessels_list, ports=ports_list)

@app.route('/vessels/delete/<int:vessel_id>', methods=['POST'])
@login_required
def delete_vessel(vessel_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM vessels WHERE id = ?", (vessel_id,))
    conn.commit()
    conn.close()
    flash("Vessel de-registered from fleet index.", "info")
    return redirect(url_for('vessels'))

# Cargo Route
@app.route('/cargo', methods=['GET', 'POST'])
@login_required
def cargo():
    conn = get_db_connection()
    if request.method == 'POST':
        container_id = request.form['container_id']
        vessel_name = request.form['vessel_name']
        origin = request.form['origin']
        destination = request.form['destination']
        current_location = request.form['current_location']
        status = request.form['status']
        
        try:
            conn.execute("INSERT INTO cargo (container_id, vessel_name, origin, destination, current_location, status) VALUES (?, ?, ?, ?, ?, ?)",
                         (container_id, vessel_name, origin, destination, current_location, status))
            
            # Automatically create customs record as Pending when new cargo declared
            conn.execute("INSERT INTO customs (container_id, clearance_status, officer_name, remarks) VALUES (?, ?, ?, ?)",
                         (container_id, "Pending", "Unassigned", f"Automatic declaration logged. Awaiting routing from {origin} to {destination}."))
            
            conn.commit()
            flash(f"Container '{container_id}' logged and customs tracking initiated.", "success")
        except sqlite3.IntegrityError:
            flash(f"Error: Container '{container_id}' already exists in manifest database.", "danger")
        except Exception as e:
            flash(f"Database Error: {str(e)}", "danger")
            
        return redirect(url_for('cargo'))
        
    cargo_list = conn.execute("SELECT * FROM cargo ORDER BY container_id").fetchall()
    vessels_list = conn.execute("SELECT vessel_name, imo_number FROM vessels").fetchall()
    conn.close()
    return render_template('cargo.html', cargo=cargo_list, vessels=vessels_list)

@app.route('/cargo/delete/<int:cargo_id>', methods=['POST'])
@login_required
def delete_cargo(cargo_id):
    conn = get_db_connection()
    # Find container_id to clean up customs as well
    item = conn.execute("SELECT container_id FROM cargo WHERE id = ?", (cargo_id,)).fetchone()
    if item:
        container_id = item['container_id']
        conn.execute("DELETE FROM cargo WHERE id = ?", (cargo_id,))
        conn.execute("DELETE FROM customs WHERE container_id = ?", (container_id,))
        conn.commit()
        flash("Cargo unit removed and associated customs records deleted.", "info")
    conn.close()
    return redirect(url_for('cargo'))

# Customs Route
@app.route('/customs', methods=['GET', 'POST'])
@login_required
def customs():
    conn = get_db_connection()
    if request.method == 'POST':
        container_id = request.form['container_id']
        officer_name = request.form['officer_name']
        clearance_status = request.form['clearance_status']
        remarks = request.form['remarks']
        
        try:
            conn.execute("INSERT OR REPLACE INTO customs (container_id, clearance_status, officer_name, remarks) VALUES (?, ?, ?, ?)",
                         (container_id, clearance_status, officer_name, remarks))
            conn.commit()
            flash(f"Customs status for '{container_id}' updated manually.", "success")
        except Exception as e:
            flash(f"Database Error: {str(e)}", "danger")
            
        return redirect(url_for('customs'))
        
    customs_list = conn.execute("SELECT * FROM customs").fetchall()
    # List cargo containers to file declarations for
    cargo_list = conn.execute("SELECT container_id, vessel_name FROM cargo").fetchall()
    conn.close()
    return render_template('customs.html', customs=customs_list, cargo=cargo_list)

@app.route('/customs/update/<int:audit_id>/<string:status>', methods=['POST'])
@login_required
def update_customs(audit_id, status):
    conn = get_db_connection()
    officer = session.get('username', 'System Operator')
    
    # Retrieve current remarks to preserve them but note the status transition
    audit = conn.execute("SELECT * FROM customs WHERE id = ?", (audit_id,)).fetchone()
    if audit:
        container_id = audit['container_id']
        remarks = audit['remarks']
        
        # update customs record
        conn.execute("UPDATE customs SET clearance_status = ?, officer_name = ?, remarks = ? WHERE id = ?",
                     (status, officer, f"{remarks} (Updated to {status} by Operator {officer})", audit_id))
        
        # Sync back to cargo state if necessary (e.g. if rejected, hold cargo. if cleared, restore transit)
        cargo_status = "Held" if status == "Rejected" else "In Transit" if status == "Cleared" else "Loaded"
        conn.execute("UPDATE cargo SET status = ? WHERE container_id = ?", (cargo_status, container_id))
        
        conn.commit()
        flash(f"Container '{container_id}' status updated to '{status}'.", "success")
        
    conn.close()
    return redirect(url_for('customs'))

@app.route('/customs/delete/<int:audit_id>', methods=['POST'])
@login_required
def delete_customs(audit_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM customs WHERE id = ?", (audit_id,))
    conn.commit()
    conn.close()
    flash("Customs declaration removed from auditing index.", "info")
    return redirect(url_for('customs'))

# Ports Route
@app.route('/ports', methods=['GET', 'POST'])
@login_required
def ports():
    conn = get_db_connection()
    if request.method == 'POST':
        port_name = request.form['port_name']
        country = request.form['country']
        operational_status = request.form['operational_status']
        congestion_level = request.form['congestion_level']
        
        try:
            conn.execute("INSERT INTO ports (port_name, country, operational_status, congestion_level) VALUES (?, ?, ?, ?)",
                         (port_name, country, operational_status, congestion_level))
            conn.commit()
            flash(f"Port '{port_name}' registered successfully.", "success")
        except sqlite3.IntegrityError:
            flash(f"Error: Port '{port_name}' is already indexed in the global network.", "danger")
        except Exception as e:
            flash(f"Database Error: {str(e)}", "danger")
            
        return redirect(url_for('ports'))
        
    ports_list = conn.execute("SELECT * FROM ports ORDER BY port_name").fetchall()
    conn.close()
    return render_template('ports.html', ports=ports_list)

@app.route('/ports/delete/<int:port_id>', methods=['POST'])
@login_required
def delete_port(port_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM ports WHERE id = ?", (port_id,))
    conn.commit()
    conn.close()
    flash("Port de-indexed from global network.", "info")
    return redirect(url_for('ports'))

if __name__ == '__main__':
    # Flask runs on port 5001 for local and container consistency
    app.run(host='0.0.0.0', port=5001, debug=True)
