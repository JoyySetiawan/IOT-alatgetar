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

# --- HALAMAN WEBSITE (ADMIN) ---

@app.route('/')
def dashboard():
    # Ambil data User & Log
    data_user = Pengguna.query.all()
    # Urutkan log dari yang terbaru
    data_log = LogRiwayat.query.order_by(LogRiwayat.waktu.desc()).limit(20).all()
    return render_template('dashboard.html', users=data_user, logs=data_log)

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
# Link: http://IP_LAPTOP:5000/api/akses?id_tele=123456&id_mesin=LOKER_1

@app.route('/api/akses', methods=['GET'])
def cek_akses():
    id_input = request.args.get('id_tele')
    mesin_input = request.args.get('id_mesin') or "Loker-Utama"
    
    # 1. Cari User di Database
    user = Pengguna.query.get(id_input)
    
    if user:
        if user.status == 'WHITELIST':
            # IZINKAN & CATAT LOG
            catat_log(user.id_telegram, user.nama_telegram, mesin_input)
            return jsonify({"hasil": "IZIN", "nama": user.nama_telegram, "pesan": "Silakan Masuk"})
        else:
            # DIBLOKIR
            return jsonify({"hasil": "TOLAK", "pesan": "ID Anda Diblokir!"})
    else:
        # TIDAK TERDAFTAR
        return jsonify({"hasil": "TOLAK", "pesan": "ID Tidak Terdaftar"})

def catat_log(id_tele, nama, mesin):
    log = LogRiwayat(id_telegram=id_tele, nama_telegram=nama, id_mesin=mesin)
    db.session.add(log)
    db.session.commit()

# --- JALANKAN SERVER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)