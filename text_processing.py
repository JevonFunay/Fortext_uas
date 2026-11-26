"""
Modul pemrosesan teks untuk Tugas A Forensic Text (Deteksi Kemiripan Dokumen dengan Simhash).

Berisi fungsi untuk:
1. Memisahkan metadata artikel (judul, subjudul, penulis, redaktur, tanggal, URL, kategori)
   dan membersihkan elemen non-isi situs (label rubrik, subjudul bagian, iklan/baca juga jika ada)
   tanpa mengubah isi kalimat atau kutipan asli artikel.
2. Normalisasi teks (mengubah huruf menjadi kecil / lowercase) tanpa stemming dan tanpa
   menghapus stopword.
3. Segmentasi dokumen menjadi kalimat dengan mempertimbangkan tanda kutip dan domain situs.
4. Pembentukan shingle (unigram secara baku, serta opsi unigram + bigram).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple


# Pemetaan sumber resmi untuk lima dokumen korpus sesuai konteks tugas.
SUMBER_KORPUS_BAKU: Dict[str, str] = {
    "dokumen1.txt": "Pemprov Jateng",
    "dokumen2.txt": "Tirto",
    "dokumen3.txt": "InfoPublik",
    "dokumen4.txt": "Detik (detikJogja)",
    "dokumen5.txt": "Komdigi",
}

# Pola tanggal berbahasa Indonesia (nama hari/bulan, format WIB/WITA/WIT).
_POLA_BULAN_ID = (
    r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|"
    r"Oktober|November|Desember|Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Ags|Sep|Okt|Nov|Des)"
)
_RE_TANGGAL = re.compile(
    rf"^(?:Terbit\s+)?(?:(?:Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu),\s*)?"
    rf"\d{{1,2}}\s+{_POLA_BULAN_ID}\s+\d{{4}}(?:\s*[\|\-]?\s*\d{{1,2}}[:.]\d{{2}}\s*(?:WIB|WITA|WIT)?)?$",
    re.IGNORECASE,
)

# Pola URL jika muncul di teks artikel.
_RE_URL = re.compile(r"^(?:(?:Sumber|URL|Tautan)\s*:\s*)?(https?://\S+)$", re.IGNORECASE)

# Pola elemen non-isi situs yang umum terbawa saat salin-tempel dari web.
_RE_BOILERPLATE = re.compile(
    r"^(?:"
    r"baca\s+juga\s*:?.*|"
    r"lihat\s+juga\s*:?.*|"
    r"simak\s+juga\s*:?.*|"
    r"berita\s+terkait\s*:?.*|"
    r"artikel\s+terkait\s*:?.*|"
    r"iklan|advertisement|sponsored|"
    r"komentar\s*:?.*|"
    r"bagikan\s*:?.*|share\s*:?.*|"
    r"[•|·\-–—]+"
    r")$",
    re.IGNORECASE,
)

# Label bagian / subjudul struktural pendek tanpa tanda akhir kalimat.
_LABEL_BAGIAN_NON_ISI = {
    "penjelasan:",
    "penjelasan",
    "penelusuran fakta",
    "kesimpulan",
    "klarifikasi hoaks",
    "hoaks•",
    "hoaks",
    "•",
}

# Singkatan umum yang titiknya tidak menandai akhir kalimat.
_SINGKATAN_UMUM = {
    "dr",
    "drs",
    "prof",
    "ir",
    "no",
    "hlm",
    "hal",
    "dkk",
    "dsb",
    "dst",
    "dll",
    "yth",
    "tgl",
    "telp",
    "s.d",
    "a.n",
    "u.b",
    "pt",
    "cv",
    "tbk",
    "rp",
}


@dataclass
class CleanedDocumentResult:
    """Hasil pemisahan metadata dan pembersihan satu dokumen korpus."""

    doc_id: str
    filename: str
    sumber: str
    judul: str = ""
    subjudul: str = ""
    penulis: str = ""
    redaktur: str = ""
    tanggal: str = ""
    kategori: str = ""
    url: str = "Tidak tercantum pada file asli"
    elemen_non_isi_dipisahkan: List[str] = field(default_factory=list)
    teks_asli: str = ""
    teks_bersih: str = ""
    catatan: str = ""

    def to_metadata_dict(self) -> Dict[str, object]:
        """Mengubah metadata menjadi dictionary siap simpan ke JSON."""
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "sumber": self.sumber,
            "judul": self.judul,
            "subjudul": self.subjudul,
            "penulis": self.penulis,
            "redaktur": self.redaktur,
            "tanggal": self.tanggal,
            "kategori": self.kategori,
            "url": self.url,
            "elemen_non_isi_dipisahkan": self.elemen_non_isi_dipisahkan,
            "catatan": self.catatan,
        }


def _adalah_baris_penulis(baris: str) -> bool:
    """Memeriksa apakah baris pendek di awal dokumen merupakan informasi penulis/byline."""
    teks = baris.strip()
    if not teks or len(teks) > 80:
        return False
    rendah = teks.lower()
    if rendah.startswith(("oleh:", "penulis:", "reporter:", "tim ", "tim.")):
        return True
    # Pola byline seperti "Aditya Mardiastuti - detikJogja"
    if " - " in teks and len(teks.split()) <= 8 and not teks.endswith("."):
        return True
    return False


def _adalah_baris_redaktur(baris: str) -> bool:
    """Memeriksa apakah baris merupakan keterangan redaktur/editor."""
    rendah = baris.strip().lower()
    return rendah.startswith(("redaktur:", "editor:"))


def _adalah_baris_rubrik(baris: str) -> bool:
    """Memeriksa apakah baris merupakan label rubrik/kategori pendek di header situs."""
    rendah = baris.strip().lower()
    return rendah in {"klarifikasi hoaks", "•", "hoaks•", "hoaks", "cek fakta", "berita"}


def clean_and_extract_metadata(
    raw_text: str,
    doc_id: str,
    filename: str,
    sumber: Optional[str] = None,
) -> CleanedDocumentResult:
    """
    Memisahkan metadata (judul, subjudul, penulis, redaktur, tanggal, URL, kategori)
    dan elemen non-isi situs dari isi utama artikel.

    Prinsip penting:
    - Dokumen asli tidak diubah (fungsi ini hanya membaca string mentah).
    - Isi artikel dan kutipan asli dipertahankan apa adanya tanpa penulisan ulang
      atau peringkasan.
    """
    sumber_final = sumber or SUMBER_KORPUS_BAKU.get(filename, "Sumber tidak diketahui")
    hasil = CleanedDocumentResult(
        doc_id=doc_id,
        filename=filename,
        sumber=sumber_final,
        teks_asli=raw_text,
    )

    # Normalisasi akhiran baris Windows/Unix saja agar pemrosesan konsisten.
    baris_mentah = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    baris_terisi_pertama = next((i for i, b in enumerate(baris_mentah) if b.strip()), None)

    if baris_terisi_pertama is None:
        hasil.teks_bersih = ""
        hasil.catatan = "Dokumen kosong atau tidak berisi teks."
        return hasil

    # Cari batas blok header metadata pada 10 baris awal dokumen.
    batas_scan_header = min(len(baris_mentah), baris_terisi_pertama + 10)
    indeks_metadata_terakhir = baris_terisi_pertama
    ditemukan_penanda_meta = False

    for idx in range(baris_terisi_pertama, batas_scan_header):
        baris = baris_mentah[idx].strip()
        if not baris:
            continue
        if (
            _RE_URL.match(baris)
            or _RE_TANGGAL.match(baris)
            or _adalah_baris_penulis(baris)
            or _adalah_baris_redaktur(baris)
            or _adalah_baris_rubrik(baris)
        ):
            indeks_metadata_terakhir = idx
            ditemukan_penanda_meta = True

    # Ekstrak field metadata dari blok header.
    baris_header = (
        baris_mentah[baris_terisi_pertama : indeks_metadata_terakhir + 1]
        if ditemukan_penanda_meta
        else []
    )
    indeks_mulai_isi = (
        indeks_metadata_terakhir + 1 if ditemukan_penanda_meta else baris_terisi_pertama
    )

    kategori_terkumpul: List[str] = []
    for pos, baris_asli in enumerate(baris_header):
        baris = baris_asli.strip()
        if not baris:
            continue
        cocok_url = _RE_URL.match(baris)
        if cocok_url:
            hasil.url = cocok_url.group(1)
        elif _RE_TANGGAL.match(baris):
            hasil.tanggal = baris
        elif _adalah_baris_redaktur(baris):
            hasil.redaktur = re.sub(r"^(?:redaktur|editor)\s*:\s*", "", baris, flags=re.IGNORECASE).strip()
        elif _adalah_baris_penulis(baris):
            hasil.penulis = re.sub(
                r"^(?:oleh|penulis|reporter)\s*:\s*", "", baris, flags=re.IGNORECASE
            ).strip()
        elif _adalah_baris_rubrik(baris):
            hasil.elemen_non_isi_dipisahkan.append(baris)
            bersih_rubrik = baris.replace("•", "").strip()
            if bersih_rubrik and bersih_rubrik not in kategori_terkumpul:
                kategori_terkumpul.append(bersih_rubrik)
        elif pos == 0 and not hasil.judul:
            hasil.judul = baris
        elif not hasil.subjudul:
            # Baris ringkasan/subjudul di bawah judul sebelum penulis/tanggal (contoh: Tirto).
            hasil.subjudul = baris

    if kategori_terkumpul:
        hasil.kategori = " / ".join(kategori_terkumpul)

    # Saring elemen non-isi situs (label bagian, iklan, "baca juga", URL berdiri sendiri)
    # pada bagian isi tanpa mengubah kalimat artikel.
    baris_isi_bersih: List[str] = []
    for baris_asli in baris_mentah[indeks_mulai_isi:]:
        baris = baris_asli.strip()
        if not baris:
            if baris_isi_bersih and baris_isi_bersih[-1] != "":
                baris_isi_bersih.append("")
            continue

        cocok_url = _RE_URL.match(baris)
        if cocok_url:
            if hasil.url == "Tidak tercantum pada file asli":
                hasil.url = cocok_url.group(1)
            hasil.elemen_non_isi_dipisahkan.append(baris)
            continue

        if baris.lower() in _LABEL_BAGIAN_NON_ISI or _RE_BOILERPLATE.match(baris):
            hasil.elemen_non_isi_dipisahkan.append(baris)
            continue

        baris_isi_bersih.append(baris)

    # Hapus baris kosong di akhir.
    while baris_isi_bersih and baris_isi_bersih[-1] == "":
        baris_isi_bersih.pop()

    hasil.teks_bersih = "\n".join(baris_isi_bersih)

    # Susun catatan kelengkapan metadata agar transparan saat dicek.
    catatan_bagian: List[str] = []
    if hasil.url == "Tidak tercantum pada file asli":
        catatan_bagian.append("URL artikel tidak tercantum di dalam file .txt asli.")
    if not hasil.penulis:
        catatan_bagian.append("Nama penulis tidak tercantum secara eksplisit di file asli.")
    if not hasil.teks_bersih:
        catatan_bagian.append("Isi artikel kosong setelah pemisahan metadata.")
    hasil.catatan = " ".join(catatan_bagian) if catatan_bagian else "Metadata lengkap dan isi terbaca utuh."

    return hasil


def normalize_text(text: str) -> str:
    """
    Langkah 1 algoritma wajib:
    Normalisasi teks dengan mengubah semua huruf menjadi huruf kecil (lowercase)
    dan merapikan spasi berlebih.

    Catatan: Tidak melakukan stemming dan tidak menghapus stopword sesuai ketentuan.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _gabungkan_baris_kutipan_terpotong(teks: str) -> List[str]:
    """
    Mengelompokkan teks menjadi paragraf sekaligus menggabungkan baris yang terpotong
    di tengah tanda kutip terbuka (contoh pada dokumen4.txt baris kutipan multi-baris).
    """
    baris_list = teks.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    paragraf: List[str] = []
    buffer_baris: List[str] = []
    dalam_kutip_lurus = False
    kedalaman_kutip_lengkung = 0

    for baris_mentah in baris_list:
        baris = baris_mentah.strip()
        if not baris:
            if buffer_baris:
                paragraf.append(" ".join(buffer_baris))
                buffer_baris = []
                dalam_kutip_lurus = False
                kedalaman_kutip_lengkung = 0
            continue

        if buffer_baris and not (dalam_kutip_lurus or kedalaman_kutip_lengkung > 0):
            # Baris baru tanpa kutipan terbuka diperlakukan sebagai paragraf terpisah.
            paragraf.append(" ".join(buffer_baris))
            buffer_baris = []

        buffer_baris.append(baris)

        # Perbarui status tanda kutip lurus (") dan tanda kutip lengkung (“ ”).
        for ch in baris:
            if ch == '"':
                dalam_kutip_lurus = not dalam_kutip_lurus
            elif ch == "“":
                kedalaman_kutip_lengkung += 1
            elif ch == "”" and kedalaman_kutip_lengkung > 0:
                kedalaman_kutip_lengkung -= 1

    if buffer_baris:
        paragraf.append(" ".join(buffer_baris))

    return paragraf


