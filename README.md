# Asynchronous FastAPI & Socket.IO Cloud-Native Chat Backend

Backend ini dirancang khusus untuk mendukung aplikasi **FECHAT** (Real-Time Chat App) dengan menggunakan arsitektur modern berkinerja tinggi. Backend diimplementasikan menggunakan **FastAPI (Python)** untuk REST API, **Socket.IO** untuk komunikasi real-time, **SQLAlchemy (Async)** untuk manipulasi database, serta dikontainerisasi dengan **Docker** dan diintegrasikan dengan **GitHub Actions** untuk alur CI/CD.

Pekerjaan ini dibuat untuk memenuhi projek Tugas Akhir (Tubes) dengan judul:
> **"Perancangan dan Implementasi Aplikasi Chat Real-Time Berbasis Cloud-Native Menggunakan AWS, Docker, dan GitHub Actions"**

---

## 🚀 Fitur Utama

- **Kinerja Asinkronus Tinggi**: Menggunakan FastAPI dan engine asinkronus penuh (`async/await`) untuk penanganan request yang efisien.
- **Komunikasi Real-Time (Socket.IO)**: Sinkronisasi pesan instan, kehadiran online/offline (*online presence*), pembaruan chat sidebar, dan notifikasi friend request secara real-time.
- **Autentikasi Aman & JWT**: Enkripsi password menggunakan `bcrypt` dan pengamanan REST & WebSocket dengan token Bearer JWT.
- **Dukungan Multi-Database (SQLite & PostgreSQL)**: Terkonfigurasi untuk berjalan dengan SQLite pada proses development lokal, dan beralih ke PostgreSQL (misal AWS RDS) untuk deployment production hanya dengan mengganti `DATABASE_URL`.
- **Auto-Migration & Database Seeding**: Skema tabel otomatis terbentuk pada saat startup awal dan database otomatis diisi (*seeded*) dengan user testing bawaan (`ada-77`, `bob-99`, dsb.) agar integrasi dengan frontend instan tanpa setup manual.
- **Dockerized & Orchestrated**: Dilengkapi `Dockerfile` multi-stage yang dioptimalkan serta `docker-compose.yml` untuk menjalankan aplikasi beserta database PostgreSQL dalam satu perintah.
- **CI/CD Pipeline**: Dilengkapi file workflow GitHub Actions (`.github/workflows/docker-be.yml`) untuk build otomatis dan publish image ke Docker Hub.

---

## 📂 Struktur Proyek

```text
d:\BECHAT\
├── .github/
│   └── workflows/
│       └── docker-be.yml       # GitHub Actions CI/CD workflow
├── app/
│   ├── __init__.py             # Inisialisasi package Python
│   ├── main.py                 # Core server (FastAPI app & Socket.IO handlers)
│   ├── config.py               # Pengaturan aplikasi & Pydantic settings
│   ├── database.py             # Koneksi database async (SQLAlchemy)
│   ├── models.py               # Model database SQLAlchemy (User, Chat, Message, dll.)
│   ├── schemas.py              # Pydantic schemas (Validasi Request & Response)
│   ├── auth.py                 # Helper autentikasi (JWT & Bcrypt Hashing)
│   └── seed.py                 # Script auto-seed data mock user bawaan
├── Dockerfile                  # Multi-stage production Dockerfile
├── docker-compose.yml          # Orkestrasi Docker lokal (App + PostgreSQL)
├── requirements.txt            # Daftar pustaka dependensi Python
├── .env                        # File konfigurasi Environment lokal
└── README.md                   # Dokumentasi lengkap (File ini)
```

---

## 🛠️ Panduan Instalasi & Menjalankan Lokal

### Prasyarat
- Python 3.12 atau yang lebih baru (Disarankan Python 3.13)
- Docker Desktop (Opsional, untuk containerization)

### Langkah 1: Setup Virtual Environment & Dependensi
Buka terminal/PowerShell di direktori `d:\BECHAT`:

