"""
Implementasi algoritma Simhash 64-bit dari nol (tanpa library Simhash eksternal)
untuk Tugas A Forensic Text.

Langkah yang diimplementasikan:
- Langkah 1  : Normalisasi huruf kecil (memanggil modul text_processing)
- Langkah 2  : Segmentasi dokumen menjadi kalimat
- Langkah 3  : Pemberian ID kalimat (D1-K1, D1-K2, dst.)
- Langkah 4  : Pembentukan shingle unigram (dan opsi unigram + bigram)
- Langkah 5  : Perhitungan frekuensi shingle dalam kalimat sebagai bobot TF
- Langkah 6  : Hash deterministik menggunakan SHA-256 yang dipotong menjadi 64 bit
- Langkah 7  : Konversi hash menjadi representasi biner 64 bit dengan panjang tetap
- Langkah 8  : Pembentukan vektor akumulasi (+TF jika bit 1, -TF jika bit 0)
- Langkah 9  : Pembentukan fingerprint (komponen > 0 menjadi 1, <= 0 menjadi 0)
- Langkah 10 : Penyimpanan fingerprint beserta ID dan teks kalimatnya
- Langkah 12 : Perhitungan jarak Hamming menggunakan operasi XOR dan jumlah bit 1

Catatan terkait instruksi ambigu pada panduan:
- Fingerprint 64-bit asli (biner & desimal) serta jarak Hamming dasarnya selalu
  dipertahankan utuh tanpa operasi shift "2 >> B" yang belum terkonfirmasi maknanya.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
from typing import Dict, List, Tuple

from text_processing import create_shingles, normalize_text, segment_sentences


BIT_LENGTH_DEFAULT = 64


@dataclass
class TokenHashDetail:
    """Rincian proses hashing satu token/shingle untuk keperluan inspeksi pembelajaran."""

    token: str
    tf: int
    hash_dec: int
    hash_bin: str


@dataclass
class SentenceFingerprint:
    """Representasi lengkap satu kalimat beserta hasil Simhash-nya (Langkah 10)."""

    sentence_id: str
    doc_id: str
    index: int
    original_text: str
    normalized_text: str
    shingle_mode: str
    shingles: List[str]
    tf_weights: Dict[str, int]
    token_details: List[TokenHashDetail]
    accumulation_vector: List[int]
    fingerprint_bin: str
    fingerprint_dec: int
    bit_length: int = BIT_LENGTH_DEFAULT
    has_tokens: bool = True


def compute_tf(shingles: List[str]) -> Dict[str, int]:
    """
    Langkah 5: Menghitung frekuensi kemunculan (Term Frequency / TF) setiap token/shingle
    di dalam satu kalimat.
    """
    return dict(Counter(shingles))


def deterministic_hash_64bit(token: str, bit_length: int = BIT_LENGTH_DEFAULT) -> int:
    """
    Langkah 6: Menghasilkan hash deterministik menggunakan SHA-256 yang dipotong
    menjadi `bit_length` bit (baku: 64 bit).

    Mengapa tidak memakai hash() bawaan Python?
    Karena hash() bawaan Python menggunakan randomisasi seed (PYTHONHASHSEED) sehingga
    nilainya dapat berubah setiap kali proses Python dijalankan ulang.
    """
    if bit_length <= 0 or bit_length > 256:
        raise ValueError("bit_length harus berada pada rentang 1 sampai 256.")

    # Hitung digest SHA-256 penuh (256 bit / 32 byte) dalam encoding UTF-8.
    digest_bytes = hashlib.sha256(token.encode("utf-8")).digest()
    full_hash_int = int.from_bytes(digest_bytes, byteorder="big")

    # Ambil `bit_length` bit paling signifikan (untuk 64 bit = 8 byte pertama SHA-256).
    shift_amount = 256 - bit_length
    return full_hash_int >> shift_amount


def int_to_binary(value: int, bit_length: int = BIT_LENGTH_DEFAULT) -> str:
    """
    Langkah 7: Mengubah nilai integer menjadi string biner dengan panjang bit tetap
    (nol di depan tetap dipertahankan, misalnya selalu 64 karakter '0'/'1').
    """
    return format(value, f"0{bit_length}b")


def compute_accumulation_vector(
    tf_weights: Dict[str, int],
    bit_length: int = BIT_LENGTH_DEFAULT,
) -> Tuple[List[int], List[TokenHashDetail]]:
    """
    Langkah 7 & 8:
    - Ubah hash tiap token menjadi representasi biner sepanjang `bit_length` bit.
    - Bentuk vektor akumulasi sepanjang `bit_length`:
      * Jika bit ke-i bernilai '1', tambahkan bobot TF token tersebut (+TF).
      * Jika bit ke-i bernilai '0', kurangkan bobot TF token tersebut (-TF).
    """
    vector = [0] * bit_length
    token_details: List[TokenHashDetail] = []

    for token, tf in tf_weights.items():
        hash_dec = deterministic_hash_64bit(token, bit_length=bit_length)
        hash_bin = int_to_binary(hash_dec, bit_length=bit_length)
        token_details.append(
            TokenHashDetail(token=token, tf=tf, hash_dec=hash_dec, hash_bin=hash_bin)
        )

        # Akumulasi bobot TF pada setiap posisi bit (indeks 0 = MSB, indeks 63 = LSB).
        for idx, bit_char in enumerate(hash_bin):
            if bit_char == "1":
                vector[idx] += tf
            else:
                vector[idx] -= tf

    return vector, token_details


def vector_to_fingerprint(vector: List[int]) -> Tuple[str, int]:
    """
    Langkah 9:
    Membentuk fingerprint kalimat dari vektor akumulasi:
    - Komponen positif (> 0) -> bit '1'
    - Komponen nol atau negatif (<= 0) -> bit '0'

    Mengembalikan tuple (fingerprint_biner, fingerprint_desimal).
    """
    bits = ["1" if val > 0 else "0" for val in vector]
    fingerprint_bin = "".join(bits)
    fingerprint_dec = int(fingerprint_bin, 2) if fingerprint_bin else 0
    return fingerprint_bin, fingerprint_dec


def compute_sentence_simhash(
    sentence_id: str,
    doc_id: str,
    index: int,
    original_text: str,
    shingle_mode: str = "unigram",
    bit_length: int = BIT_LENGTH_DEFAULT,
) -> SentenceFingerprint:
    """
    Menjalankan seluruh tahapan Simhash (Langkah 1, 4–10) untuk satu kalimat
    dan menyimpan fingerprint beserta ID dan teks kalimatnya.
    """
    # Langkah 1: normalisasi huruf kecil.
    normalized = normalize_text(original_text)

    # Langkah 4: bentuk shingle (unigram atau unigram + bigram).
    shingles = create_shingles(normalized, mode=shingle_mode)

    # Langkah 5: hitung frekuensi token/shingle (TF).
    tf_weights = compute_tf(shingles)

    # Langkah 6–8: hash deterministik 64-bit, konversi biner, dan vektor akumulasi.
    vector, token_details = compute_accumulation_vector(tf_weights, bit_length=bit_length)

    # Langkah 9: konversi vektor akumulasi menjadi fingerprint biner dan desimal.
    fingerprint_bin, fingerprint_dec = vector_to_fingerprint(vector)

    # Langkah 10: simpan hasil lengkap beserta ID dan teks kalimat.
    return SentenceFingerprint(
        sentence_id=sentence_id,
        doc_id=doc_id,
        index=index,
        original_text=original_text,
        normalized_text=normalized,
        shingle_mode=shingle_mode,
        shingles=shingles,
        tf_weights=tf_weights,
        token_details=token_details,
        accumulation_vector=vector,
        fingerprint_bin=fingerprint_bin,
        fingerprint_dec=fingerprint_dec,
        bit_length=bit_length,
        has_tokens=len(shingles) > 0,
    )


def build_document_fingerprints(
    doc_id: str,
    document_text: str,
    shingle_mode: str = "unigram",
    bit_length: int = BIT_LENGTH_DEFAULT,
) -> List[SentenceFingerprint]:
    """
    Menjalankan Langkah 2–10 untuk satu dokumen utuh:
    segmentasi kalimat, pemberian ID (mis. D1-K1, D1-K2), dan perhitungan Simhash.
    """
    sentences = segment_sentences(document_text)
    results: List[SentenceFingerprint] = []

    for idx, sentence_text in enumerate(sentences, start=1):
        sentence_id = f"{doc_id}-K{idx}"
        fp = compute_sentence_simhash(
            sentence_id=sentence_id,
            doc_id=doc_id,
            index=idx,
            original_text=sentence_text,
            shingle_mode=shingle_mode,
            bit_length=bit_length,
        )
        results.append(fp)

    return results


def compute_hamming_details(
    fp_a: int,
    fp_b: int,
    bit_length: int = BIT_LENGTH_DEFAULT,
) -> Tuple[int, int, str]:
    """
    Langkah 12: Menghitung jarak Hamming antara dua fingerprint menggunakan:
    1. Operasi XOR bit-demi-bit (`fp_a ^ fp_b`) -> bit bernilai 1 jika kedua bit berbeda.
    2. Menghitung jumlah bit '1' pada hasil XOR.

    Mengembalikan tuple (jarak_hamming, nilai_xor_desimal, string_xor_biner).
    """
    xor_val = fp_a ^ fp_b
    xor_bin = int_to_binary(xor_val, bit_length=bit_length)
    distance = xor_val.bit_count()
    return distance, xor_val, xor_bin


def hamming_distance(fp_a: int, fp_b: int) -> int:
    """Fungsi ringkas untuk menghitung jarak Hamming dua fingerprint integer."""
    return (fp_a ^ fp_b).bit_count()
