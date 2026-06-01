# Dokumentasi Integrasi Backend FECHAT

Dokumen ini menjelaskan kontrak yang dibutuhkan agar frontend FECHAT dapat disambungkan ke backend. Isi dokumen mengikuti kode yang ada di repository saat ini, terutama:

- `src/services/api.ts`
- `src/context/AuthContext.tsx`
- `src/pages/Login.tsx`
- `src/pages/Register.tsx`
- `src/pages/Chat.tsx`
- `src/pages/Files.tsx`
- `src/pages/Members.tsx`

## 1. Ringkasan Aplikasi

FECHAT adalah aplikasi chat berbasis React, Vite, TypeScript, dan React Router. Frontend sudah memiliki:

- Login dan register.
- Route guard untuk halaman privat.
- Penyimpanan session di `localStorage`.
- API wrapper dengan header `Authorization: Bearer <token>`.
- Halaman chat dengan daftar chat, members, friend requests, dan placeholder WebSocket.
- Halaman files dan members yang saat ini masih memakai mock data.

Backend minimal harus menyediakan REST API untuk auth, chat list, members, user lookup, dan friend request. Untuk realtime chat, backend sebaiknya menyediakan WebSocket atau Socket.IO.

## 2. Base URL dan Environment

Frontend membaca base URL API dari environment variable:

```env
VITE_API_URL=http://localhost:5000/api
```

Catatan penting:

- Jika `VITE_API_URL` tidak diisi, beberapa halaman akan memakai mock data dan tidak memanggil backend.
- `src/services/api.ts` punya fallback `http://localhost:5000/api`, tetapi halaman `Login`, `Register`, dan `Chat` tetap mengecek `import.meta.env.VITE_API_URL`. Jadi untuk integrasi real, wajib set `VITE_API_URL`.
- Setelah mengubah `.env`, restart dev server Vite.

Contoh file `.env` untuk development:

```env
VITE_API_URL=http://localhost:5000/api
VITE_WS_URL=http://localhost:5000
```

`VITE_WS_URL` belum dipakai langsung oleh kode saat ini, tetapi direkomendasikan untuk integrasi realtime.

## 3. Cara Menjalankan Frontend

Install dependency:

```bash
npm install
```

Jalankan frontend:

```bash
npm run dev
```

Default script menjalankan Vite di port `3000`:

```text
http://localhost:3000
```

Build production:

```bash
npm run build
```

Type check:

```bash
npm run lint
```

## 4. Arsitektur Integrasi FE

### 4.1 API Wrapper

Semua call backend sebaiknya lewat `src/services/api.ts`.

Perilaku wrapper:

- Mengambil token dari `localStorage.getItem('token')`.
- Jika token ada, menambahkan header:

```http
Authorization: Bearer <token>
```

- Jika body bukan `FormData`, otomatis menambahkan:

```http
Content-Type: application/json
```

- Jika response status bukan 2xx:
  - FE mencoba membaca JSON error.
  - FE memakai `errorData.message` sebagai pesan error.
  - Jika status `401`, FE menghapus `token` dan `user` dari `localStorage`, lalu redirect ke `/login`.

Format error backend yang direkomendasikan:

```json
{
  "message": "Invalid email or password"
}
```

### 4.2 Kewajiban Response JSON

API wrapper saat ini selalu menjalankan:

```ts
return response.json();
```

Artinya semua response sukses sebaiknya punya JSON body. Hindari response `204 No Content` kecuali frontend diubah lebih dulu.

Contoh response delete/update yang aman:

```json
{
  "success": true
}
```

## 5. Session dan Auth Flow

### 5.1 Data Session FE

Setelah login/register sukses, FE menyimpan:

```text
localStorage.token
localStorage.user
```

`user` disimpan sebagai JSON string.

Type `User` yang dibutuhkan FE:

```ts
type User = {
  id: string;
  name: string;
  email: string;
  avatar?: string;
};
```

### 5.2 Route Guard

Halaman privat:

- `/chat`
- `/groups`
- `/files`
- `/members`

Jika tidak ada token, user diarahkan ke `/login`.

Halaman publik:

- `/login`
- `/register`

Jika sudah ada token, user diarahkan ke `/chat`.

### 5.3 Logout

Logout saat ini hanya terjadi di frontend:

- Menghapus `token`.
- Menghapus `user`.
- Mengosongkan auth state.

Backend tidak wajib menyediakan endpoint logout untuk versi minimal. Jika memakai refresh token atau session server-side, tambahkan endpoint logout dan panggil dari FE.

## 6. Standar Umum API

### 6.1 Prefix

Semua endpoint di dokumen ini diasumsikan berada di bawah:

```text
{VITE_API_URL}
```

Jika `.env` berisi:

```env
VITE_API_URL=http://localhost:5000/api
```

Maka endpoint login menjadi:

```text
POST http://localhost:5000/api/auth/login
```

### 6.2 Header

Endpoint publik:

```http
Content-Type: application/json
```

Endpoint privat:

```http
Content-Type: application/json
Authorization: Bearer <token>
```

Upload file:

```http
Authorization: Bearer <token>
```

Untuk `FormData`, frontend tidak boleh memaksa `Content-Type`; browser akan mengisi multipart boundary otomatis.

### 6.3 Format Error

Gunakan format konsisten:

```json
{
  "message": "Human readable error message",
  "code": "OPTIONAL_MACHINE_CODE",
  "details": {}
}
```

FE saat ini hanya membaca `message`.

### 6.4 Status Code

Rekomendasi:

| Status | Kapan dipakai |
| --- | --- |
| 200 | Request sukses |
| 201 | Resource berhasil dibuat |
| 400 | Request body/query tidak valid |
| 401 | Token hilang, invalid, atau expired |
| 403 | Token valid tetapi tidak punya izin |
| 404 | Resource tidak ditemukan |
| 409 | Conflict, misalnya email atau userId sudah dipakai |
| 422 | Validasi domain gagal |
| 500 | Error server |

## 7. Data Model yang Dibutuhkan FE

### 7.1 User

```ts
type User = {
  id: string;
  name: string;
  email: string;
  avatar?: string;
};
```

Contoh:

```json
{
  "id": "ada-77",
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "avatar": "https://example.com/avatar/ada.png"
}
```

### 7.2 ChatSession

```ts
type ChatSession = {
  id: string;
  name: string;
  type: "direct" | "group";
  avatar?: string;
  color?: string;
  lastMessage: string;
  time: string;
  unreadCount: number;
  online: boolean;
};
```

Catatan:

- `id` dipakai sebagai identifier chat aktif.
- `type` menentukan apakah chat masuk tab direct atau group.
- `avatar` adalah URL image.
- `color` saat ini berupa class Tailwind seperti `bg-rose-500`. Untuk backend real, lebih aman kirim `avatar` atau field warna biasa seperti hex, lalu FE bisa disesuaikan.
- `time` saat ini string siap tampil, misalnya `"2:51 PM"` atau `"Yesterday"`. Untuk backend yang lebih rapi, kirim juga timestamp ISO seperti `lastMessageAt`, lalu FE bisa diformat di client.

Contoh:

```json
{
  "id": "c1",
  "name": "Engineering Team",
  "type": "group",
  "avatar": "https://example.com/groups/engineering.png",
  "lastMessage": "David: Let's look at the blur-radius.",
  "time": "2:51 PM",
  "unreadCount": 3,
  "online": true
}
```

### 7.3 Message

```ts
type Message = {
  id: string;
  senderId: string;
  senderName: string;
  senderAvatar?: string;
  senderColor?: string;
  time: string;
  content: string;
  image?: string;
  status?: "sent" | "delivered" | "read";
  isSelf: boolean;
};
```

Catatan:

- `content` di type FE bisa `string | React.ReactNode`, tetapi dari backend gunakan `string`.
- `isSelf` bisa dihitung di frontend dari `senderId === currentUser.id`. Untuk endpoint awal, boleh dikirim dari backend agar cocok dengan UI saat ini.
- `time` sebaiknya string siap tampil untuk kompatibilitas sekarang. Untuk jangka panjang, tambahkan `createdAt` ISO.

Contoh:

```json
{
  "id": "msg-1001",
  "senderId": "ada-77",
  "senderName": "Ada Lovelace",
  "senderAvatar": "",
  "time": "2:50 PM",
  "content": "Halo team",
  "status": "read",
  "isSelf": true
}
```

