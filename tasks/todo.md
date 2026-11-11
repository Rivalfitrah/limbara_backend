# Auth Security Hardening Tasks

## Task 1: Docker Development Override

**Description:** Tambahkan override development yang memasang source Python, migration, dan tests sebagai bind mount serta menjalankan Uvicorn reload tanpa mengubah konfigurasi production.

**Acceptance criteria:**
- [ ] Perubahan file Python terbaca tanpa rebuild image.
- [ ] Perubahan `requirements.txt`/Dockerfile tetap terdokumentasi memerlukan rebuild.
- [ ] `.env` dan secret tidak masuk build context atau version control.

**Verification:**
- [ ] `docker compose config` menunjukkan mount development yang sempit.
- [ ] Route baru muncul setelah reload tanpa `docker compose build`.

**Dependencies:** None

**Files likely touched:** `docker-compose.override.yml`, `.dockerignore`

**Estimated scope:** Small

## Task 2: Register Without Session

**Description:** Ubah registrasi manual agar hanya membuat akun dan mengarahkan pengguna untuk login, tanpa membuat cookie atau mencatat login.

**Acceptance criteria:**
- [ ] Respons register tidak memiliki session cookie.
- [ ] `last_login_at` tetap kosong setelah register.
- [ ] Frontend menampilkan sukses lalu menuju `/login`.

**Verification:**
- [ ] Backend route/service tests.
- [ ] Frontend utility/component lint dan typecheck.

**Dependencies:** None

**Files likely touched:** `app/routes/auth_route.py`, `app/services/auth_service.py`, `app/schemas/auth.py`, `tests/test_auth_routes.py`

**Estimated scope:** Medium

## Task 3: Frontend Register-to-Login Flow

**Description:** Sesuaikan kontrak API frontend dan halaman register agar keberhasilan registrasi mengarah ke login dengan notifikasi aman, bukan menganggap pengguna sudah memiliki sesi.

**Acceptance criteria:**
- [ ] API client memakai response registrasi baru.
- [ ] Register sukses menuju `/login?registered=1` dan login menampilkan pesan sukses non-sensitif.
- [ ] Navbar/current-user tetap dalam kondisi logout sampai login berhasil.

**Verification:**
- [ ] Frontend typecheck, targeted ESLint, dan auth utility tests.

**Dependencies:** Task 2

**Files likely touched:** `../limbara/src/app/service/api.ts`, `../limbara/src/app/register/page.tsx`, `../limbara/src/app/login/page.tsx`, `../limbara/src/utils/auth.test.mjs`

**Estimated scope:** Medium

## Task 4: Password and Generic Error Policy

**Description:** Naikkan batas minimal password menjadi 12 karakter, tambahkan common-password blocklist lokal, dan pastikan seluruh kegagalan kredensial tetap tidak mengungkap keberadaan akun/provider.

**Acceptance criteria:**
- [ ] Password lemah/umum ditolak pada boundary schema.
- [ ] Password manager dan paste tetap didukung tanpa aturan komposisi arbitrer.
- [ ] Respons login salah tetap identik untuk semua kondisi akun.

**Verification:**
- [ ] Security schema/service tests mencakup boundary 11/12/128/129 karakter.

**Dependencies:** Task 2

**Files likely touched:** `app/schemas/auth.py`, `app/services/auth_service.py`, `tests/test_auth_security.py`, `tests/test_auth_service.py`

**Estimated scope:** Medium

## Task 5: Persistent Auth Security Models

**Description:** Tambahkan tabel rate-limit bucket dan OAuth state sekali pakai, termasuk constraint/index/expiry yang diperlukan.

**Acceptance criteria:**
- [ ] Bucket mempunyai unique key atomik per action+identifier+window.
- [ ] OAuth state hanya menyimpan hash, expiry, dan waktu pemakaian.
- [ ] Migration upgrade teruji pada PostgreSQL.

**Verification:**
- [ ] Model tests dan Alembic upgrade pada database test/development.

**Dependencies:** None

**Files likely touched:** `alembic/versions/0007_auth_security_hardening.py`, `app/models/auth_rate_limit.py`, `app/models/oauth_login_state.py`, `app/models/__init__.py`, `tests/test_auth_models.py`

**Estimated scope:** Medium

## Task 6: Database-backed Rate Limiting

**Description:** Terapkan limiter persisten untuk login, register, dan awal Google OAuth menggunakan identifier HMAC dan update atomik.

**Acceptance criteria:**
- [ ] Login dibatasi per akun dan per IP.
- [ ] Register/OAuth start dibatasi per IP.
- [ ] Respons blocked adalah `429` dengan `Retry-After`, tanpa membocorkan identifier.

**Verification:**
- [ ] Tests untuk batas, reset window, success reset, dan persistensi lintas service instance.

**Dependencies:** Task 5

**Files likely touched:** `app/services/auth_rate_limit_service.py`, `app/routes/auth_route.py`, `app/services/auth_service.py`, `tests/test_auth_rate_limit.py`

**Estimated scope:** Medium

