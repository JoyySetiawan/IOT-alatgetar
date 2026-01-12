from app import app, db, Pengguna

# Jalankan dalam app context
with app.app_context():
    # Buat tabel
    db.create_all()
    
    # Cek apakah sudah ada data
    existing = Pengguna.query.first()
    
    if not existing:
        # Tambah user test dengan kartu ID: A1B2C3D4
        user_test = Pengguna(id_telegram='A1B2C3D4', nama_telegram='User Test', status='WHITELIST')
        db.session.add(user_test)
        db.session.commit()
        print("✓ Database sudah disetup!")
        print("✓ Ditambah user: A1B2C3D4 (User Test) dengan status WHITELIST")
    else:
        print("✓ Database sudah ada data")
    
    # Tampilkan semua user
    print("\nData user yang tersedia:")
    all_users = Pengguna.query.all()
    for user in all_users:
        print(f"  - {user.id_telegram} | {user.nama_telegram} | Status: {user.status}")
