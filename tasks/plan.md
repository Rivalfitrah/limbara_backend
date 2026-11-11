# Implementation Plan: Auth Security Hardening

## Overview

Memperketat autentikasi Limbara tanpa verifikasi email: registrasi manual tidak lagi membuat sesi, Google OAuth tetap dapat langsung masuk, sesi dibatasi maksimal 24 jam dan idle 2 jam, satu akun maksimal memiliki tiga sesi aktif, serta percobaan autentikasi dibatasi secara persisten. Pekerjaan juga mencakup bind mount khusus development agar perubahan kode Python dapat ter-reload tanpa rebuild image.

Plan ini tidak membaca atau mengubah nilai rahasia pada `.env`. Build frontend juga tidak dijalankan sesuai aturan proyek.

## Temuan Audit Saat Ini

- `POST /api/auth/register` langsung membuat session cookie; ini bertentangan dengan alur yang telah disepakati.
- Sesi saat ini berlaku 7 hari dan belum memiliki idle timeout maupun batas jumlah sesi aktif.
- Login/register belum memiliki rate limit yang persisten.
- Google ID token saat ini dibaca menggunakan unverified claims. Klaim tersebut belum diverifikasi terhadap signature Google, audience, issuer, dan expiry.
- OAuth `state` ditandatangani, tetapi nonce belum dikirim ke Google dan belum dicocokkan dengan ID token; state juga belum ditandai sekali pakai.
- Legacy JWT cookie masih dapat digunakan sebagai fallback autentikasi.
- Password sudah memakai Argon2id dan session token hanya disimpan dalam bentuk hash; fondasi ini dipertahankan.

## Architecture Decisions

