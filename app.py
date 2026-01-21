from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_loker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

# [BARU] Variabel untuk menyimpan perintah Remote Control
command_queue = {
    "action": None  # Isinya nanti 'BUKA' atau 'KUNCI'
}

OFFLINE_TIMEOUT = 15 # Detik (Sudah diperbaiki)

# --- HALAMAN DASHBOARD ---
@app.route('/')
def dashboard():
    data_user = Pengguna.query.all()
    data_log = LogRiwayat.query.order_by(LogRiwayat.waktu.desc()).limit(20).all()
    check_pico_online()
    return render_template('dashboard.html', users=data_user, logs=data_log, hardware=status_perangkat)

def check_pico_online():
    if status_perangkat['last_update_time'] is None:
        status_perangkat['is_online'] = False
        return
    time_diff = (datetime.now() - status_perangkat['last_update_time']).total_seconds()
    if time_diff > OFFLINE_TIMEOUT:
        status_perangkat['is_online'] = False
    else:
        status_perangkat['is_online'] = True

# --- [BARU] ROUTE UNTUK TOMBOL REMOTE DI WEBSITE ---
@app.route('/remote/<action>')
def remote_control(action):
    # Simpan perintah ke antrian agar diambil oleh Pico
    command_queue['action'] = action
    
    # Update status visual sementara
    if action == 'BUKA':
        status_perangkat['solenoid'] = 'TERBUKA'
        catat_log("ADMIN WEB", "Membuka Pintu (Remote)", "Web-Dashboard")
    elif action == 'KUNCI':
        status_perangkat['solenoid'] = 'TERKUNCI'
        catat_log("ADMIN WEB", "Mengunci Pintu (Remote)", "Web-Dashboard")
        
    return redirect(url_for('dashboard'))

# --- [BARU] API UNTUK PICO MENGAMBIL PERINTAH ---
@app.route('/api/get_command', methods=['GET'])
def get_command():
    update_last_seen()
    
    # Ambil perintah saat ini
    perintah = command_queue['action']
    
    # Kosongkan antrian setelah diambil (agar tidak dieksekusi berulang)
    command_queue['action'] = None 
    
    return jsonify({"command": perintah})

# --- API 1: CEK AKSES (PIN BENAR / SALAH) ---
@app.route('/api/cek_akses', methods=['GET'])
def cek_akses():
    update_last_seen()
    
    id_input = request.args.get('kode')
    mesin_input = request.args.get('id_mesin') or "Loker-Utama"
    
    user = Pengguna.query.get(id_input)
    
    if user:
        if user.status == 'WHITELIST':
            # 1. PIN BENAR
            catat_log(user.id_telegram, "PIN BENAR", mesin_input)
            status_perangkat['solenoid'] = "TERBUKA"
            return jsonify({"hasil": "IZIN", "nama": user.nama_telegram, "pesan": "Silakan Masuk"})
        else:
            # 2. PIN SALAH (DIBLOKIR)
            catat_log(user.id_telegram, "PIN SALAH (BLOKIR)", mesin_input)
            return jsonify({"hasil": "TOLAK", "pesan": "ID Diblokir"})
    else:
        # 3. PIN SALAH (TIDAK TERDAFTAR)
        catat_log(id_input, "PIN SALAH (UNKNOWN)", mesin_input)
        return jsonify({"hasil": "TOLAK", "pesan": "ID Tidak Dikenal"})

# --- API 2: UPDATE STATUS (PINTU & GETARAN) ---
@app.route('/api/update_status', methods=['GET'])
def update_status():
    update_last_seen()
    
    alat = request.args.get('alat')
    status = request.args.get('status')
    
    if alat and status:
        if alat in status_perangkat:
            status_sebelumnya = status_perangkat[alat]
            status_perangkat[alat] = status

            # --- LOGIKA PENCATATAN RIWAYAT ---
            if alat == 'solenoid' and status != status_sebelumnya:
                if status == 'TERKUNCI':
                    catat_log("SYSTEM", "Pintu Terkunci", "Loker-Utama")
                elif status == 'TERBUKA':
                    catat_log("SYSTEM", "Pintu Terbuka", "Loker-Utama")
            
            elif alat == 'getaran' and status == 'BAHAYA':
                catat_log("SENSOR", "Terdeteksi Getaran Memaksa!", "Loker-Utama")

        return jsonify({"msg": "OK"})
    return jsonify({"msg": "No Data"})

# --- FUNGSI BANTUAN ---
def update_last_seen():
    status_perangkat['last_update_time'] = datetime.now()
    status_perangkat['is_online'] = True
    status_perangkat['last_seen'] = datetime.now().strftime('%H:%M:%S')

def catat_log(id_tele, keterangan, mesin):
    log = LogRiwayat(id_telegram=id_tele, nama_telegram=keterangan, id_mesin=mesin)
    db.session.add(log)
    db.session.commit()

# --- CRUD USER STANDARD ---
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
    # Pastikan host='0.0.0.0' agar bisa diakses dari luar localhost
    app.run(host='0.0.0.0', port=5000, debug=True)