def _adalah_titik_bukan_akhir_kalimat(paragraf: str, indeks_titik: int) -> bool:
    """
    Memeriksa apakah tanda titik pada posisi `indeks_titik` bukan akhir kalimat:
    - Bagian dari domain situs (mis. harianjogja.com) atau angka desimal (mis. 43.3)
      karena karakter tepat setelah titik bukan spasi/akhir teks/tanda kutip tutup.
    - Singkatan umum seperti Dr., No., dkk.
    """
    panjang = len(paragraf)
    if indeks_titik + 1 < panjang:
        berikutnya = paragraf[indeks_titik + 1]
        # Jika langsung diikuti huruf atau angka (contoh: harianjogja.com, 3.14), bukan akhir kalimat.
        if berikutnya.isalnum():
            return True

    # Periksa kata tepat sebelum titik apakah termasuk singkatan umum.
    kiri = paragraf[:indeks_titik]
    cocok_kata = re.search(r"([A-Za-z\.]+)$", kiri)
    if cocok_kata:
        kata_sebelum = cocok_kata.group(1).lower().strip(".")
        if kata_sebelum in _SINGKATAN_UMUM:
            return True

    return False


def segment_sentences(text: str) -> List[str]:
    """
    Langkah 2 algoritma wajib:
    Segmentasi dokumen menjadi daftar kalimat utuh.

    Aturan segmentasi yang dipakai:
    - Memisahkan antar-paragraf (baris kosong / baris baru di luar kutipan).
    - Di dalam paragraf, tanda akhir kalimat (`.`, `!`, `?`) memisahkan kalimat
      apabila berada di luar tanda kutip terbuka (`"..."` atau `“...”`), bukan bagian
      dari domain situs (`harianjogja.com`), dan bukan singkatan umum.
    - Kutipan utuh seperti `"Kalimat 1. Kalimat 2," ujar narasumber.` tetap dijaga
      sebagai satu kalimat agar konteks kutipan tidak terpecah menjadi fragmen.
    """
    if not text or not text.strip():
        return []

    kalimat_hasil: List[str] = []
    paragraf_list = _gabungkan_baris_kutipan_terpotong(text)

    for paragraf in paragraf_list:
        paragraf = re.sub(r"\s+", " ", paragraf).strip()
        if not paragraf:
            continue

        mulai = 0
        dalam_kutip_lurus = False
        kedalaman_kutip_lengkung = 0
        i = 0
        panjang = len(paragraf)

        while i < panjang:
            ch = paragraf[i]

            if ch == '"':
                dalam_kutip_lurus = not dalam_kutip_lurus
                i += 1
                continue
            if ch == "“":
                kedalaman_kutip_lengkung += 1
                i += 1
                continue
            if ch == "”":
                if kedalaman_kutip_lengkung > 0:
                    kedalaman_kutip_lengkung -= 1
                i += 1
                continue

            dalam_kutip = dalam_kutip_lurus or kedalaman_kutip_lengkung > 0

            if ch in ".!?" and not dalam_kutip:
                if ch == "." and _adalah_titik_bukan_akhir_kalimat(paragraf, i):
                    i += 1
                    continue

                # Serap tanda akhir berurutan (mis. "!." atau "...") dan tanda tutup (mis. ")", "”").
                akhir = i + 1
                while akhir < panjang and paragraf[akhir] in '.!?"”)\'':
                    if paragraf[akhir] == '"':
                        dalam_kutip_lurus = not dalam_kutip_lurus
                    elif paragraf[akhir] == "”" and kedalaman_kutip_lengkung > 0:
                        kedalaman_kutip_lengkung -= 1
                    akhir += 1

                # Pastikan diikuti spasi atau sudah mencapai akhir paragraf.
                if akhir >= panjang or paragraf[akhir].isspace():
                    potongan = paragraf[mulai:akhir].strip()
                    if potongan:
                        kalimat_hasil.append(potongan)
                    mulai = akhir
                    while mulai < panjang and paragraf[mulai].isspace():
                        mulai += 1
                    i = mulai
                    continue

            i += 1

        sisa = paragraf[mulai:].strip()
        if sisa:
            kalimat_hasil.append(sisa)

    return kalimat_hasil