- **Registrasi manual tidak autentikatif.** Respons `201` hanya menyatakan akun berhasil dibuat; tidak ada session cookie dan `last_login_at` tetap `NULL`. Frontend mengarahkan pengguna ke `/login?registered=1`.
- **Google OAuth tetap autentikatif.** Callback boleh membuat sesi setelah token diverifikasi secara kriptografis.
- **Verifikasi token Google memakai library resmi.** Gunakan `google-auth` untuk memeriksa signature, `aud`, `iss`, dan `exp`; `sub` tetap menjadi identitas provider utama. Google secara resmi menyarankan library klien dan validasi token server-side: [Google backend authentication](https://developers.google.com/identity/sign-in/web/backend-auth) dan [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect).
- **OAuth state dan nonce sekali pakai.** Simpan hash state dalam database dengan expiry dan `used_at`; kirim nonce ke Google lalu cocokkan dengan klaim token terverifikasi. Callback yang replay atau tidak cocok ditolak.
- **Rate limiting berbasis PostgreSQL.** Gunakan bucket unik yang di-claim/update secara atomik, bukan memory process. Identifier email/IP disimpan sebagai HMAC, bukan nilai mentah. Login dibatasi per akun dan per IP; register dan awal OAuth dibatasi per IP.
- **HMAC limiter memakai derived key.** Turunkan sub-key berlabel `auth-rate-limit-v1` dari secret server yang sudah diwajibkan, sehingga tidak memerlukan secret baru dan tidak menggunakan secret mentah langsung untuk identifier.
- **Kebijakan sesi server-side.** Absolute timeout 24 jam, idle timeout 2 jam, dan maksimal tiga sesi aktif. Saat sesi keempat dibuat, sesi aktif paling lama dicabut di dalam transaksi yang mengunci user terkait.
- **Password berbasis panjang, bukan aturan komposisi rumit.** Minimal 12 dan maksimal 128 karakter, tetap mendukung password manager/paste, dan menolak daftar password yang sangat umum. Ini mengikuti rekomendasi panjang dan blocklist OWASP: [Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
- **Cookie tetap opaque dan HttpOnly.** Pertahankan `Secure`, `HttpOnly`, `__Host-` saat HTTPS, serta origin check untuk request yang mengubah state. Idle dan absolute timeout ditegakkan server-side sesuai [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet).
- **Legacy JWT fallback dihapus.** Setelah perubahan ini pengguna dengan cookie lama harus login ulang. Cookie legacy tetap dibersihkan saat login/logout agar transisi eksplisit.
- **Development override terpisah.** Tambahkan `docker-compose.override.yml` yang hanya memasang direktori source/migration/test dan menjalankan Uvicorn `--reload`. Perubahan dependency atau Dockerfile tetap memerlukan rebuild.

## Threat Model Ringkas

| Batas kepercayaan | Risiko utama | Kontrol yang direncanakan |
|---|---|---|
| Form login/register → API | brute force, credential stuffing, enumeration | schema validation, error generik, rate limit email/IP, Argon2id dummy verification |
| Browser cookie → session store | pencurian/replay sesi, sesi tidak berakhir | opaque token hash, Secure/HttpOnly/SameSite, idle + absolute timeout, revoke |
| Google → callback backend | token palsu, login CSRF, callback replay | signature/audience/issuer/expiry verification, one-time state, nonce |
| Proxy/client IP → limiter | spoofed forwarded header, penyimpanan PII | hanya percaya proxy yang dikonfigurasi, HMAC identifier, tanpa IP mentah |
| Database auth | race pada limiter/sesi keempat | unique constraint, transaction/row lock, pengujian concurrent intent |

## API Contract

### `POST /api/auth/register`

- Input tetap: `email`, `name`, `password`.
- Output `201`:

```json
{
  "message": "Akun berhasil dibuat. Silakan masuk."
}
```

- Tidak mengirim `Set-Cookie` session.
- Duplicate account tetap memakai pesan generik.
- Rate limit: `429` dengan pesan generik dan `Retry-After`.

### `POST /api/auth/login`

- Output sukses tetap `AuthenticatedUser` dan session cookie baru.
- Password/email salah, user nonaktif, atau provider tidak sesuai tetap menghasilkan pesan generik yang sama.
- Rate limit menghasilkan `429`; keberhasilan mereset bucket akun yang relevan.
- Pembuatan sesi baru menjaga maksimal tiga sesi aktif.

### `GET /api/auth/google/login`

- Membuat state dan nonce sekali pakai.
- Menyetel cookie korelasi sementara yang HttpOnly, Secure sesuai environment, SameSite Lax, dan berumur maksimal 10 menit.
- Rate limit per IP sebelum redirect.

### `GET /api/auth/google/callback`

- Mencocokkan state, cookie korelasi, record state belum dipakai, dan nonce ID token.
- Memverifikasi token Google dengan library resmi sebelum membaca `sub`/email/profile.
- State ditandai terpakai secara atomik dan cookie sementara selalu dibersihkan.
- Sukses membuat sesi dengan kebijakan 24 jam/2 jam/maksimal 3 sesi.

### Endpoint session yang sudah ada

- `GET /api/auth/me`: menolak sesi revoked, absolute expired, atau idle expired.
- `POST /api/auth/logout`: mencabut sesi aktif dan membersihkan cookie.
- `POST /api/auth/logout-all`: mencabut seluruh sesi akun.

## Task List

### Phase 0: Development Workflow

- [x] Task 1: Tambahkan Docker development override dan Docker ignore hygiene.

### Phase 1: Manual Registration and Password Boundary

- [x] Task 2: Ubah kontrak register agar tidak membuat sesi.
- [x] Task 3: Sesuaikan frontend register agar kembali ke halaman login.
- [x] Task 4: Perketat validasi password dan pertahankan error generik.

### Checkpoint: Manual Auth

- [x] Register tidak membuat sesi dan frontend mengarahkan ke login.
- [x] Login manual tetap berhasil memakai Argon2id.
- [x] Tes focused backend dan frontend lulus.

### Phase 2: Persistent Security State

- [x] Task 5: Tambahkan migration/model untuk rate-limit bucket dan OAuth state.
- [x] Task 6: Terapkan rate limiting persisten pada register/login/OAuth start.
- [x] Task 7: Terapkan timeout sesi dan batas tiga sesi aktif.

### Checkpoint: Abuse Resistance

- [x] Percobaan berlebih diblokir menggunakan state database.
- [x] Sesi idle/absolute expired ditolak dan sesi keempat mencabut sesi tertua.
- [x] Tidak ada email, IP mentah, token, atau password dalam log/tabel limiter.

### Phase 3: Google OAuth Verification

- [x] Task 8: Ganti unverified claims dengan verifikasi Google resmi.
- [x] Task 9: Terapkan one-time state, nonce, dan cookie korelasi OAuth.

### Checkpoint: OAuth

- [x] Token dengan signature/audience/issuer/expiry/nonce salah ditolak.
- [x] Callback replay ditolak.
- [x] Google OAuth valid tetap langsung login.

### Phase 4: Cleanup and Defense in Depth

- [x] Task 10: Hapus legacy JWT fallback dan tambahkan header keamanan API yang aman.
- [x] Task 11: Tambahkan event log autentikasi yang tidak memuat data sensitif.
- [x] Task 12: Jalankan regression suite dan pemeriksaan runtime end-to-end yang dapat diotomasi.

### Checkpoint: Complete

- [x] Seluruh acceptance criteria implementasi terpenuhi; login Google nyata perlu spot-check pengguna.
- [x] Backend tests dan frontend typecheck/lint file terkait lulus.
- [x] Tidak menjalankan frontend production build.
- [x] Siap direview sebelum implementasi keamanan lanjutan (email verification/2FA/reset password).

## Risks and Mitigations

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Rate limiter salah mengunci pengguna sah | Sedang | bucket terpisah akun/IP, TTL pendek, `Retry-After`, tes boundary |
| Header proxy dipalsukan | Tinggi | gunakan direct client IP kecuali trusted proxy secara eksplisit dikonfigurasi |
| Race membuat lebih dari tiga sesi | Sedang | row lock user dan revoke sesi tertua dalam transaksi yang sama |
| Google login rusak akibat validasi lebih ketat | Tinggi | contract tests untuk token valid/invalid dan mock key verification sebelum integrasi manual |
| Cookie cross-site production gagal | Tinggi | pertahankan kebijakan Secure/SameSite berbasis environment dan origin allowlist eksplisit |
| User lama masih memakai legacy cookie | Rendah | force re-login sekali dan hapus cookie legacy secara eksplisit |
| Bind mount menutupi file container | Sedang | mount hanya source/migration/test, bukan seluruh `/app`; rebuild tetap wajib saat dependency berubah |

## Open Questions Deferred

- Verifikasi email, reset password, 2FA, CAPTCHA, device-management UI, dan breach-password API berada di luar scope tahap ini.
- Kebijakan retention untuk event log autentikasi ditetapkan singkat (usulan 30 hari) dan dapat disesuaikan sebelum produksi.

