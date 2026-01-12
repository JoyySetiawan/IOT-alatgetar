# 🔴 OFFLINE DETECTION SYSTEM

## Cara Kerja Sistem Offline Detection Pico W

Sistem sekarang dapat mendeteksi ketika Pico W terputus dari jaringan dan menampilkan status **OFFLINE** pada dashboard.

### 1️⃣ BACKEND (app.py) - Timeout Detection

**Konfigurasi:**
```python
# Timeout dalam detik - jika tidak ada update > 15 detik = OFFLINE
OFFLINE_TIMEOUT = 15

status_perangkat = {
    "last_update_time": None,    # Timestamp terakhir update dari Pico
    "is_online": False            # Status koneksi Pico W
}
```

**Logic Detection:**
```python
def check_pico_online():
    """Check apakah Pico W masih online"""
    if status_perangkat['last_update_time'] is None:
        status_perangkat['is_online'] = False
        return
    
    time_diff = (datetime.now() - status_perangkat['last_update_time']).total_seconds()
    if time_diff > OFFLINE_TIMEOUT:
        status_perangkat['is_online'] = False
    else:
        status_perangkat['is_online'] = True
```

**Flow:**
1. Pico W mengirim API request → `last_update_time` di-update ke waktu sekarang
2. Dashboard auto-refresh setiap 3 detik → `check_pico_online()` dipanggil
3. Jika > 15 detik tanpa update → Status berubah ke OFFLINE
4. Frontend menampilkan "🔴 OFFLINE" di status cards

---

### 2️⃣ FRONTEND (dashboard.html) - Visual Indicators

**CSS Styling untuk OFFLINE:**
```css
.status-offline {
    background: linear-gradient(87deg, #999 0, #666 100%) !important;
    color: white;
}

.blink-offline {
    animation: blink-offline 1s infinite;
}

@keyframes blink-offline {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0.5; }
}
```

**Status Card Berubah Menjadi:**
- ✅ **ONLINE**: Menampilkan status hardware real-time (TERBUKA/TERKUNCI/BAHAYA/AMAN/MENYALA/MATI)
- ❌ **OFFLINE**: 
  - Menampilkan "🔴 OFFLINE" di 3 status cards (merah)
  - Icon berubah warna abu-abu
  - Card berkedip lambat (blinking animation)
  - Badge di bawah "Last Seen" menunjukkan "OFFLINE"

**Template Jinja2:**
```html
{% if not hardware.is_online %}
    <span class="h2 font-weight-bold mb-0 text-danger">
        🔴 OFFLINE
    </span>
    <div class="icon-shape status-offline">
        <i class="fas fa-door-open"></i>
    </div>
    <span class="badge bg-danger">OFFLINE</span>
{% else %}
    <!-- Tampilkan status normal -->
{% endif %}
```

---

### 3️⃣ PERUBAHAN YANG DILAKUKAN

#### app.py (Backend):
✅ Tambah field ke `status_perangkat`:
- `last_update_time`: Tracking timestamp update terakhir
- `is_online`: Boolean status online/offline

✅ Tambah timeout constant:
- `OFFLINE_TIMEOUT = 15` (detik)

✅ Tambah function `check_pico_online()`:
- Dipanggil setiap kali dashboard di-refresh
- Hitung time difference antara sekarang dan last_update
- Update is_online berdasarkan threshold

✅ Update semua API endpoint:
- `/api/cek_akses`: Set last_update_time & is_online = True
- `/api/update_status`: Set last_update_time & is_online = True

#### dashboard.html (Frontend):
✅ Tambah CSS untuk styling OFFLINE:
- `.status-offline`: Warna abu-abu gradient
- `.blink-offline`: Animasi berkedip

✅ Update 3 status cards:
- Kondisional render: jika offline tampilkan "🔴 OFFLINE"
- Icon berubah warna abu-abu
- Badge "OFFLINE" di bawah Last Seen

✅ Auto-refresh (sudah ada):
- Refresh setiap 3 detik → detection bekerja otomatis