def tokenize_unigrams(normalized_text: str) -> List[str]:
    """
    Mengambil daftar token unigram (huruf dan angka) dari teks yang sudah dinormalisasi.
    Urutan dan pengulangan token dipertahankan agar frekuensi (TF) dapat dihitung tepat.
    """
    if not normalized_text:
        return []
    return re.findall(r"[a-z0-9]+", normalized_text)


def create_shingles(normalized_text: str, mode: str = "unigram") -> List[str]:
    """
    Langkah 4 algoritma wajib:
    Membentuk shingle pada setiap kalimat.

    Mode yang didukung:
    - "unigram" (default, sesuai langkah wajib): setiap token kata/angka menjadi 1 shingle.
    - "unigram_bigram" (opsi tambahan terkait variasi di panduan): menggabungkan semua
      unigram dengan bigram berurutan ("kata_i kata_{i+1}").
    """
    unigram = tokenize_unigrams(normalized_text)
    if mode == "unigram":
        return unigram
    if mode == "unigram_bigram":
        bigram = [f"{unigram[i]} {unigram[i + 1]}" for i in range(len(unigram) - 1)]
        return unigram + bigram
    raise ValueError(f"Mode shingle tidak dikenal: {mode!r}. Gunakan 'unigram' atau 'unigram_bigram'.")