### 7.4 Member

Untuk panel member di halaman chat:

```ts
type Member = {
  id: string;
  name: string;
  role: "Admin" | "Engineer" | "Designer" | "Guest";
  status: "online" | "offline" | "busy";
  avatar: string;
  color?: string;
};
```

Untuk halaman `/members`, mock data juga memiliki:

```ts
email: string;
github: string;
```

Rekomendasi backend:

```ts
type Member = {
  id: string;
  name: string;
  role: "Admin" | "Engineer" | "Designer" | "Guest";
  status: "online" | "offline" | "busy";
  avatar: string;
  color?: string;
  email?: string;
  github?: string;
};
```

Contoh:

```json
{
  "id": "1",
  "name": "Elena Rostova",
  "role": "Admin",
  "status": "online",
  "avatar": "https://example.com/avatar/elena.png",
  "email": "elena@example.com",
  "github": "erostova"
}
```

### 7.5 FriendRequest

```ts
type FriendRequest = {
  id: string;
  fromId: string;
  fromName: string;
};
```

Contoh:

```json
{
  "id": "req-1",
  "fromId": "bob-99",
  "fromName": "Bob Engineer"
}
```

### 7.6 FileItem

Halaman `/files` saat ini masih mock data, tetapi jika mau disambungkan ke backend, gunakan model:

```ts
type FileItem = {
  id: string;
  name: string;
  type: "folder" | "image" | "document" | "archive" | "code";
  size: string;
  modified: string;
  owner: string;
};
```

Contoh:

```json
{
  "id": "file-1",
  "name": "api_spec_v1.4.pdf",
  "type": "document",
  "size": "1.1 MB",
  "modified": "5 hours ago",
  "owner": "Marcus Chen"
}
```

## 8. Endpoint Wajib untuk Versi Minimal

Endpoint berikut adalah yang sudah dirujuk langsung oleh kode frontend.

### 8.1 Login

```http
POST /auth/login
```

Auth: publik.

Request:

```json
{
  "email": "ada@example.com",
  "password": "Secret123"
}
```

Response sukses:

```json
{
  "token": "jwt-token",
  "user": {
    "id": "ada-77",
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "avatar": ""
  }
}
```

Response gagal:

```json
{
  "message": "Invalid email or password"
}
```

Validasi backend:

- `email` wajib valid.
- `password` wajib.
- Return `401` jika kredensial salah.

### 8.2 Register

```http
POST /auth/register
```

Auth: publik.

Request dari FE:

```json
{
  "userId": "ada-77",
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "Secret123"
}
```

Response sukses:

```json
{
  "token": "jwt-token",
  "user": {
    "id": "ada-77",
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "avatar": ""
  }
}
```

Catatan:

- FE mengirim field `userId`, tetapi menyimpan user sebagai `id`.
- Backend harus memetakan `userId` menjadi `user.id` di response.
- Return `409` jika `email` atau `userId` sudah dipakai.

### 8.3 Get Chats

```http
GET /chats
```

Auth: wajib.

Response sukses:

```json
[
  {
    "id": "c1",
    "name": "Engineering Team",
    "type": "group",
    "avatar": "https://example.com/groups/engineering.png",
    "lastMessage": "David: Let's look at the blur-radius.",
    "time": "2:51 PM",
    "unreadCount": 3,
    "online": true
  },
  {
    "id": "u2",
    "name": "Elena Rostova",
    "type": "direct",
    "avatar": "https://example.com/avatar/elena.png",
    "lastMessage": "Verification complete!",
    "time": "2:46 PM",
    "unreadCount": 0,
    "online": true
  }
]
```

### 8.4 Get Members

```http
GET /members
```

Auth: wajib.

Response sukses:

```json
[
  {
    "id": "1",
    "name": "Elena Rostova",
    "role": "Admin",
    "status": "online",
    "avatar": "https://example.com/avatar/elena.png"
  },
  {
    "id": "3",
    "name": "Marcus Chen",
    "role": "Engineer",
    "status": "online",
    "avatar": "",
    "color": "bg-rose-500"
  }
]
```

### 8.5 Get Friend Requests

```http
GET /friend-requests
```

Auth: wajib.

Response sukses:

