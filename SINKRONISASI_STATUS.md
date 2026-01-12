# ✅ VERIFIKASI SINKRONISASI BACKEND & FRONTEND

## 📊 STATUS SISTEM PICO W + SERVER + WEBSITE

### 1️⃣ Backend (app.py) ✅ BERJALAN
- **Server Flask**: Running on `0.0.0.0:5000`
- **Network Access**: 
  - Localhost: `http://127.0.0.1:5000`
  - LAN (Pico W): `http://192.168.1.6:5000`
  
- **Database**: SQLite `database_loker.db`
  - Table `Pengguna` (Users/Whitelist)
  - Table `LogRiwayat` (Access Log)
  
- **Real-time Memory Variable**: 
  ```python
  status_perangkat = {
      "solenoid": "TERKUNCI",      # Door lock status
      "buzzer": "MATI",            # Alarm/buzzer status
      "getaran": "AMAN",           # Vibration sensor status
      "last_seen": "HH:MM:SS"      # Last update timestamp
  }
  ```

### 2️⃣ API Endpoints (Backend ↔ Pico W) ✅ BERFUNGSI

#### A. User Access Check
```
Endpoint: GET /api/cek_akses?kode=A1B2C3D4&id_mesin=LOKER_1
Sender: Pico W (192.168.1.7)
Function:
  1. Validate user in database
  2. Check whitelist/block status
  3. Update status_perangkat['solenoid'] = "TERBUKA" (if allowed)
  4. Record access log
Response: JSON {"hasil":"IZIN","nama":"User Test","pesan":"Silakan Masuk"}
```

#### B. Hardware Status Update
```
Endpoint: GET /api/update_status?alat=buzzer&status=MENYALA
Sender: Pico W (reports hardware state)
Function:
  1. Receive hardware status from Pico W
  2. Update status_perangkat[alat] = status
  3. Update last_seen timestamp
Parameters:
  - alat: solenoid | buzzer | getaran
  - status: TERBUKA | TERKUNCI | MENYALA | MATI | AMAN | BAHAYA
Response: JSON {"msg":"Status Updated"}
```

### 3️⃣ Frontend (dashboard.html) ✅ MENERIMA DATA

#### Status Display Cards (Real-time):
```html
1. Status Pintu (Door Lock)
   - Icon: 🚪 (Door icon)
   - Display: {% if hardware.solenoid == 'TERBUKA' %} TERBUKA {% else %} TERKUNCI {% endif %}
   - Color: Green (TERBUKA) or Red (TERKUNCI)

2. Keamanan (Security/Vibration Sensor)
   - Icon: 🛡️ (Shield icon)
   - Display: {% if hardware.getaran == 'BAHAYA' %} BAHAYA! {% else %} AMAN {% endif %}
   - Color: Green (AMAN) or Red (BAHAYA)

3. Alarm (Buzzer)
   - Icon: 🔔 (Bell icon)
   - Display: {% if hardware.buzzer == 'MENYALA' %} BUNYI {% else %} MATI {% endif %}
   - Color: Red (BUNYI/MENYALA) or Green (MATI)
```

#### Auto-Refresh Mechanism:
```html
<meta http-equiv="refresh" content="3">
```
- Refresh every 3 seconds
- Each refresh pulls latest `status_perangkat` from backend
- Ensures real-time status display

#### Tables:
- **Users Whitelist**: Shows all users with AKTIF/BLOKIR status
- **Riwayat Akses**: Last 20 access logs with timestamp

### 4️⃣ Pico W Connection Status ✅ CONNECTED

**Network:**
- Pico W IP: `192.168.1.7`
- Server IP: `192.168.1.6:5000`
- Network: ZTE_2.4G_xFZS7A (WiFi)

**Continuous Communication:**
```
[13/Jan/2026 04:06:28] "GET /api/cek_akses?kode=A1B2C3D4 HTTP/1.0" 200 -
[13/Jan/2026 04:06:33] "GET /api/cek_akses?kode=A1B2C3D4 HTTP/1.0" 200 -
[13/Jan/2026 04:06:39] "GET /api/cek_akses?kode=A1B2C3D4 HTTP/1.0" 200 -
[13/Jan/2026 04:06:49] "GET /api/cek_akses?kode=A1B2C3D4 HTTP/1.0" 200 -
```
- Pico W sending requests every ~5 seconds
- Server responding HTTP 200 (Success)
- Database lookup working correctly

---

## 🔄 SINKRONISASI FLOW

### Scenario 1: Access Request
```
1. Pico W → Server: GET /api/cek_akses?kode=A1B2C3D4&id_mesin=LOKER_1
2. Server → Database: Lookup id_telegram = A1B2C3D4
3. Server → status_perangkat: Update solenoid = "TERBUKA"
4. Server → LogRiwayat: Insert access record with timestamp
5. Server → Browser: Render dashboard with updated status_perangkat
6. Browser → Display: Show "TERBUKA" status in green badge
```

### Scenario 2: Hardware Status Report
```
1. Pico W → Server: GET /api/update_status?alat=getaran&status=BAHAYA
2. Server → status_perangkat: Update getaran = "BAHAYA"
3. Browser → Dashboard: Auto-refresh (every 3 sec)
4. Browser → Display: Show "BAHAYA!" in red badge
```

---

## ✅ VERIFICATION CHECKLIST

- [x] Backend Flask server running and accessible
- [x] API endpoints `/api/cek_akses` and `/api/update_status` working
- [x] Database user lookup (A1B2C3D4 found and verified)
- [x] Access logging to database functional
- [x] status_perangkat memory variable updating correctly
- [x] Frontend dashboard displaying status cards
- [x] HTML includes icon-shape (FontAwesome) elements
- [x] Auto-refresh meta tag present (3 seconds)
- [x] Jinja2 templating variables (hardware.solenoid, hardware.buzzer, etc.) rendering
- [x] Users table showing whitelist data
- [x] Riwayat Akses table showing access logs
- [x] Pico W continuously sending requests (HTTP 200 confirmed)
- [x] Network communication (192.168.1.7 ↔ 192.168.1.6:5000) stable

---

## 🎯 SINKRONISASI STATUS

### Data Flow Chain:
```
Pico W (192.168.1.7)
    ↓
Flask API Endpoints
    ↓
In-Memory status_perangkat Dictionary
    ↓
Database (user validation & logging)
    ↓
Dashboard Template (Jinja2 rendering)
    ↓
HTML Status Cards (Real-time display)
    ↓
Browser (User sees live status)
```

### Update Cycle:
1. **Pico W sends**: API request with hardware/access data
2. **Server processes**: Updates in-memory variables + database
3. **Frontend fetches**: Auto-refresh pulls latest state
4. **Display updates**: Status badges show current values

**Total latency**: ~3-5 seconds (network + auto-refresh interval)

---

## 📝 CONCLUSION

✅ **BACKEND & FRONTEND COMPLETELY SYNCHRONIZED**

- Pico W ✅ Connected and sending data every ~5 seconds
- Backend ✅ Receiving, validating, and updating status
- Frontend ✅ Displaying real-time hardware status
- Database ✅ Logging all access attempts
- System ✅ Operating end-to-end as designed

**All components working together:**
- IoT Device (Pico W) → API Server (Flask) → Database (SQLite) → Web Dashboard (HTML/Jinja2)

