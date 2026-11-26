"""
Modul perbandingan dokumen berbasis Simhash per kalimat untuk Tugas A Forensic Text.

Mencakup:
- Langkah 11: Membandingkan setiap kalimat dokumen A dengan setiap kalimat dokumen B.
- Langkah 12: Menghitung jarak Hamming via XOR dan jumlah bit 1.
- Langkah 13: Menandai pasangan kandidat dengan aturan ambang yang jelas (Jarak Hamming <= K).
- Bonus     : Pencocokan kalimat satu-ke-satu (one-to-one) agar satu kalimat tidak dihitung
              berulang kali, perhitungan persentase kemiripan (Sørensen-Dice berbasis kalimat),
              cakupan terhadap masing-masing dokumen, klasifikasi kategori kemiripan yang
              batasnya dapat disesuaikan, serta perbandingan seluruh pasangan unik (10 pasangan
              untuk 5 dokumen).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from simhash_core import (
    BIT_LENGTH_DEFAULT,
    SentenceFingerprint,
    build_document_fingerprints,
    compute_hamming_details,
)


# Batas kategori default (pilihan implementasi, BUKAN ketentuan resmi dosen, dapat diubah).
DEFAULT_DUPLICATE_MIN_PERCENT = 80.0
DEFAULT_NEAR_DUPLICATE_MIN_PERCENT = 30.0


@dataclass
class CorpusDocument:
    """Representasi satu dokumen korpus yang siap dibandingkan."""

    doc_id: str
    filename: str
    sumber: str
    judul: str
    text: str
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def display_label(self) -> str:
        """Label ringkas untuk ditampilkan di antarmuka."""
        return f"{self.doc_id} — {self.sumber} ({self.filename})"


@dataclass
class SentencePairComparison:
    """Hasil perbandingan satu pasang kalimat antara Dokumen A dan Dokumen B."""

    sentence_a: SentenceFingerprint
    sentence_b: SentenceFingerprint
    hamming_distance: int
    xor_value: int
    xor_bin: str
    is_candidate: bool
    is_matched_one_to_one: bool = False


@dataclass
class DocumentComparisonResult:
    """Ringkasan dan detail lengkap perbandingan dua dokumen."""

    doc_a: CorpusDocument
    doc_b: CorpusDocument
    threshold: int
    threshold_rule: str
    shingle_mode: str
    bit_length: int
    sentences_a: List[SentenceFingerprint]
    sentences_b: List[SentenceFingerprint]
    total_sentences_a: int
    total_sentences_b: int
    total_pairs_evaluated: int
    candidate_pairs: List[SentencePairComparison]
    matched_pairs: List[SentencePairComparison]
    candidate_pair_count: int
    matched_pair_count: int
    similarity_percent: float
    coverage_a_percent: float
    coverage_b_percent: float
    category: str
    duplicate_min_percent: float
    near_duplicate_min_percent: float
    is_same_document: bool
    is_empty_comparison: bool
    notice: str = ""


def classify_similarity(
    similarity_percent: float,
    duplicate_min_percent: float = DEFAULT_DUPLICATE_MIN_PERCENT,
    near_duplicate_min_percent: float = DEFAULT_NEAR_DUPLICATE_MIN_PERCENT,
    is_empty: bool = False,
) -> str:
    """
    Mengelompokkan persentase kemiripan ke dalam label interpretatif:
    - 'Duplikat'         : persentase >= duplicate_min_percent
    - 'Hampir Duplikat'  : near_duplicate_min_percent <= persentase < duplicate_min_percent
    - 'Kemiripan Rendah' : persentase < near_duplicate_min_percent

    Catatan: Batas kategori ini merupakan pilihan implementasi yang dapat disesuaikan,
    bukan ketentuan resmi dosen, dan bukan vonis plagiarisme.
    """
    if is_empty:
        return "Tidak Dapat Dihitung (Dokumen Kosong)"
    if similarity_percent >= duplicate_min_percent:
        return "Duplikat"
    if similarity_percent >= near_duplicate_min_percent:
        return "Hampir Duplikat"
    return "Kemiripan Rendah"


def match_one_to_one(
    candidate_pairs: List[SentencePairComparison],
) -> List[SentencePairComparison]:
    """
    Melakukan pencocokan kalimat satu-ke-satu (one-to-one) secara greedy berdasarkan
    jarak Hamming terkecil terlebih dahulu.

    Tujuan:
    - Mencegah satu kalimat di Dokumen A dihitung berulang kali karena mirip dengan
      beberapa kalimat sekaligus di Dokumen B (dan sebaliknya).
    - Pasangan dengan jarak Hamming paling kecil (paling mirip, misalnya 0) selalu
      diprioritaskan lebih dahulu.
    - Urutan pengikatan deterministik: (hamming_distance, indeks_A, indeks_B).
    """
    sorted_candidates = sorted(
        candidate_pairs,
        key=lambda p: (p.hamming_distance, p.sentence_a.index, p.sentence_b.index),
    )

    used_a = set()
    used_b = set()
    matched: List[SentencePairComparison] = []

    for pair in sorted_candidates:
        pair.is_matched_one_to_one = False

    for pair in sorted_candidates:
        id_a = pair.sentence_a.sentence_id
        id_b = pair.sentence_b.sentence_id
        if id_a not in used_a and id_b not in used_b:
            pair.is_matched_one_to_one = True
            used_a.add(id_a)
            used_b.add(id_b)
            matched.append(pair)

    return matched


def compare_documents(
    doc_a: CorpusDocument,
    doc_b: CorpusDocument,
    threshold: int = 3,
    shingle_mode: str = "unigram",
    bit_length: int = BIT_LENGTH_DEFAULT,
    duplicate_min_percent: float = DEFAULT_DUPLICATE_MIN_PERCENT,
    near_duplicate_min_percent: float = DEFAULT_NEAR_DUPLICATE_MIN_PERCENT,
    precomputed_a: Optional[List[SentenceFingerprint]] = None,
    precomputed_b: Optional[List[SentenceFingerprint]] = None,
) -> DocumentComparisonResult:
    """
    Membandingkan Dokumen A dan Dokumen B berdasarkan Simhash setiap kalimatnya.

    Aturan ambang:
    - Pasangan kalimat ditandai sebagai pasangan kandidat mirip apabila
      `jarak_hamming <= threshold`.

    Rumus persentase kemiripan utama (Sørensen-Dice berbasis pencocokan kalimat 1-ke-1):
        Persentase Kemiripan = (2 * M) / (N_A + N_B) * 100%
    dengan:
        M   = jumlah pasangan kalimat cocok satu-ke-satu (M <= min(N_A, N_B))
        N_A = jumlah kalimat Dokumen A
        N_B = jumlah kalimat Dokumen B

    Penanganan kasus khusus:
    - Jika salah satu atau kedua dokumen kosong (N_A == 0 atau N_B == 0), persentase
      ditetapkan 0.0% disertai keterangan jelas (tanpa pembagian nol).
    - Jika dua dokumen yang dipilih sama (doc_a.doc_id == doc_b.doc_id), perhitungan
      tetap berjalan dengan pemberitahuan eksplisit bahwa dokumen dibandingkan dengan
      dirinya sendiri.
    """
    if threshold < 0 or threshold > bit_length:
        raise ValueError(f"Ambang jarak Hamming harus berada pada rentang 0 sampai {bit_length}.")

    sentences_a = (
        precomputed_a
        if precomputed_a is not None
        else build_document_fingerprints(
            doc_id=doc_a.doc_id,
            document_text=doc_a.text,
            shingle_mode=shingle_mode,
            bit_length=bit_length,
        )
    )
    sentences_b = (
        precomputed_b
        if precomputed_b is not None
        else build_document_fingerprints(
            doc_id=doc_b.doc_id,
            document_text=doc_b.text,
            shingle_mode=shingle_mode,
            bit_length=bit_length,
        )
    )

    n_a = len(sentences_a)
    n_b = len(sentences_b)
    is_same_document = doc_a.doc_id == doc_b.doc_id
    is_empty = n_a == 0 or n_b == 0
    threshold_rule = f"Jarak Hamming <= {threshold}"

    notices: List[str] = []
    if is_empty:
        if n_a == 0 and n_b == 0:
            notices.append("Kedua dokumen kosong (0 kalimat), sehingga kemiripan tidak dapat dihitung.")
        elif n_a == 0:
            notices.append(f"Dokumen A ({doc_a.doc_id}) kosong (0 kalimat), sehingga kemiripan tidak dapat dihitung.")
        else:
            notices.append(f"Dokumen B ({doc_b.doc_id}) kosong (0 kalimat), sehingga kemiripan tidak dapat dihitung.")
    if is_same_document:
        notices.append(
            f"Anda membandingkan dokumen yang sama ({doc_a.doc_id} dengan {doc_b.doc_id}). "
            "Setiap kalimat identik dengan dirinya sendiri (jarak Hamming = 0)."
        )

    candidate_pairs: List[SentencePairComparison] = []
    total_pairs_evaluated = n_a * n_b

    # Langkah 11–13: bandingkan semua pasangan kalimat (A_i, B_j).
    if not is_empty:
        for sent_a in sentences_a:
            for sent_b in sentences_b:
                dist, xor_val, xor_bin = compute_hamming_details(
                    sent_a.fingerprint_dec,
                    sent_b.fingerprint_dec,
                    bit_length=bit_length,
                )
                if dist <= threshold:
                    candidate_pairs.append(
                        SentencePairComparison(
                            sentence_a=sent_a,
                            sentence_b=sent_b,
                            hamming_distance=dist,
                            xor_value=xor_val,
                            xor_bin=xor_bin,
                            is_candidate=True,
                            is_matched_one_to_one=False,
                        )
                    )

    # Urutkan kandidat dari jarak Hamming terkecil agar mudah dibaca.
    candidate_pairs.sort(
        key=lambda p: (p.hamming_distance, p.sentence_a.index, p.sentence_b.index)
    )

    # Pencocokan satu-ke-satu untuk mencegah penghitungan kalimat berulang.
    matched_pairs = match_one_to_one(candidate_pairs)
    m_matched = len(matched_pairs)

    if is_empty:
        similarity_percent = 0.0
        coverage_a = 0.0
        coverage_b = 0.0
    else:
        # Rumus Sørensen-Dice berbasis kalimat (simetris, selalu pada rentang 0%..100%).
        similarity_percent = (2.0 * m_matched / (n_a + n_b)) * 100.0
        coverage_a = (m_matched / n_a) * 100.0
        coverage_b = (m_matched / n_b) * 100.0

    category = classify_similarity(
        similarity_percent=similarity_percent,
        duplicate_min_percent=duplicate_min_percent,
        near_duplicate_min_percent=near_duplicate_min_percent,
        is_empty=is_empty,
    )

    return DocumentComparisonResult(
        doc_a=doc_a,
        doc_b=doc_b,
        threshold=threshold,
        threshold_rule=threshold_rule,
        shingle_mode=shingle_mode,
        bit_length=bit_length,
        sentences_a=sentences_a,
        sentences_b=sentences_b,
        total_sentences_a=n_a,
        total_sentences_b=n_b,
        total_pairs_evaluated=total_pairs_evaluated,
        candidate_pairs=candidate_pairs,
        matched_pairs=matched_pairs,
        candidate_pair_count=len(candidate_pairs),
        matched_pair_count=m_matched,
        similarity_percent=similarity_percent,
        coverage_a_percent=coverage_a,
        coverage_b_percent=coverage_b,
        category=category,
        duplicate_min_percent=duplicate_min_percent,
        near_duplicate_min_percent=near_duplicate_min_percent,
        is_same_document=is_same_document,
        is_empty_comparison=is_empty,
        notice=" ".join(notices),
    )


def compare_all_document_pairs(
    documents: List[CorpusDocument],
    threshold: int = 3,
    shingle_mode: str = "unigram",
    bit_length: int = BIT_LENGTH_DEFAULT,
    duplicate_min_percent: float = DEFAULT_DUPLICATE_MIN_PERCENT,
    near_duplicate_min_percent: float = DEFAULT_NEAR_DUPLICATE_MIN_PERCENT,
) -> List[DocumentComparisonResult]:
    """
    Membandingkan seluruh pasangan dokumen unik dalam korpus.
    Untuk 5 dokumen, menghasilkan C(5, 2) = 10 pasangan unik.
    """
    # Hitung fingerprint tiap dokumen sekali saja agar efisien dan konsisten.
    fingerprint_cache: Dict[str, List[SentenceFingerprint]] = {
        doc.doc_id: build_document_fingerprints(
            doc_id=doc.doc_id,
            document_text=doc.text,
            shingle_mode=shingle_mode,
            bit_length=bit_length,
        )
        for doc in documents
    }

    results: List[DocumentComparisonResult] = []
    for doc_a, doc_b in combinations(documents, 2):
        res = compare_documents(
            doc_a=doc_a,
            doc_b=doc_b,
            threshold=threshold,
            shingle_mode=shingle_mode,
            bit_length=bit_length,
            duplicate_min_percent=duplicate_min_percent,
            near_duplicate_min_percent=near_duplicate_min_percent,
            precomputed_a=fingerprint_cache[doc_a.doc_id],
            precomputed_b=fingerprint_cache[doc_b.doc_id],
        )
        results.append(res)

    return results