```json
[
  {
    "id": "req-1",
    "fromId": "bob-99",
    "fromName": "Bob Engineer"
  }
]
```

### 8.6 Lookup User by ID

```http
GET /users/:id
```

Auth: wajib.

Dipakai ketika user klik start new chat dan memasukkan user ID.

Response sukses minimal:

```json
{
  "id": "ada-77",
  "name": "Ada Lovelace"
}
```

Response jika tidak ditemukan:

```json
{
  "message": "User ID not found. Please check the ID and try again."
}
```

Gunakan status `404`.

### 8.7 Send Friend Request

```http
POST /friend-requests
```

Auth: wajib.

Request:

```json
{
  "to": "ada-77"
}
```

Response sukses:

```json
{
  "success": true,
  "request": {
    "id": "req-2",
    "fromId": "current-user-id",
    "fromName": "Current User",
    "toId": "ada-77",
    "status": "pending"
  }
}
```

Status yang disarankan:

- `201` jika request baru dibuat.
- `200` jika request sudah pernah ada dan masih pending.
- `409` jika user sudah menjadi friend/contact.

## 9. Endpoint yang Sudah Disiapkan di Komentar FE

Endpoint berikut belum aktif penuh di kode, tetapi sudah ada titik integrasinya.

### 9.1 Accept Friend Request

```http
POST /friend-requests/:requestId/accept
```

Auth: wajib.

Response sukses:

```json
{
  "success": true,
  "chat": {
    "id": "bob-99",
    "name": "Bob Engineer",
    "type": "direct",
    "lastMessage": "Say hi!",
    "time": "Just now",
    "unreadCount": 0,
    "online": true
  }
}
```

Catatan implementasi FE saat ini:

- Handler `handleAcceptFriendRequest` masih update local state tanpa memanggil API.
- Setelah BE siap, aktifkan call ini di handler tersebut.
- Idealnya FE memakai `chat` dari response, bukan membuat chat lokal manual.

### 9.2 Reject Friend Request

```http
POST /friend-requests/:requestId/reject
```

Auth: wajib.

Response sukses:

```json
{
  "success": true
}
```

Catatan implementasi FE saat ini:

- Handler `handleRejectFriendRequest` masih update local state tanpa memanggil API.
- Setelah BE siap, aktifkan call ini di handler tersebut.

## 10. Endpoint Rekomendasi untuk Chat Lengkap

Kode saat ini belum mengambil message history dari backend. Agar chat benar-benar lengkap, backend sebaiknya menyediakan endpoint berikut dan FE bisa ditambahkan call-nya saat `activeChat` berubah.

### 10.1 Get Messages by Chat

```http
GET /chats/:chatId/messages?limit=50&before=<cursor>
```

Auth: wajib.

Response sukses sederhana:

```json
[
  {
    "id": "msg-1",
    "senderId": "elena",
    "senderName": "Elena Rostova",
    "senderAvatar": "https://example.com/avatar/elena.png",
    "time": "2:46 PM",
    "content": "Can someone verify the glow intensity?",
    "status": "read",
    "isSelf": false
  }
]
```

Response dengan pagination yang lebih baik:

```json
{
  "items": [
    {
      "id": "msg-1",
      "senderId": "elena",
      "senderName": "Elena Rostova",
      "senderAvatar": "https://example.com/avatar/elena.png",
      "time": "2:46 PM",
      "createdAt": "2026-06-01T07:46:00.000Z",
      "content": "Can someone verify the glow intensity?",
      "status": "read",
      "isSelf": false
    }
  ],
  "nextCursor": "msg-1"
}
```

Jika memakai format pagination object, FE perlu disesuaikan karena saat ini type `messages` adalah array langsung.

### 10.2 Send Message via REST

Jika belum memakai WebSocket untuk kirim message:

```http
POST /chats/:chatId/messages
```

Auth: wajib.

Request:

```json
{
  "content": "Halo team"
}
```

Response sukses:

```json
{
  "id": "msg-1002",
  "senderId": "ada-77",
  "senderName": "Ada Lovelace",
  "time": "2:52 PM",
  "createdAt": "2026-06-01T07:52:00.000Z",
  "content": "Halo team",
  "status": "sent",
  "isSelf": true
}
```

### 10.3 Mark Message Read

```http
POST /chats/:chatId/read
```

