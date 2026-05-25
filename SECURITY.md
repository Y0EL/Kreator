# Kebijakan Keamanan

Dokumen ini menjelaskan cara melaporkan kerentanan pada Crawler Konten, proyek editorial milik Yoel, dan cara proyek ini menangani keamanan serta data pribadi. Kebijakan mengikuti praktik pengungkapan kerentanan terkoordinasi dan standar yang berlaku.

## Lingkup

Yang termasuk dalam lingkup pelaporan keamanan.

- Backend FastAPI dan endpoint dashboard
- Bot Telegram dan jalur webhook
- Penanganan token, kredensial, dan rahasia
- Logika otorisasi pemilik pada agen admin

Yang berada di luar lingkup.

- Layanan pihak ketiga seperti Fly, Neon, Cloudflare, OpenAI, dan Telegram, yang punya program keamanannya sendiri
- Serangan rekayasa sosial terhadap pemilik
- Pengujian penolakan layanan dengan volume tinggi yang dapat mengganggu layanan

## Cara melaporkan

Laporkan dugaan kerentanan secara privat melalui surel ke yoelandreasmanoppo@gmail.com. Jangan membuka isu publik sebelum masalah selesai diperbaiki.

Agar laporan dapat ditindaklanjuti dengan cepat, sertakan hal berikut.

- Deskripsi singkat dan dampak yang mungkin terjadi
- Langkah untuk mereproduksi, sejelas mungkin
- Berkas, endpoint, atau komponen yang terpengaruh
- Bukti konsep bila ada, dalam bentuk yang aman
- Tingkat keparahan menurut perkiraan Anda

Bila perlu mengirim data sensitif, mintalah kunci enkripsi terlebih dahulu, atau pakai kanal yang sudah memakai HTTPS untuk pengiriman laporan.

## Pengungkapan terkoordinasi

Proyek ini menganut pengungkapan kerentanan terkoordinasi. Target waktu di bawah ini bersifat upaya terbaik karena proyek dikelola satu orang.

| Tahap | Target waktu |
| --- | --- |
| Konfirmasi penerimaan laporan | 3 hari kerja |
| Penilaian awal dan tingkat keparahan | 7 hari kerja |
| Perbaikan atau rencana mitigasi | bergantung tingkat keparahan |
| Pengungkapan publik | setelah perbaikan tersedia, atas kesepakatan |

Kami menghargai pelapor yang memberi waktu wajar untuk memperbaiki sebelum publikasi. Atas izin, nama pelapor dapat dicantumkan sebagai ucapan terima kasih.

## Pelindung niat baik

Riset keamanan yang dilakukan dengan itikad baik dan mematuhi kebijakan ini tidak akan kami anggap sebagai tindakan jahat. Tetap dalam lingkup, hindari mengakses data milik orang lain, jangan merusak data, dan hentikan pengujian begitu sebuah kerentanan ditemukan lalu laporkan.

## Penanganan rahasia

Proyek ini menyimpan kredensial sensitif, mencakup kunci OpenAI, sandi basis data Neon, token bot Telegram, dan kunci Cloudflare R2.

- Semua rahasia berada dalam berkas lingkungan yang diabaikan oleh git dan tidak pernah dikomit
- Rahasia produksi disimpan sebagai secret pada Fly, bukan di dalam kode
- Berkas kunci akun layanan disimpan di folder yang diabaikan oleh git
- Bila sebuah token diduga bocor, segera putar token tersebut dan cabut yang lama

## Privasi dan kepatuhan

Penanganan data pribadi mengacu pada Undang Undang Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi, yang berlaku penuh sejak Oktober 2024. Prinsip yang dipegang.

- Minimalkan data. Proyek hanya menyimpan cerita publik dan satu identitas pemilik untuk otorisasi
- Langkah pengamanan teknis dan operasional yang sepadan dengan risiko, selaras dengan Pasal 35 undang undang tersebut
- Bila terjadi insiden yang menyentuh data pribadi, lakukan penanganan dan pemberitahuan sesuai ketentuan yang berlaku
- Permintaan subjek data, seperti akses atau penghapusan, ditangani secepatnya dalam batas waktu yang diatur

## Berkas security.txt

Sesuai RFC 9116, sebuah berkas security.txt dapat disajikan pada path .well-known agar peneliti mudah menemukan kanal pelaporan. Contoh isi.

```text
Contact: mailto:yoelandreasmanoppo@gmail.com
Expires: 2027-05-25T00:00:00.000Z
Preferred-Languages: id, en
Canonical: https://konten-yoel.fly.dev/.well-known/security.txt
```

Bidang Contact dan Expires wajib ada. Perbarui tanggal Expires sebelum kedaluwarsa agar isinya tetap dianggap sah.

## Standar acuan

- RFC 9116, format berkas untuk membantu pengungkapan kerentanan
- ISO/IEC 29147, pengungkapan kerentanan
- ISO/IEC 30111, penanganan kerentanan
- OWASP Vulnerability Disclosure Cheat Sheet
- Undang Undang Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi
