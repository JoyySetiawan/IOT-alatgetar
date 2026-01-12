"""
TEST MANUAL API - IoT Smart Locker System
Untuk testing API tanpa perlu Pico W
"""

import requests
import json
from datetime import datetime

# Konfigurasi
SERVER_URL = "http://localhost:5000"
HEADERS = {"Content-Type": "application/json"}

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_api_cek_akses():
    """Test API untuk cek akses kartu"""
    print_section("TEST 1: API CEK AKSES (/api/cek_akses)")
    
    test_cases = [
        {"kode": "A1B2C3D4", "desc": "Kartu Valid (Whitelist)"},
        {"kode": "INVALID123", "desc": "Kartu Tidak Terdaftar"},
    ]
    
    for case in test_cases:
        try:
            url = f"{SERVER_URL}/api/cek_akses?kode={case['kode']}&id_mesin=LOKER_1"
            print(f"📤 Test: {case['desc']}")
            print(f"   URL: {url}")
            
            response = requests.get(url, timeout=5)
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            print(f"   ✓ OK\n")
            
        except Exception as e:
            print(f"   ✗ ERROR: {str(e)}\n")

def test_api_update_status():
    """Test API untuk update status hardware"""
    print_section("TEST 2: API UPDATE STATUS (/api/update_status)")
    
    test_cases = [
        {"alat": "solenoid", "status": "TERBUKA", "desc": "Pintu Terbuka"},
        {"alat": "solenoid", "status": "TERKUNCI", "desc": "Pintu Terkunci"},
        {"alat": "buzzer", "status": "MENYALA", "desc": "Buzzer Menyala"},
        {"alat": "buzzer", "status": "MATI", "desc": "Buzzer Mati"},
        {"alat": "getaran", "status": "BAHAYA", "desc": "Sensor Getaran: BAHAYA"},
        {"alat": "getaran", "status": "AMAN", "desc": "Sensor Getaran: AMAN"},
    ]
    
    for case in test_cases:
        try:
            url = f"{SERVER_URL}/api/update_status?alat={case['alat']}&status={case['status']}"
            print(f"📤 Test: {case['desc']}")
            print(f"   URL: {url}")
            
            response = requests.get(url, timeout=5)
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            print(f"   ✓ OK\n")
            
        except Exception as e:
            print(f"   ✗ ERROR: {str(e)}\n")

def test_dashboard():
    """Test Dashboard HTML"""
    print_section("TEST 3: DASHBOARD (/)")
    
    try:
        url = f"{SERVER_URL}/"
        print(f"📤 Mengakses Dashboard...")
        print(f"   URL: {url}")
        
        response = requests.get(url, timeout=5)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Cek beberapa elemen penting di HTML
            checks = [
                ("STATUS PERANGKAT" in response.text, "Panel Status Perangkat"),
                ("CRUD User" in response.text, "CRUD User Section"),
                ("Log Riwayat" in response.text, "Log Riwayat Section"),
                ("IoT Control Center" in response.text, "Navbar Title"),
            ]
            
            for check, name in checks:
                status = "✓" if check else "✗"
                print(f"   {status} {name}")
            
            print(f"\n   ✓ OK - Dashboard dapat diakses\n")
        else:
            print(f"   ✗ ERROR - Status code bukan 200\n")
            
    except Exception as e:
        print(f"   ✗ ERROR: {str(e)}\n")

def test_database():
    """Test akses database melalui API"""
    print_section("TEST 4: DATABASE (Cek User & Log)")
    
    try:
        # Buat user baru untuk test
        url = f"{SERVER_URL}/tambah_user"
        data = {
            'id_tele': 'TEST_USER_001',
            'nama_tele': 'User Test Manual'
        }
        
        print(f"📤 Tambah User Test...")
        response = requests.post(url, data=data, timeout=5)
        print(f"   Status Code: {response.status_code}")
        print(f"   ✓ OK - User test ditambahkan\n")
        
        # Cek dashboard untuk melihat user baru
        url = f"{SERVER_URL}/"
        response = requests.get(url, timeout=5)
        
        if "User Test Manual" in response.text:
            print(f"✓ Verifikasi - User test muncul di dashboard\n")
        else:
            print(f"✗ Verifikasi - User test TIDAK muncul di dashboard\n")
            
    except Exception as e:
        print(f"   ✗ ERROR: {str(e)}\n")

def test_koneksi():
    """Test koneksi ke server"""
    print_section("TEST 0: KONEKSI SERVER")
    
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"✓ Server ONLINE - {SERVER_URL}")
            print(f"✓ Response Time OK\n")
            return True
        else:
            print(f"✗ Server merespons tapi ada error: {response.status_code}\n")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ TIDAK BISA CONNECT ke {SERVER_URL}")
        print(f"✗ Pastikan Flask server sudah running!\n")
        return False
    except Exception as e:
        print(f"✗ ERROR: {str(e)}\n")
        return False

def main():
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  TEST MANUAL - IoT Smart Locker System".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "═"*58 + "╝")
    print(f"\nServer: {SERVER_URL}")
    print(f"Waktu: {datetime.now().strftime('%H:%M:%S | %d-%m-%Y')}")
    
    # Test koneksi dulu
    if not test_koneksi():
        print("\n❌ TEST DIBATALKAN - Server tidak bisa diakses")
        return
    
    # Jalankan semua test
    test_api_cek_akses()
    test_api_update_status()
    test_dashboard()
    test_database()
    
    # Summary
    print_section("SUMMARY")
    print("✓ Semua test selesai dijalankan!")
    print("✓ Buka browser: http://localhost:5000 untuk lihat dashboard")
    print("✓ Refresh browser untuk melihat update status real-time")
    print("\n")

if __name__ == "__main__":
    main()