Auth: wajib.

Request:

```json
{
  "lastReadMessageId": "msg-1002"
}
```

Response:

```json
{
  "success": true
}
```

### 10.4 Delete Chat or Leave Chat

UI saat ini punya aksi delete room secara lokal.

Untuk direct chat:

```http
DELETE /chats/:chatId
```

Response:

```json
{
  "success": true
}
```

Untuk group, lebih aman bedakan antara leave dan delete:

```http
POST /chats/:chatId/leave
DELETE /chats/:chatId
```

`DELETE` hanya boleh untuk owner/admin.

## 11. Endpoint Rekomendasi untuk Groups

Halaman `/groups` saat ini masih full mock. Jika ingin dihubungkan:

### 11.1 Get Group Chats

```http
GET /groups
```

Auth: wajib.

Response:

```json
[
  {
    "id": "g1",
    "name": "Engineering Team",
    "type": "group",
    "avatar": "https://example.com/groups/engineering.png",
    "lastMessage": "Marcus: Pushing the fix now.",
    "time": "2:51 PM",
    "unreadCount": 3,
    "online": true
  }
]
```

### 11.2 Create Group

```http
POST /groups
```

Auth: wajib.

Request:

```json
{
  "name": "Project Alpha",
  "memberIds": ["ada-77", "bob-99"]
}
```

Response:

```json
{
  "id": "g3",
  "name": "Project Alpha",
  "type": "group",
  "avatar": "",
  "lastMessage": "Group created",
  "time": "Just now",
  "unreadCount": 0,
  "online": true
}
```

### 11.3 Get Group Members

```http
GET /groups/:groupId/members
```

Auth: wajib.

Response:

```json
[
  {
    "id": "ada-77",
    "name": "Ada Lovelace",
    "role": "Admin",
    "status": "online",
    "avatar": ""
  }
]
```

## 12. Endpoint Rekomendasi untuk Files

Halaman `/files` saat ini masih mock. Jika ingin disambungkan:

### 12.1 Get Files

```http
GET /files?chatId=<optional>&q=<optional>
```

Auth: wajib.

Response:

```json
[
  {
    "id": "file-1",
    "name": "api_spec_v1.4.pdf",
    "type": "document",
    "size": "1.1 MB",
    "modified": "5 hours ago",
    "owner": "Marcus Chen"
  }
]
```

### 12.2 Upload File

```http
POST /files
```

Auth: wajib.

Request: `multipart/form-data`.

Field yang disarankan:

```text
file: binary
chatId: optional string
folderId: optional string
```

Response:

```json
{
  "id": "file-2",
  "name": "hero_background_v2.png",
  "type": "image",
  "size": "4.2 MB",
  "modified": "Just now",
  "owner": "Ada Lovelace",
  "url": "https://example.com/files/file-2"
}
```

### 12.3 Download File

```http
GET /files/:fileId/download
```

Auth: wajib.

Response:

- Bisa redirect ke signed URL.
- Bisa stream file langsung.

Jika response bukan JSON, jangan panggil endpoint ini lewat `api.get()` yang sekarang, karena wrapper selalu `response.json()`. Gunakan `fetch` khusus untuk blob/download.

### 12.4 Delete File

```http
DELETE /files/:fileId
```

Response:

```json
{
  "success": true
}
```

## 13. Realtime dengan WebSocket atau Socket.IO

Di `src/pages/Chat.tsx` sudah ada placeholder untuk Socket.IO:

```ts
// import { io } from 'socket.io-client';
// const socket = io('YOUR_BE_URL', { auth: { token: localStorage.getItem('token') } });
```

Rekomendasi:

- Gunakan Socket.IO jika ingin mengikuti komentar FE saat ini.
- Install dependency frontend jika belum ada:

```bash
npm install socket.io-client
```

- Tambahkan env:

```env
VITE_WS_URL=http://localhost:5000
```

### 13.1 Handshake Auth

Client mengirim token:

```ts
io(VITE_WS_URL, {
  auth: {
    token: localStorage.getItem('token')
  }
});
```

Backend harus memvalidasi token yang sama dengan REST API.

Jika token invalid:

- Reject connection.
- Emit/connect error dengan message yang jelas.

### 13.2 Event dari Client ke Server

