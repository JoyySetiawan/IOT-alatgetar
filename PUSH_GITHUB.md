# 📤 PANDUAN PUSH KE GITHUB

## Langkah 1: Buat Repository di GitHub

1. Buka https://github.com/new
2. Isi nama repository: `iot-alatgetar`
3. Deskripsi: `Smart Locker IoT System - Pico W + Flask + Dashboard`
4. Pilih: Public (agar bisa dilihat)
5. **JANGAN** centang "Initialize this repository with a README"
6. Klik "Create repository"

GitHub akan menampilkan instruksi. Anda akan mendapat URL seperti:
```
https://github.com/username/iot-alatgetar.git
```

## Langkah 2: Connect Local Repository ke GitHub

Copy-paste salah satu perintah di bawah ke terminal:

### Option A: HTTPS (Lebih mudah untuk pemula)
```bash
cd c:\Users\Asus\Downloads\iot-alatgetar
git remote add origin https://github.com/USERNAME/iot-alatgetar.git
git branch -M main
git push -u origin main
```

### Option B: SSH (Jika sudah setup SSH key)
```bash
cd c:\Users\Asus\Downloads\iot-alatgetar
git remote add origin git@github.com:USERNAME/iot-alatgetar.git
git branch -M main
git push -u origin main
```

## Langkah 3: Ganti USERNAME

Replace `USERNAME` dengan username GitHub Anda. Contoh:
```bash
# ❌ SALAH:
git remote add origin https://github.com/USERNAME/iot-alatgetar.git

# ✅ BENAR:
git remote add origin https://github.com/kelompok9/iot-alatgetar.git
```

## Langkah 4: Push ke GitHub

Setelah menjalankan perintah di atas, akan ada prompt:
```
Username for 'https://github.com': your-username
Password for 'https://your-username@github.com': 
```

**PENTING:** Jika menggunakan password, gunakan **Personal Access Token** bukan password biasa.

### Membuat Personal Access Token:
1. GitHub Settings → Developer settings → Personal access tokens
2. Generate new token
3. Pilih scope: `repo` (full control)
4. Copy token dan paste saat diminta password

Atau gunakan GitHub CLI:
```bash
gh auth login
```

## Quick Command (Semuanya dalam satu baris)

```bash
cd c:\Users\Asus\Downloads\iot-alatgetar && git remote add origin https://github.com/USERNAME/iot-alatgetar.git && git branch -M main && git push -u origin main
```

## Verifikasi Push Berhasil

1. Buka https://github.com/USERNAME/iot-alatgetar
2. Lihat apakah files sudah ter-upload
3. Check commit history

## Push Update Selanjutnya (Lebih Mudah)

Setelah push pertama, update selanjutnya cukup:
```bash
git add .
git commit -m "Deskripsi perubahan"
git push
```

## Status Current Repository

```
Repository: iot-alatgetar
Branch: main
Commits: 2 (ready to push)
Files:
  - app.py (Flask backend)
  - setup_db.py
  - test_manual.py
  - test_sync.py
  - templates/dashboard.html
  - OFFLINE_DETECTION.md
  - SINKRONISASI_STATUS.md
  - README.md
  - .gitignore
```

## ✅ Checklist Push

- [ ] GitHub account siap
- [ ] Repository dibuat di GitHub
- [ ] USERNAME sudah diketahui
- [ ] Personal Access Token dibuat (jika HTTPS)
- [ ] Perintah git remote ditjalankan
- [ ] Push berhasil
- [ ] Files terlihat di GitHub

## 🆘 Troubleshooting

### Error: "Permission denied (publickey)"
→ Gunakan HTTPS instead of SSH

### Error: "fatal: remote origin already exists"
→ Jalankan: `git remote rm origin` lalu retry

### Error: "Authentication failed"
→ Gunakan Personal Access Token, bukan password

### Push stuck/slow
→ Abaikan venv folder dengan .gitignore sudah ada

---

**Siap untuk push? Beri tahu USERNAME GitHub Anda!**