---

### 4️⃣ TIMELINE OFFLINE DETECTION

**Skenario: Pico W Diputus Jaringan**

```
t=0s    : Pico W terputus (tidak kirim request lagi)
t=1s    : Dashboard refresh #1 → is_online = True (masih di cache)
t=3s    : Dashboard refresh #2 → is_online = True
t=5s    : Dashboard refresh #3 → time_diff = 5s → MASIH ONLINE
t=10s   : Dashboard refresh #4 → time_diff = 10s → MASIH ONLINE
t=15s   : Dashboard refresh #5 → time_diff = 15s → MASIH ONLINE
t=18s   : Dashboard refresh #6 → time_diff = 18s > 15s → ⛔ OFFLINE!
```

**Hasil:**
- ~18 detik setelah Pico terputus → sistem deteksi OFFLINE
- Dashboard menampilkan "🔴 OFFLINE" di 3 status cards
- Cards berkedip dan berwarna abu-abu

---

### 5️⃣ TESTING OFFLINE DETECTION

**Cara Test:**

1. **Pico masih terhubung:**
   - Buka dashboard di `http://localhost:5000`
   - Lihat 3 status cards menampilkan status hardware (TERBUKA, AMAN, MATI, dll)
   - Badge menunjukkan "ONLINE"
   - Last Seen update terus

2. **Putus Pico dari jaringan:**
   - Disconnect Pico W dari WiFi
   - Tunggu 15-18 detik
   - Dashboard refresh otomatis
   - Status berubah menjadi:
     ```
     🔴 OFFLINE
     🔴 OFFLINE
     🔴 OFFLINE
     ```
   - Cards berkedip (blinking animation)
   - Icons berubah warna abu-abu

3. **Hubungkan Pico kembali:**
   - Reconnect Pico W ke WiFi
   - Pico kirim API request lagi
   - `last_update_time` di-update
   - Dashboard refresh → `is_online = True`
   - Status berubah kembali normal

---

### 6️⃣ KONFIGURASI

**Ubah timeout jika diperlukan:**

```python
# Dalam app.py, ubah nilai ini:
OFFLINE_TIMEOUT = 15  # Detik

# Opsi:
OFFLINE_TIMEOUT = 10  # Detect lebih cepat
OFFLINE_TIMEOUT = 20  # Lebih toleran dengan lag
OFFLINE_TIMEOUT = 30  # Sangat toleran
```

**Ubah auto-refresh interval:**

```html
<!-- Dalam dashboard.html -->
<meta http-equiv="refresh" content="3">

<!-- Ubah ke detik yang diinginkan: -->
<meta http-equiv="refresh" content="5">   <!-- 5 detik -->
<meta http-equiv="refresh" content="2">   <!-- 2 detik -->
```

---

### 7️⃣ MONITORING

**Server Log saat OFFLINE:**
```
127.0.0.1 - - [13/Jan/2026 04:06:31] "GET / HTTP/1.1" 200 -
(no more requests dari 192.168.1.7)
(dashboard refresh dari localhost terus, tapi Pico offline)
127.0.0.1 - - [13/Jan/2026 04:06:34] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [13/Jan/2026 04:06:37] "GET / HTTP/1.1" 200 -
(masih tidak ada request dari Pico)
```

---

## ✅ KESIMPULAN

**Sistem Offline Detection Selesai:**
- ✅ Backend tracking last update timestamp
- ✅ Timeout detection dengan threshold 15 detik
- ✅ Frontend menampilkan visual indicator OFFLINE
- ✅ Animation & styling untuk kemudahan identifikasi
- ✅ Auto-refresh setiap 3 detik
- ✅ Support reconnect (otomatis kembali ONLINE saat Pico reconnect)

**User Experience:**
- Jelas kapan Pico W offline vs online
- Tidak ada data stale (update timestamp selalu terpantau)
- Visual feedback yang obvious (🔴, warna abu-abu, blinking)
- Timeout dapat dikonfigurasi sesuai kebutuhan

