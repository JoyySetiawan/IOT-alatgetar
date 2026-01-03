from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data_iot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MEMBUAT MODEL (TABEL) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='staff')

class LogAlat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_alat = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False) 
    waktu = db.Column(db.DateTime, default=datetime.now) 

# --- RUTE WEBSITE (SEMUA TARUH DI SINI SEJAJAR) ---

@app.route('/')
def home():
    # Langsung ke Dashboard tanpa Login
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # 1. Ambil data User
    data_para_user = User.query.all()
    
    # 2. Ambil data Log Alat (Diurutkan dari yang paling baru)
    data_log_alat = LogAlat.query.order_by(LogAlat.waktu.desc()).all()
    
    # Kirim DUA data (users & logs) ke HTML
    return render_template('dashboard.html', users=data_para_user, logs=data_log_alat)

# --- SIMULASI ALAT IOT (Cara Pura-pura kirim data) ---
# Contoh link: http://IP_LAPTOP:5000/update_iot?nama=Pompa&status=ON
@app.route('/update_iot', methods=['GET'])
def update_iot():
    # Tangkap data dari link
    nama = request.args.get('nama')
    stat = request.args.get('status')
    
    if nama and stat:
        # Simpan ke Database
        log_baru = LogAlat(nama_alat=nama, status=stat)
        db.session.add(log_baru)
        db.session.commit()
        return f"Berhasil simpan: Alat {nama} statusnya {stat}"
    else:
        return "Gagal! Harus ada ?nama=...&status=..."

@app.route('/tambah_user', methods=['POST'])
def tambah_user():
    nama_baru = request.form.get('username')
    pass_baru = request.form.get('password')
    user_baru = User(username=nama_baru, password=pass_baru, role='staff')
    db.session.add(user_baru)
    db.session.commit() 
    return redirect(url_for('dashboard'))

# --- FITUR HAPUS USER (DELETE) ---
@app.route('/hapus_user/<int:id_user>')
def hapus_user(id_user):
    user_hapus = User.query.get(id_user)
    if user_hapus:
        db.session.delete(user_hapus)
        db.session.commit()
    return redirect(url_for('dashboard'))

# --- FITUR EDIT USER (UPDATE) ---
@app.route('/edit_user/<int:id_user>', methods=['GET', 'POST'])
def edit_user(id_user):
    user_edit = User.query.get(id_user)
    
    if request.method == 'POST':
        user_edit.username = request.form.get('username')
        user_edit.password = request.form.get('password')
        user_edit.role = request.form.get('role')
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('edit_user.html', user=user_edit)

# --- JALANKAN APLIKASI (PALING BAWAH) ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Bikin admin otomatis jika belum ada
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password='123', role='admin')
            db.session.add(admin)
            db.session.commit()
            print("User ADMIN berhasil dibuat otomatis!")

    # PERUBAHAN PENTING DI SINI:
    # host='0.0.0.0' artinya membuka akses ke seluruh jaringan Wi-Fi
    app.run(host='0.0.0.0', port=5000, debug=True)