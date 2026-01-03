from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data_iot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODEL DATABASE (LOG RIWAYAT) ---
class LogAlat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_alat = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False) 
    waktu = db.Column(db.DateTime, default=datetime.now) 

# --- [UPGRADE] MEMORI STATUS 6 PERANGKAT (REAL-TIME) ---
# Menyimpan status terkini agar bisa ditampilkan di kartu Dashboard
status_terkini = {
    "solenoid": "LOCKED",       # Kunci Pintu (LOCKED / OPEN)
    "magnet": "TERTUTUP",       # Sensor Pintu Fisik (TERTUTUP / TERBUKA)
    "paket": "KOSONG",          # Sensor IR (ADA / KOSONG)
    "keamanan": "AMAN",         # Sensor Getar (AMAN / BAHAYA)
    "rfid": "-",                # ID Kartu Terakhir
    "buzzer": "OFF"             # Alarm (ON / OFF)
}

# --- PERINTAH KONTROL (UNTUK ALAT) ---
perintah_alat = {
    "solenoid": "LOCKED", 
    "buzzer": "OFF"
}

# --- RUTE WEBSITE ---

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Ambil 20 log terakhir saja biar loading cepat
    data_log_alat = LogAlat.query.order_by(LogAlat.waktu.desc()).limit(20).all()
    # Kirim Log DAN Status Terkini ke HTML
    return render_template('dashboard.html', logs=data_log_alat, status=status_terkini)

# --- API UTAMA (UPDATE DARI ALAT) ---
@app.route('/update_iot', methods=['GET'])
def update_iot():
    nama = request.args.get('nama')   # Contoh: solenoid, magnet, ir, rfid, getar
    stat = request.args.get('status') # Contoh: OPEN, TERBUKA, ADA, 12345, BAHAYA
    
    if nama and stat:
        # 1. Simpan Log (Sejarah)
        log_baru = LogAlat(nama_alat=nama, status=stat)
        db.session.add(log_baru)
        db.session.commit()
        
        # 2. Update Status Visual (Real-time) sesuai nama alat
        nama_kecil = nama.lower()
        
        if 'solenoid' in nama_kecil:       # Update Status Kunci
            status_terkini['solenoid'] = stat
            perintah_alat['solenoid'] = 'LOCKED' if stat == 'LOCKED' else 'OPEN'
            
        elif 'magnet' in nama_kecil:       # Update Status Pintu Fisik
            status_terkini['magnet'] = stat
            
        elif 'ir' in nama_kecil or 'paket' in nama_kecil: # Update Paket
            status_terkini['paket'] = stat
            
        elif 'rfid' in nama_kecil:         # Update Siapa yang akses terakhir
            status_terkini['rfid'] = stat
            
        elif 'getar' in nama_kecil:        # Update Keamanan
            status_terkini['keamanan'] = stat
            # Logika Otomatis: Ada Getaran -> Nyalakan Buzzer
            if 'BAHAYA' in stat or 'ALERT' in stat:
                perintah_alat['buzzer'] = 'ON'
                status_terkini['buzzer'] = 'ON'
            else:
                perintah_alat['buzzer'] = 'OFF'
                status_terkini['buzzer'] = 'OFF'
                
        elif 'buzzer' in nama_kecil:       # Update Status Buzzer
             status_terkini['buzzer'] = stat
             perintah_alat['buzzer'] = stat

        return jsonify(perintah_alat)
    
    else:
        return jsonify(perintah_alat)

# --- API TELEGRAM (OPSIONAL) ---
@app.route('/api_telegram', methods=['GET'])
def api_telegram():
    alat = request.args.get('alat') 
    aksi = request.args.get('aksi')
    
    if alat in perintah_alat and aksi:
        perintah_alat[alat] = aksi
        # Update visual dashboard juga
        if alat in status_terkini:
            status_terkini[alat] = aksi
        return f"Berhasil: {alat} -> {aksi}"
    return "Gagal."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)