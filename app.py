from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_loker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 1. TABEL MEMBER (DAFTAR KARTU/PIN YANG BOLEH MASUK) ---
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    # kode_akses bisa berupa UID Kartu RFID (misal: "A1B2C3D4") atau PIN (misal: "1234")
    kode_akses = db.Column(db.String(50), unique=True, nullable=False) 
    status = db.Column(db.String(20), default='AKTIF') # AKTIF / BLOKIR

# --- 2. TABEL LOG RIWAYAT (SIAPA YANG BUKA PINTU) ---
class LogAkses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_member = db.Column(db.String(100), nullable=False)
    kode_akses = db.Column(db.String(50), nullable=False)
    status_akses = db.Column(db.String(20), nullable=False) # SUKSES / DITOLAK
    waktu = db.Column(db.DateTime, default=datetime.now)

# --- HALAMAN WEBSITE (KHUSUS ADMIN) ---

@app.route('/')
def dashboard():
    # Tampilkan Data Member & Log
    data_member = Member.query.all()
    data_log = LogAkses.query.order_by(LogAkses.waktu.desc()).limit(20).all()
    return render_template('dashboard.html', members=data_member, logs=data_log)

# --- CRUD MEMBER (ADMIN DAFTARKAN KARTU) ---

@app.route('/tambah_member', methods=['POST'])
def tambah_member():
    nama = request.form.get('nama')
    kode = request.form.get('kode') # UID RFID atau PIN
    
    # Cek duplikat
    cek = Member.query.filter_by(kode_akses=kode).first()
    if not cek:
        member_baru = Member(nama=nama, kode_akses=kode, status='AKTIF')
        db.session.add(member_baru)
        db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/hapus_member/<int:id_member>')
def hapus_member(id_member):
    member = Member.query.get(id_member)
    if member:
        db.session.delete(member)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/blokir_member/<int:id_member>')
def blokir_member(id_member):
    member = Member.query.get(id_member)
    if member:
        # Toggle Status
        if member.status == 'AKTIF':
            member.status = 'BLOKIR'
        else:
            member.status = 'AKTIF'
        db.session.commit()
    return redirect(url_for('dashboard'))

# --- API UNTUK ALAT (PICO W) ---
# Alat menembak link ini saat ada yang tempel kartu / ketik PIN
# Contoh: http://IP_LAPTOP:5000/api/cek_akses?kode=A1B2C3D4

@app.route('/api/cek_akses', methods=['GET'])
def cek_akses():
    kode_input = request.args.get('kode')
    
    # 1. Cari di Database
    member = Member.query.filter_by(kode_akses=kode_input).first()
    
    if member:
        if member.status == 'AKTIF':
            # IZINKAN MASUK
            catat_log(member.nama, kode_input, "SUKSES")
            return jsonify({"hasil": "IZIN", "nama": member.nama, "pesan": "Silakan Masuk"})
        else:
            # DITOLAK (DIBLOKIR)
            catat_log(member.nama, kode_input, "DITOLAK (BLOKIR)")
            return jsonify({"hasil": "TOLAK", "pesan": "Kartu Diblokir!"})
    else:
        # DITOLAK (TIDAK DIKENAL)
        catat_log("UNKNOWN", kode_input, "DITOLAK (INVALID)")
        return jsonify({"hasil": "TOLAK", "pesan": "Kartu Tidak Terdaftar"})

def catat_log(nama, kode, status):
    log = LogAkses(nama_member=nama, kode_akses=kode, status_akses=status)
    db.session.add(log)
    db.session.commit()

# --- JALANKAN SERVER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)