#### sendMessage

```ts
socket.emit("sendMessage", {
  chatId: "c1",
  content: "Halo team",
  senderId: "ada-77"
});
```

Payload:

```json
{
  "chatId": "c1",
  "content": "Halo team",
  "senderId": "ada-77"
}
```

Catatan:

- Backend sebaiknya tidak mempercayai `senderId` dari client.
- Gunakan user ID dari token sebagai sender sebenarnya.
- `senderId` dari client boleh diabaikan atau dipakai hanya untuk debug.

#### joinChat

Direkomendasikan walaupun belum ada di FE:

```ts
socket.emit("joinChat", {
  "chatId": "c1"
});
```

Backend memasukkan socket ke room chat terkait.

#### leaveChat

```ts
socket.emit("leaveChat", {
  "chatId": "c1"
});
```

### 13.3 Event dari Server ke Client

#### receiveMessage

Sudah disebut di komentar FE.

```ts
socket.on("receiveMessage", (message) => {
  setMessages(prev => [...prev, message]);
});
```

Payload:

```json
{
  "id": "msg-1003",
  "chatId": "c1",
  "senderId": "bob-99",
  "senderName": "Bob Engineer",
  "senderAvatar": "",
  "time": "2:55 PM",
  "createdAt": "2026-06-01T07:55:00.000Z",
  "content": "Siap, saya cek.",
  "status": "delivered",
  "isSelf": false
}
```

#### messageStatusUpdate

Sudah disebut di komentar FE.

```ts
socket.on("messageStatusUpdate", ({ messageId, status }) => {
  setMessages(prev => prev.map(m => m.id === messageId ? { ...m, status } : m));
});
```

Payload:

```json
{
  "messageId": "msg-1003",
  "chatId": "c1",
  "status": "read"
}
```

Status valid:

```text
sent
delivered
read
```

#### chatUpdated

Direkomendasikan agar sidebar chat ikut berubah.

```json
{
  "id": "c1",
  "lastMessage": "Bob: Siap, saya cek.",
  "time": "2:55 PM",
  "unreadCount": 4
}
```

#### friendRequestReceived

Direkomendasikan agar modal request realtime.

```json
{
  "id": "req-3",
  "fromId": "new-user-1",
  "fromName": "New User"
}
```

#### friendRequestAccepted

Direkomendasikan agar chat direct muncul saat request diterima.

```json
{
  "requestId": "req-3",
  "chat": {
    "id": "new-user-1",
    "name": "New User",
    "type": "direct",
    "lastMessage": "Say hi!",
    "time": "Just now",
    "unreadCount": 0,
    "online": true
  }
}
```

## 14. CORS untuk Development

Jika frontend jalan di `http://localhost:3000`, backend harus mengizinkan origin tersebut.

Contoh konfigurasi Express:

```ts
import cors from "cors";

app.use(cors({
  origin: ["http://localhost:3000"],
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"]
}));
```

Jika tidak memakai cookie dan hanya memakai bearer token, `credentials` tidak wajib. Tetapi tetap aman jika disiapkan sejak awal.

## 15. JWT dan Security

Rekomendasi claim JWT:

```json
{
  "sub": "ada-77",
  "email": "ada@example.com",
  "name": "Ada Lovelace",
  "iat": 1780297200,
  "exp": 1780383600
}
```

Aturan:

- Simpan password dengan hash kuat seperti bcrypt atau argon2.
- Jangan kirim password hash ke frontend.
- Gunakan HTTPS di production.
- Set masa berlaku token yang masuk akal.
- Untuk production, pertimbangkan refresh token di httpOnly cookie.
- Rate limit endpoint login dan register.
- Validasi semua input di backend.
- Jangan percaya `senderId`, `role`, atau `status` dari client.

## 16. Contoh Implementasi Backend Express Minimal

Contoh ini hanya untuk memvalidasi kontrak dengan frontend. Untuk production, ganti in-memory data dengan database dan password hashing.