1. Buat Virtual Environment jika belum ada:
   ```powershell
   python -m venv .venv
   ```
2. Aktifkan Virtual Environment:
   * **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   * **Windows (CMD)**:
     ```cmd
     .venv\Scripts\activate.bat
     ```
3. Install seluruh dependensi yang tertera di `requirements.txt`:
   ```powershell
   pip install -r requirements.txt
   ```

### Langkah 2: Konfigurasi `.env`
Buka file `.env` di root folder dan sesuaikan variabel konfigurasi:
```env
JWT_SECRET=dev-secret-change-me-in-production-1234567890
DATABASE_URL=postgresql+psycopg://postgres:1234@localhost:5434/chat
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]
```

> [!TIP]
> Jika Anda belum menjalankan server PostgreSQL di sistem Anda, Anda bisa menggunakan **SQLite** secara instan untuk testing mandiri dengan mengubah:
> `DATABASE_URL=sqlite+aiosqlite:///./app.db`
>
> Sistem akan otomatis membuat file `app.db` di root dan memigrasikan tabelnya.

### Langkah 3: Menjalankan Server Lokal
Jalankan server menggunakan Uvicorn:
```powershell
python -m uvicorn app.main:sio_asgi_app --reload --port 5000
```
Server akan berjalan di:
- REST API Base URL: `http://localhost:5000/api`
- WebSocket/Socket.IO Path: `http://localhost:5000/socket.io`
- Swagger Interactive Documentation: `http://localhost:5000/docs`

---

## 🐳 Orkestrasi dengan Docker Compose

Aplikasi ini sudah dilengkapi database PostgreSQL terisolasi menggunakan Docker Compose. Ini merupakan simulasi cloud-native di lingkungan lokal.

Jalankan perintah berikut:
```bash
docker-compose up --build -d
```

Perintah di atas akan secara otomatis:
1. Mendownload dan menjalankan PostgreSQL versi `15-alpine` di port `5434`.
2. Melakukan build file `Dockerfile` backend FastAPI.
3. Menjalankan backend FastAPI di port `5000`.
4. Menunggu PostgreSQL siap, melakukan migrasi tabel secara otomatis, dan menginputkan seed data user testing.

Untuk menghentikan layanan:
```bash
docker-compose down
```

---

## 🛜 Kontrak Integrasi REST API & WebSocket

### 1. Endpoint REST API (di bawah `/api`)

| Method | Endpoint | Fungsi | Keterangan |
| --- | --- | --- | --- |
| **POST** | `/auth/register` | Mendaftarkan user baru | Input: `userId`, `name`, `email`, `password` |
| **POST** | `/auth/login` | Login user | Mengembalikan JWT Token & Data User |
| **GET** | `/chats` | Mendapatkan daftar chat aktif | Memerlukan JWT Token. Berisi detail unread, status online, & chat type |
| **GET** | `/chats/{chatId}/messages` | Mengambil riwayat pesan | Memerlukan JWT Token |
| **GET** | `/members` | Direktori seluruh member | Memerlukan JWT Token |
| **GET** | `/friend-requests` | Melihat friend requests pending | Memerlukan JWT Token |
| **POST** | `/friend-requests` | Mengirim friend request | Input: `{"to": "target-user-id"}` |
| **POST** | `/friend-requests/{reqId}/accept` | Menerima friend request | Membuat direct chat baru secara otomatis |
| **POST** | `/friend-requests/{reqId}/reject` | Menolak friend request | Mengupdate status menjadi rejected |
| **GET** | `/users/{userId}` | Cari user berdasarkan ID | Dipakai saat inisiasi chat baru |
| **GET** | `/files` | Melihat file yang dibagikan | Mendukung pencarian dan filter chatId |
| **POST** | `/files` | Upload file (`multipart/form-data`) | Menyimpan ke disk & mengembalikan info file |
| **GET** | `/files/{fileId}/download` | Download file biner | Mengunduh file secara langsung |

### 2. Event Real-Time Socket.IO

Ketika client terhubung menggunakan `socket.io-client`:
- **Auth Handshake**: Client wajib mengirim token via `auth`:
  ```javascript
  const socket = io('http://localhost:5000', {
    auth: { token: localStorage.getItem('token') }
  });
  ```
  *Backend akan otomatis memvalidasi token, mengubah status database user ke `online`, dan memancarkan notifikasi status.*

- **Client Emit ke Server**:
  - `joinChat`: data `{"chatId": "c1"}` (Memasukkan client ke ruang chat terkait).
  - `leaveChat`: data `{"chatId": "c1"}` (Mengeluarkan client dari ruang chat).
  - `sendMessage`: data `{"chatId": "c1", "content": "Halo team"}` (Menyimpan pesan di DB & memancarkan secara realtime).

- **Server Emit ke Client**:
  - `memberStatusUpdate`: memberi tahu perubahan status online/offline user lain secara instan.
  - `receiveMessage`: memancarkan pesan baru yang masuk ke ruang chat.
  - `chatUpdated`: memberi tahu sidebar chat agar memperbarui pesan terakhir dan counter unread secara realtime.
  - `friendRequestReceived`: memunculkan popup friend request baru secara instan.
  - `friendRequestAccepted`: memunculkan room chat baru di sidebar secara instan pada penerima request saat disetujui.

---

## 🛠️ Panduan CI/CD dengan GitHub Actions

File `.github/workflows/docker-be.yml` mengotomatisasi proses deployment ke Docker Hub ketika ada pembaruan pada branch `main` atau `master`.

### Konfigurasi Repository Secrets di GitHub
Agar pipeline berjalan dengan lancar, Anda harus menambahkan Secrets berikut pada repository GitHub Anda:
1. Masuk ke **Settings > Secrets and variables > Actions** pada repo GitHub Anda.
2. Klik **New repository secret** dan tambahkan:
   - `DOCKERHUB_USERNAME`: Username Docker Hub Anda.
   - `DOCKERHUB_TOKEN`: Personal Access Token Docker Hub Anda (Buat di *Docker Hub Account Settings > Security > New Access Token*).

Saat Anda melakukan `git push` ke branch `main`, GitHub Actions akan otomatis membuat image Docker terbaru dengan tag `:latest` dan `:commit-sha`, lalu mempublikasikannya ke Docker Hub registry Anda.

---

## ☁️ Rekomendasi Deployment Cloud AWS (Cloud-Native)

Untuk mendukung judul Tugas Akhir bertema **Cloud-Native AWS**, berikut adalah rekomendasi arsitektur deployment di AWS:

1. **Database Layer (AWS RDS PostgreSQL)**:
   - Gunakan AWS RDS PostgreSQL instance untuk database utama yang andal dan terkelola secara otomatis (*Managed Database*).
   - Set database URL backend Anda ke endpoint AWS RDS PostgreSQL.

2. **Container Registry (AWS ECR)**:
   - Alternatif Docker Hub, Anda dapat mengarahkan pipeline GitHub Actions untuk melakukan push image Docker ke **Amazon Elastic Container Registry (ECR)**.

3. **Backend Service (AWS ECS Fargate)**:
   - Deploy image Docker backend Anda ke **Amazon ECS** menggunakan **AWS Fargate** (serverless container execution).
   - Fargate akan mengelola scaling dan provisioning kontainer backend secara otomatis tanpa harus memanage server EC2 fisik.

4. **Routing & SSL (Application Load Balancer - ALB)**:
   - Gunakan **AWS ALB** di depan ECS Fargate. ALB mendukung protokol WebSockets natively, yang sangat krusial untuk koneksi stabil Socket.IO.
   - Sambungkan dengan **AWS Certificate Manager (ACM)** untuk aktivasi HTTPS/WSS (SSL) gratis.

5. **Static File Storage (AWS S3)**:
   - File uploads dapat disimpan di bucket **Amazon S3** secara aman untuk menggantikan local filesystem disk storage lokal yang ephemeral.
