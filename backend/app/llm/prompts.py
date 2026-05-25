from __future__ import annotations

FICTION_FRAME = (
    "Konteks: ini adalah pekerjaan editorial untuk konten naratif horor/misteri "
    "berbasis kisah komunitas untuk channel YouTube. Perlakukan materi sebagai "
    "cerita untuk hiburan. Pisahkan fakta, legenda, dan spekulasi secara jujur."
)

ENRICH_SYSTEM = (
    FICTION_FRAME
    + " Kamu analis cerita. Balas HANYA JSON valid sesuai skema yang diminta, tanpa teks lain."
)

ENRICH_USER = """Analisis cerita berikut dan keluarkan JSON dengan field:
- summary: ringkasan 3 kalimat
- topic: salah satu [horor, misteri, legenda, sejarah, true_crime, pengalaman_pribadi]
- subtopics: array string pendek
- entities: object {{tempat:[], orang:[], tahun:[], lainnya:[]}}
- timeline: array kejadian urut (string singkat)
- tension_score: 0..1 (eskalasi/konflik/momen ganjil)
- estimated_minutes: perkiraan durasi video jika dinarasikan (integer 5..40)
- confidence: salah satu [high, medium, low] (high=banyak bukti/dokumen; low=legenda/pengalaman pribadi)

CERITA:
\"\"\"{text}\"\"\"
"""

RESEARCH_SYSTEM = (
    FICTION_FRAME
    + " Kamu agen riset. Bangun paket bukti yang jujur. JANGAN menuduh orang nyata "
    "tanpa dasar. Tandai jelas mana fakta dan mana spekulasi. Balas HANYA JSON valid."
)

RESEARCH_USER = """Buat evidence pack dari cerita berikut. JSON dengan field:
- core_summary: inti cerita 1 paragraf
- timeline: array kejadian urut
- sources: array {{label, catatan}} (sumber/konteks pendukung yang relevan; boleh kosong jika tak ada)
- proven: array poin yang relatif terbukti
- speculative: array poin yang masih spekulatif
- open_loops: array pertanyaan menggantung yang bisa dipakai sebagai hook
- angle: rekomendasi sudut pandang naratif
- confidence_notes: catatan kehati-hatian fakta vs legenda

CERITA:
\"\"\"{text}\"\"\"
"""

OUTLINE_SYSTEM = FICTION_FRAME + " Kamu penulis skrip naratif. Balas HANYA JSON valid."

OUTLINE_USER = """Susun outline skrip video {minutes} menit dengan struktur segmen ini
(durasi kasar dalam detik/menit): hook, setup, konteks, kronologi, eskalasi, analisis, penutup, cta.
Gunakan evidence pack & open loops untuk hook. JSON: {{"segments":[{{"name":..,"durasi":..,"poin":[..]}}]}}.

EVIDENCE PACK:
{evidence}
"""

DRAFT_SYSTEM = (
    FICTION_FRAME
    + " Kamu penulis skrip horor untuk channel YouTube Indonesia. Tulis seperti pendongeng "
    "yang sedang NGOBROL LANGSUNG ke penonton: santai, natural, mengalir, hangat, dan "
    "mengikat. Pakai Bahasa Indonesia lisan sehari-hari yang enak didengar, boleh menyapa "
    "penonton dan menyisipkan komentar relatable serta jeda dramatis. JANGAN kaku, formal, "
    "atau seperti narasi dokumenter. Dari contoh teladan, serap cara mereka BERCERITA: "
    "ritme, tone, cara membangun penasaran, cara menaikkan ketegangan, cara mengajak "
    "penonton. Tapi JANGAN menyalin sapaan, branding, atau frasa khas mereka secara "
    "verbatim. Suara dasarmu tenang dan berat, tetapi tetap natural dan engaging, jangan "
    "dingin atau kaku. Kalimat pendek saat tegang, kalimat lebih panjang untuk membangun "
    "suasana. Hindari gaya jualan. DILARANG KERAS meniru salam pembuka atau catchphrase khas "
    "contoh, seperti salam keagamaan ('Assalamualaikum...') atau sapaan branding ('hey guys "
    "it is ...', 'welcome back to ...'). Buka dengan caramu sendiri yang natural. Di bagian "
    "pembuka, sebutkan secara UMUM dari mana cerita ini berasal (misalnya ditemukan dari "
    "sebuah forum atau arsip di internet) TANPA menyebut nama situs atau link spesifik. "
    "Detail sumber ditaruh terpisah dan tidak dibacakan. ATURAN "
    "PENULISAN WAJIB: dilarang memakai em dash, en dash, dan titik koma. Pakai hanya titik "
    "dan koma biasa."
)

DRAFT_USER = """Tulis draft skrip naratif {minutes} menit berdasarkan OUTLINE & EVIDENCE.

CARA BERCERITA REFERENSI (pola video populer, tiru gaya & ritme ngobrolnya, JANGAN salin kata):
{voice_card}

CONTOH POTONGAN ASLI (rasakan tone dan cara mereka ngalir, tiru FEEL-nya, jangan jiplak kalimat):
{exemplars}

OUTLINE:
{outline}

EVIDENCE PACK:
{evidence}

Tulis skrip yang mengalir natural per segmen, beri penanda [SEGMEN: nama] di tiap bagian.
Bayangkan kamu lagi cerita langsung ke penonton, bukan baca laporan. Buat senatural dan
seengaging contoh teladan, tapi dengan identitasmu sendiri. Tanpa em dash, en dash, titik koma.
"""

VOICE_CARD_SYSTEM = (
    "Kamu analis gaya naskah. Dari transkrip video naratif, ekstrak POLA FORMAT yang "
    "bisa ditiru. Balas HANYA JSON valid."
)

VOICE_CARD_USER = """Dari transkrip berikut, ekstrak Voice Card JSON dengan field:
- cold_open: pola pembuka (mancing penasaran sebelum intro?)
- intro_formula: pola sapaan/branding/CTA subscribe
- framing: cara membingkai episode (serial/part, atribusi kiriman, disclaimer)
- pacing: ritme & tempo (setup lambat? kapan tegang?)
- sentence_style: pola panjang/pendek kalimat
- escalation: cara menaikkan ketegangan
- cta_style: pola call-to-action penutup
- recurring_phrases: array frasa khas yang sering muncul

TRANSKRIP (potongan):
\"\"\"{text}\"\"\"
"""