```ts
import express from "express";
import cors from "cors";
import jwt from "jsonwebtoken";

const app = express();
const JWT_SECRET = process.env.JWT_SECRET || "dev-secret";

app.use(cors({
  origin: ["http://localhost:3000"],
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"]
}));
app.use(express.json());

const users = [
  { id: "ada-77", name: "Ada Lovelace", email: "ada@example.com", password: "Secret123", avatar: "" },
  { id: "bob-99", name: "Bob Engineer", email: "bob@example.com", password: "Secret123", avatar: "" }
];

const chats = [
  {
    id: "c1",
    name: "Engineering Team",
    type: "group",
    avatar: "",
    lastMessage: "Welcome to Engineering Team",
    time: "Just now",
    unreadCount: 0,
    online: true
  }
];

const members = [
  { id: "ada-77", name: "Ada Lovelace", role: "Admin", status: "online", avatar: "" },
  { id: "bob-99", name: "Bob Engineer", role: "Engineer", status: "offline", avatar: "" }
];

let friendRequests = [
  { id: "req-1", fromId: "bob-99", fromName: "Bob Engineer", toId: "ada-77", status: "pending" }
];

function signToken(user: any) {
  return jwt.sign({ sub: user.id, email: user.email, name: user.name }, JWT_SECRET, { expiresIn: "1d" });
}

function publicUser(user: any) {
  return { id: user.id, name: user.name, email: user.email, avatar: user.avatar || "" };
}

function auth(req: any, res: any, next: any) {
  const header = req.headers.authorization || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";

  if (!token) {
    return res.status(401).json({ message: "Missing token" });
  }

  try {
    req.auth = jwt.verify(token, JWT_SECRET);
    next();
  } catch {
    return res.status(401).json({ message: "Invalid or expired token" });
  }
}

app.post("/api/auth/login", (req, res) => {
  const { email, password } = req.body;
  const user = users.find(u => u.email === email && u.password === password);

  if (!user) {
    return res.status(401).json({ message: "Invalid email or password" });
  }

  res.json({
    token: signToken(user),
    user: publicUser(user)
  });
});

app.post("/api/auth/register", (req, res) => {
  const { userId, name, email, password } = req.body;

  if (!userId || !name || !email || !password) {
    return res.status(400).json({ message: "userId, name, email, and password are required" });
  }

  if (users.some(u => u.id === userId || u.email === email)) {
    return res.status(409).json({ message: "User ID or email already exists" });
  }

  const user = { id: userId, name, email, password, avatar: "" };
  users.push(user);

  res.status(201).json({
    token: signToken(user),
    user: publicUser(user)
  });
});

app.get("/api/chats", auth, (_req, res) => {
  res.json(chats);
});

app.get("/api/members", auth, (_req, res) => {
  res.json(members);
});

app.get("/api/friend-requests", auth, (req: any, res) => {
  const currentUserId = req.auth.sub;
  res.json(friendRequests.filter(r => r.toId === currentUserId && r.status === "pending"));
});

app.get("/api/users/:id", auth, (req, res) => {
  const user = users.find(u => u.id === req.params.id);

  if (!user) {
    return res.status(404).json({ message: "User ID not found. Please check the ID and try again." });
  }

  res.json(publicUser(user));
});

app.post("/api/friend-requests", auth, (req: any, res) => {
  const fromId = req.auth.sub;
  const toId = req.body.to;
  const target = users.find(u => u.id === toId);
  const from = users.find(u => u.id === fromId);

  if (!target) {
    return res.status(404).json({ message: "Target user not found" });
  }

  if (fromId === toId) {
    return res.status(400).json({ message: "Cannot send friend request to yourself" });
  }

  const existing = friendRequests.find(r => r.fromId === fromId && r.toId === toId && r.status === "pending");
  if (existing) {
    return res.json({ success: true, request: existing });
  }

  const request = {
    id: `req-${Date.now()}`,
    fromId,
    fromName: from?.name || "Unknown User",
    toId,
    status: "pending"
  };

  friendRequests.push(request);
  res.status(201).json({ success: true, request });
});

app.post("/api/friend-requests/:requestId/accept", auth, (req: any, res) => {
  const request = friendRequests.find(r => r.id === req.params.requestId);

  if (!request) {
    return res.status(404).json({ message: "Friend request not found" });
  }

  request.status = "accepted";

  const chat = {
    id: request.fromId,
    name: request.fromName,
    type: "direct",
    lastMessage: "Say hi!",
    time: "Just now",
    unreadCount: 0,
    online: true
  };

  res.json({ success: true, chat });
});

app.post("/api/friend-requests/:requestId/reject", auth, (req, res) => {
  const request = friendRequests.find(r => r.id === req.params.requestId);

  if (!request) {
    return res.status(404).json({ message: "Friend request not found" });
  }

  request.status = "rejected";
  res.json({ success: true });
});

app.listen(5000, () => {
  console.log("API listening on http://localhost:5000/api");
});
```

