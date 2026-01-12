from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_loker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 1. TABEL USER (CRUD USER) ---
class Pengguna(db.Model):
    # ID Telegram dijadikan Primary Key (unik)
    id_telegram = db.Column(db.String(50), primary_key=True) 
    nama_telegram = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='WHITELIST') # WHITELIST / BLOKIR

# --- 2. TABEL LOG RIWAYAT (SESUAI REQUEST) ---
class LogRiwayat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_telegram = db.Column(db.String(50), nullable=False)
    nama_telegram = db.Column(db.String(100), nullable=False)
    id_mesin = db.Column(db.String(50), nullable=False)
    waktu = db.Column(db.DateTime, default=datetime.now)

# --- [BARU] MEMORI STATUS PERANGKAT (REAL-TIME) ---
# Ini menyimpan laporan terakhir dari Pico W
status_perangkat = {
    "solenoid": "TERKUNCI",    # Pintu
    "buzzer": "MATI",          # Alarm
    "getaran": "AMAN",         # Sensor SW420
    "last_seen": "Belum Terhubung", # Kapan terakhir Pico lapor
    "last_update_time": None,   # Timestamp terakhir update
    "is_online": False           # Status online/offline Pico W
}

# Timeout detection: Jika tidak ada update dalam X detik = OFFLINE
OFFLINE_TIMEOUT = 15  # 15 detik

# --- HALAMAN WEBSITE (ADMIN) ---

@app.route('/')
def dashboard():
    # Ambil data User & Log
    data_user = Pengguna.query.all()
    # Urutkan log dari yang terbaru
    data_log = LogRiwayat.query.order_by(LogRiwayat.waktu.desc()).limit(20).all()
    
    # Deteksi apakah Pico W masih online
    check_pico_online()
    
    # Kita kirim data 'status_perangkat' ke HTML juga
    return render_template('dashboard.html', users=data_user, logs=data_log, hardware=status_perangkat)

def check_pico_online():
    """Check apakah Pico W masih online berdasarkan last_update_time"""
    if status_perangkat['last_update_time'] is None:
        status_perangkat['is_online'] = False
        return
    
    time_diff = (datetime.now() - status_perangkat['last_update_time']).total_seconds()
    if time_diff > OFFLINE_TIMEOUT:
        status_perangkat['is_online'] = False
    else:
        status_perangkat['is_online'] = True

# --- CRUD USER (TAMBAH, HAPUS, BLOKIR) ---

@app.route('/tambah_user', methods=['POST'])
def tambah_user():
    id_tele = request.form.get('id_tele')
    nama_tele = request.form.get('nama_tele')
    
    # Cek apakah ID Tele sudah ada
    cek = Pengguna.query.get(id_tele)
    if not cek:
        user_baru = Pengguna(id_telegram=id_tele, nama_telegram=nama_tele, status='WHITELIST')
        db.session.add(user_baru)
        db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/hapus_user/<id_tele>')
def hapus_user(id_tele):
    user = Pengguna.query.get(id_tele)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/blokir_user/<id_tele>')
def blokir_user(id_tele):
    user = Pengguna.query.get(id_tele)
    if user:
        # Toggle Status
        if user.status == 'WHITELIST':
            user.status = 'BLOKIR'
        else:
            user.status = 'WHITELIST'
        db.session.commit()
    return redirect(url_for('dashboard'))

# --- API UNTUK ALAT (PICO W) ---
# Link: http://IP_LAPTOP:5000/api/cek_akses?kode=123456&id_mesin=LOKER_1

@app.route('/api/cek_akses', methods=['GET'])
def cek_akses():
    id_input = request.args.get('kode')  # Parameter dari Pico (sesuai nama yang dikirim)
    mesin_input = request.args.get('id_mesin') or "Loker-Utama"
    
    # UPDATE: Mark Pico as ONLINE
    status_perangkat['last_update_time'] = datetime.now()
    status_perangkat['is_online'] = True
    status_perangkat['last_seen'] = datetime.now().strftime('%H:%M:%S')
    
    # 1. Cari User di Database
    user = Pengguna.query.get(id_input)
    
    if user:
        if user.status == 'WHITELIST':
            # IZINKAN & CATAT LOG
            catat_log(user.id_telegram, user.nama_telegram, mesin_input)
            # Saat ada akses sukses, kita anggap pintu terbuka sebentar
            status_perangkat['solenoid'] = "TERBUKA"
            return jsonify({"hasil": "IZIN", "nama": user.nama_telegram, "pesan": "Silakan Masuk"})
        else:
            # DIBLOKIR
            status_perangkat['buzzer'] = "MENYALA" # Trigger alarm visual
            return jsonify({"hasil": "TOLAK", "pesan": "ID Anda Diblokir!"})
    else:
        # TIDAK TERDAFTAR
        status_perangkat['buzzer'] = "MENYALA"
        return jsonify({"hasil": "TOLAK", "pesan": "ID Tidak Terdaftar"})

# --- API 2: [BARU] PICO MELAPORKAN STATUS HARDWARE ---
# Pico menembak: /api/update_status?alat=getaran&status=BAHAYA
@app.route('/api/update_status', methods=['GET'])
def update_status():
    alat = request.args.get('alat')     # solenoid / buzzer / getaran
    status = request.args.get('status') # ON / OFF / BAHAYA / AMAN
    
    # UPDATE: Mark Pico as ONLINE
    status_perangkat['last_update_time'] = datetime.now()
    status_perangkat['is_online'] = True
    status_perangkat['last_seen'] = datetime.now().strftime('%H:%M:%S')
    
    if alat and status:
        # Update memori server
        if alat in status_perangkat:
            status_perangkat[alat] = status
        return jsonify({"msg": "Status Updated"})
    return jsonify({"msg": "No Data"})

def catat_log(id_tele, nama, mesin):
    log = LogRiwayat(id_telegram=id_tele, nama_telegram=nama, id_mesin=mesin)
    db.session.add(log)
    db.session.commit()

# --- JALANKAN SERVER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)