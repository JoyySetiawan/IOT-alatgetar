from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data_iot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODEL DATABASE (HANYA LOG ALAT) ---
class LogAlat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_alat = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False) 
    waktu = db.Column(db.DateTime, default=datetime.now) 

# --- STATUS MEMORI (UNTUK INTEGRASI BOT / ALAT) ---
# Menyimpan status terakhir agar alat tahu harus ngapain (Buka/Tutup)
perintah_alat = {
    "solenoid": "LOCKED", 
    "buzzer": "OFF"
}

# --- RUTE WEBSITE ---

@app.route('/')
def home():
    # Langsung masuk ke dashboard log
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Ambil data log, urutkan dari yang terbaru
    data_log_alat = LogAlat.query.order_by(LogAlat.waktu.desc()).all()
    
    # Tampilkan halaman monitoring
    return render_template('dashboard.html', logs=data_log_alat)

# --- API UTAMA (KOMUNIKASI DENGAN ALAT) ---
# Raspberry Pi Pico W menembak link ini
@app.route('/update_iot', methods=['GET'])
def update_iot():
    # 1. TERIMA DATA (Simpan ke Log)
    nama = request.args.get('nama')
    stat = request.args.get('status')
    
    if nama and stat:
        log_baru = LogAlat(nama_alat=nama, status=stat)
        db.session.add(log_baru)
        db.session.commit()
        
        # 2. KIRIM BALASAN STATUS (JSON)
        # Alat membaca balasan ini untuk mengontrol Solenoid/Buzzer
        return jsonify(perintah_alat)
    
    else:
        return jsonify(perintah_alat)

# --- API KHUSUS TELEGRAM BOT (OPSIONAL) ---
# Link ini bisa dipakai Bot Telegram Bagas untuk mengubah status
@app.route('/api_telegram', methods=['GET'])
def api_telegram():
    alat = request.args.get('alat') # solenoid / buzzer
    aksi = request.args.get('aksi') # OPEN / LOCKED / ON / OFF
    
    if alat in perintah_alat and aksi:
        perintah_alat[alat] = aksi
        return f"Berhasil: {alat} diubah jadi {aksi}"
    return "Gagal."

# --- JALANKAN SERVER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Buat tabel log otomatis
            
    # Host 0.0.0.0 agar bisa diakses dari jaringan Wi-Fi
    app.run(host='0.0.0.0', port=5000, debug=True)