## 17. Contoh Test Manual dengan cURL

### 17.1 Register

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"userId\":\"ada-77\",\"name\":\"Ada Lovelace\",\"email\":\"ada@example.com\",\"password\":\"Secret123\"}"
```

### 17.2 Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"ada@example.com\",\"password\":\"Secret123\"}"
```

Simpan token dari response.

### 17.3 Get Chats

```bash
curl http://localhost:5000/api/chats \
  -H "Authorization: Bearer <TOKEN>"
```

### 17.4 Get Members

```bash
curl http://localhost:5000/api/members \
  -H "Authorization: Bearer <TOKEN>"
```

### 17.5 Lookup User

```bash
curl http://localhost:5000/api/users/bob-99 \
  -H "Authorization: Bearer <TOKEN>"
```

### 17.6 Send Friend Request

```bash
curl -X POST http://localhost:5000/api/friend-requests \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"to\":\"bob-99\"}"
```

## 18. Checklist Integrasi Backend

Gunakan checklist ini agar FE langsung bisa jalan dengan BE.

- Buat endpoint `POST /auth/login`.
- Buat endpoint `POST /auth/register`.
- Pastikan response auth berisi `token` dan `user`.
- Set `user.id`, bukan hanya `user.userId`.
- Buat middleware JWT Bearer.
- Buat endpoint `GET /chats`.
- Buat endpoint `GET /members`.
- Buat endpoint `GET /friend-requests`.
- Buat endpoint `GET /users/:id`.
- Buat endpoint `POST /friend-requests`.
- Pastikan semua error punya field `message`.
- Pastikan semua success response berupa JSON.
- Aktifkan CORS untuk `http://localhost:3000`.
- Isi `.env` frontend dengan `VITE_API_URL=http://localhost:5000/api`.
- Restart frontend setelah mengubah `.env`.
- Test login dari UI.
- Test register dari UI.
- Test halaman `/chat` memuat chat, members, dan friend requests dari backend.
- Setelah REST stabil, aktifkan WebSocket untuk message realtime.

## 19. Urutan Implementasi yang Disarankan

1. Auth dulu: login dan register.
2. Middleware JWT.
3. `GET /chats`, `GET /members`, `GET /friend-requests`.
4. User lookup dan friend request.
5. Accept/reject friend request.
6. Message history.
7. Send message via REST atau WebSocket.
8. Realtime message, status delivered/read, online presence.
9. Integrasi halaman files.
10. Integrasi halaman members directory secara penuh.

## 20. Catatan Perubahan FE yang Mungkin Dibutuhkan Nanti

Beberapa hal sengaja belum diubah di kode sekarang, tetapi perlu dipertimbangkan saat backend makin lengkap:

- `Chat.tsx` belum fetch message history ketika `activeChat` berubah.
- `handleSendMessage` masih simulasi status `delivered` dan `read`.
- `handleAcceptFriendRequest` dan `handleRejectFriendRequest` masih belum memanggil API.
- `GroupChats.tsx`, `Files.tsx`, dan `Members.tsx` masih memakai mock data lokal.
- `api.ts` selalu parsing JSON, sehingga download file/blob perlu helper khusus.
- `time` saat ini string siap tampil. Backend production sebaiknya mengirim timestamp ISO dan FE memformatnya.

## 21. Kontrak Minimal Paling Penting

Jika backend ingin cepat tersambung ke FE saat ini, cukup penuhi kontrak ini:

```text
POST /auth/login
POST /auth/register
GET  /chats
GET  /members
GET  /friend-requests
GET  /users/:id
POST /friend-requests
```

Dengan response auth:

```json
{
  "token": "jwt-token",
  "user": {
    "id": "ada-77",
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "avatar": ""
  }
}
```

Dan semua endpoint privat menerima:

```http
Authorization: Bearer <token>
```
