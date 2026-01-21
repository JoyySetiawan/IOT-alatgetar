import threading
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

# Import fungsi bot dari file bot.py
from bot import start_bot

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_loker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- KONFIGURASI KEAMANAN ---
API_KEY_SECRET = "MY_SECRET_API_KEY"

# --- TABEL USER ---
class Pengguna(db.Model):
    id_telegram = db.Column(db.String(50), primary_key=True) 
    nama_telegram = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='WHITELIST') 

# --- TABEL LOG RIWAYAT ---
class LogRiwayat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_telegram = db.Column(db.String(50), nullable=False)
    nama_telegram = db.Column(db.String(100), nullable=False)
    id_mesin = db.Column(db.String(50), nullable=False)
    waktu = db.Column(db.DateTime, default=datetime.now)

# --- STATUS PERANGKAT & ANTRIAN PERINTAH ---
status_perangkat = {
    "solenoid": "TERKUNCI",
    "getaran": "AMAN",
    "last_seen": "Belum Terhubung",
    "last_update_time": None,
    "is_online": False
}

command_queue = {
    "action": None 
}

OFFLINE_TIMEOUT = 15 

# --- FUNGSI BANTUAN ---
def update_last_seen():
    status_perangkat['last_update_time'] = datetime.now()
    status_perangkat['is_online'] = True
    status_perangkat['last_seen'] = datetime.now().strftime('%H:%M:%S')

def catat_log(id_tele, keterangan, mesin):
    try:
        log = LogRiwayat(id_telegram=id_tele, nama_telegram=keterangan, id_mesin=mesin)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error Log: {e}")

def check_pico_online():
    if status_perangkat['last_update_time'] is None:
        status_perangkat['is_online'] = False
        return
    time_diff = (datetime.now() - status_perangkat['last_update_time']).total_seconds()
    if time_diff > OFFLINE_TIMEOUT:
        status_perangkat['is_online'] = False
    else:
        status_perangkat['is_online'] = True

# --- ROUTE WEBSITE ---
@app.route('/')
def dashboard():
    data_user = Pengguna.query.all()
    data_log = LogRiwayat.query.order_by(LogRiwayat.waktu.desc()).limit(20).all()
    check_pico_online()
    return render_template('dashboard.html', users=data_user, logs=data_log, hardware=status_perangkat)

# --- [PERBAIKAN] ROUTE TOMBOL HARD OPEN/CLOSE ---
@app.route('/remote/<action>')
def remote_control(action):
    if action == 'BUKA':
        status_perangkat['solenoid'] = 'TERBUKA'
        command_queue['action'] = 'BUKA'
        catat_log("ADMIN WEB", "Membuka Pintu (Remote)", "Web-Dashboard")
    elif action == 'KUNCI':
        status_perangkat['solenoid'] = 'TERKUNCI'
        command_queue['action'] = 'KUNCI'
        catat_log("ADMIN WEB", "Mengunci Pintu (Remote)", "Web-Dashboard")
    return redirect(url_for('dashboard'))

# --- ROUTE API UNTUK BOT TELEGRAM ---
@app.route('/register', methods=['POST'])
def register_api():
    if request.headers.get('X-API-KEY') != API_KEY_SECRET:
        return jsonify({"message": "Akses Ditolak"}), 401
    
    data = request.get_json()
    id_tele = data.get('user_id')
    nama_tele = data.get('username')

    user = Pengguna.query.get(id_tele)
    if user:
        return jsonify({"message": "User sudah terdaftar"}), 409
    
    try:
        new_user = Pengguna(id_telegram=id_tele, nama_telegram=nama_tele, status='WHITELIST')
        db.session.add(new_user)
        db.session.commit()
        catat_log(id_tele, f"Register via Bot ({nama_tele})", "System")
        return jsonify({"message": "Registrasi Berhasil"}), 201
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/open', methods=['POST'])
def open_locker_api():
    if request.headers.get('X-API-KEY') != API_KEY_SECRET:
        return jsonify({"message": "Akses Ditolak"}), 401
    
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    
    user = Pengguna.query.get(user_id)
    if not user:
        return jsonify({"message": "ID Belum Terdaftar. Ketik /register di bot."}), 404
    
    if user.status != 'WHITELIST':
        return jsonify({"message": "ID Kamu DIBLOKIR"}), 403
    
    status_perangkat['solenoid'] = 'TERBUKA'
    command_queue['action'] = 'BUKA'
    catat_log(user_id, f"Buka via Bot ({username})", "Loker-Bot")
    
    return jsonify({"message": "Loker Berhasil Dibuka!"}), 200

@app.route('/close', methods=['POST'])
def close_locker_api():
    if request.headers.get('X-API-KEY') != API_KEY_SECRET:
        return jsonify({"message": "Akses Ditolak"}), 401
    
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')

    status_perangkat['solenoid'] = 'TERKUNCI'
    command_queue['action'] = 'KUNCI'
    catat_log(user_id, f"Tutup via Bot ({username})", "Loker-Bot")
    
    return jsonify({"message": "Loker Berhasil Dikunci!"}), 200

# --- API ALAT (PICO/ESP32) ---
@app.route('/api/get_command', methods=['GET'])
def get_command():
    update_last_seen()
    perintah = command_queue['action']
    command_queue['action'] = None 
    return jsonify({"command": perintah})

@app.route('/api/update_status', methods=['GET'])
def update_status():
    update_last_seen()
    alat = request.args.get('alat')
    status = request.args.get('status')
    
    if alat and status:
        if alat in status_perangkat:
            status_prev = status_perangkat[alat]
            status_perangkat[alat] = status
            
            if alat == 'getaran' and status == 'BAHAYA':
                catat_log("SENSOR", "⚠️ GETARAN MEMAKSA!", "Loker-Fisik")
            elif alat == 'solenoid' and status != status_prev:
                catat_log("SYSTEM", f"Pintu {status}", "Loker-Fisik")

        return jsonify({"msg": "OK"})
    return jsonify({"msg": "No Data"})

# --- MANAJEMEN USER ---
@app.route('/tambah_user', methods=['POST'])
def tambah_user():
    id_tele = request.form.get('id_tele')
    nama_tele = request.form.get('nama_tele')
    if not Pengguna.query.get(id_tele):
        db.session.add(Pengguna(id_telegram=id_tele, nama_telegram=nama_tele))
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/hapus_user/<id_tele>')
def hapus_user(id_tele):
    user = Pengguna.query.get(id_tele)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # 1. Jalankan Bot
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True 
    bot_thread.start()

    # 2. Jalankan Flask
    print("🚀 Menjalankan Server IoT + Bot Telegram...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)