## Task 7: Session Lifetime and Device Limit

**Description:** Terapkan absolute timeout 24 jam, idle timeout 2 jam, dan maksimal tiga sesi aktif per user.

**Acceptance criteria:**
- [ ] Sesi idle/absolute expired tidak dapat memakai endpoint terlindungi.
- [ ] Login keempat mencabut sesi aktif paling lama.
- [ ] Pembuatan sesi concurrency-safe dan logout-all tetap bekerja.

**Verification:**
- [ ] Service tests dengan waktu terkontrol dan empat sesi berurutan.

**Dependencies:** Task 2

**Files likely touched:** `app/services/auth_service.py`, `app/models/user_session.py`, `tests/test_auth_service.py`

**Estimated scope:** Medium

## Task 8: Verified Google Identity Token

**Description:** Gunakan library resmi Google untuk memverifikasi token sebelum membaca identity claims.

**Acceptance criteria:**
- [ ] Signature, audience, issuer, expiry, dan email verification diperiksa.
- [ ] `sub` tetap menjadi identity key dan error eksternal tidak membocorkan detail internal.
- [ ] Tidak ada penggunaan `get_unverified_claims` untuk autentikasi.

**Verification:**
- [ ] Mocked tests untuk token valid dan setiap kelas token invalid.

**Dependencies:** Task 5

**Files likely touched:** `requirements.txt`, `app/services/auth_service.py`, `tests/test_auth_service.py`

**Estimated scope:** Medium

## Task 9: One-time OAuth State and Nonce

**Description:** Kaitkan browser start/callback dengan state record sekali pakai, cookie korelasi, serta nonce yang diverifikasi dari ID token.

**Acceptance criteria:**
- [ ] Callback tanpa cookie/state valid ditolak.
- [ ] Callback replay dan nonce mismatch ditolak.
- [ ] State/cookie kedaluwarsa maksimal 10 menit dan selalu dibersihkan.

**Verification:**
- [ ] Route tests untuk success, missing, expired, mismatch, dan replay.

**Dependencies:** Tasks 5, 8

**Files likely touched:** `app/routes/auth_route.py`, `app/services/auth_service.py`, `app/schemas/auth.py`, `tests/test_auth_routes.py`, `tests/test_auth_service.py`

**Estimated scope:** Medium

## Task 10: Remove Legacy Auth and Add Safe Headers

**Description:** Hapus fallback legacy JWT dan tambahkan header keamanan API yang kompatibel dengan arsitektur frontend/backend saat ini.

**Acceptance criteria:**
- [ ] Cookie JWT lama tidak lagi mengautentikasi request.
- [ ] Cookie lama tetap dihapus saat auth/logout.
- [ ] API mengirim nosniff, frame denial, dan referrer policy; HSTS hanya saat HTTPS production.

**Verification:**
- [ ] Route tests untuk legacy rejection dan security headers.

**Dependencies:** Tasks 2, 7

**Files likely touched:** `app/services/auth_service.py`, `app/main.py`, `tests/test_auth_routes.py`

**Estimated scope:** Small

## Task 11: Safe Authentication Event Logging

**Description:** Catat event sukses/gagal/rate-limited/revoked menggunakan identifier hash dan metadata minimal untuk investigasi tanpa token, password, email, atau IP mentah.

**Acceptance criteria:**
- [ ] Tidak ada secret/credential/PII mentah pada log.
- [ ] Event memiliki action, outcome, timestamp, dan correlation identifier.
- [ ] Retention usulan 30 hari terdokumentasi.

**Verification:**
- [ ] Tests memastikan field sensitif tidak muncul dalam output log.

**Dependencies:** Tasks 6, 7, 9

**Files likely touched:** `app/services/auth_audit_service.py`, `app/routes/auth_route.py`, `tests/test_auth_audit.py`

**Estimated scope:** Medium

## Task 12: End-to-end Regression Verification

**Description:** Verifikasi seluruh alur manual/Google/session dan pastikan marketplace serta endpoint terlindungi tidak mengalami regresi.

**Acceptance criteria:**
- [ ] Manual register → login → `/me` → logout berhasil.
- [ ] Google valid langsung masuk; callback invalid/replay ditolak.
- [ ] Seluruh backend test dan frontend checks terkait lulus.

**Verification:**
- [ ] `python -m unittest discover -s tests -v` dalam container source-mounted.
- [ ] Frontend `tsc --noEmit`, targeted ESLint, dan utility tests.
- [ ] Manual browser check untuk cookie attributes dan redirect.
- [ ] Frontend production build tidak dijalankan.

**Dependencies:** Tasks 1-11

**Files likely touched:** tests only if a regression guard is missing

**Estimated scope:** Small

## Checkpoints

- [ ] Setelah Task 4: manual registration/login contract disetujui dan tests hijau.
- [ ] Setelah Task 7: rate limit dan session policies terverifikasi.
- [ ] Setelah Task 9: Google OAuth aman dan tetap berfungsi.
- [ ] Setelah Task 12: seluruh scope siap review.

