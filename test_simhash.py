"""
Pengujian otomatis (unit test) untuk memverifikasi ketepatan implementasi Simhash
dan modul perbandingan dokumen Tugas A Forensic Text.

Menjalankan pengujian:
    python -m unittest test_simhash.py -v
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from comparison import (
    CorpusDocument,
    compare_all_document_pairs,
    compare_documents,
    match_one_to_one,
)
from prepare_corpus import CLEAN_CORPUS_DIR, PROJECT_DIR, load_clean_corpus
from simhash_core import (
    BIT_LENGTH_DEFAULT,
    build_document_fingerprints,
    compute_hamming_details,
    compute_sentence_simhash,
    deterministic_hash_64bit,
    hamming_distance,
)
from text_processing import create_shingles, normalize_text, segment_sentences


class TestSimhashAndComparison(unittest.TestCase):
    """Kumpulan pengujian utama sesuai daftar pemeriksaan kualitas tugas."""

    def test_identical_text_same_fingerprint_and_zero_hamming(self) -> None:
        """Teks identik (termasuk beda huruf kapital) harus menghasilkan fingerprint sama & Hamming 0."""
        kalimat_1 = "Sri Sultan Hamengkubuwono X tidak menghentikan program MBG di DIY."
        kalimat_2 = "SRI SULTAN HAMENGKUBUWONO X TIDAK MENGHENTIKAN PROGRAM MBG DI DIY."

        fp1 = compute_sentence_simhash("D1-K1", "D1", 1, kalimat_1, shingle_mode="unigram")
        fp2 = compute_sentence_simhash("D2-K1", "D2", 1, kalimat_2, shingle_mode="unigram")

        self.assertEqual(len(fp1.fingerprint_bin), BIT_LENGTH_DEFAULT)
        self.assertEqual(fp1.fingerprint_bin, fp2.fingerprint_bin)
        self.assertEqual(fp1.fingerprint_dec, fp2.fingerprint_dec)
        self.assertEqual(hamming_distance(fp1.fingerprint_dec, fp2.fingerprint_dec), 0)

        dist, xor_val, xor_bin = compute_hamming_details(fp1.fingerprint_dec, fp2.fingerprint_dec)
        self.assertEqual(dist, 0)
        self.assertEqual(xor_val, 0)
        self.assertEqual(xor_bin, "0" * BIT_LENGTH_DEFAULT)

    def test_fingerprint_consistent_across_processes(self) -> None:
        """Fingerprint harus identik antarproses Python meskipun PYTHONHASHSEED berbeda."""
        sample_text = "Faktanya, pernyataan tersebut bukan merupakan kebijakan Sri Sultan Hamengkubuwono X."
        expected = compute_sentence_simhash("D1-K1", "D1", 1, sample_text).fingerprint_dec

        code = (
            "from simhash_core import compute_sentence_simhash; "
            f"fp = compute_sentence_simhash('D1-K1', 'D1', 1, {sample_text!r}); "
            "print(f'{fp.fingerprint_dec}|{fp.fingerprint_bin}')"
        )

        outputs = []
        for seed in ("1", "42", "999999"):
            env = {"PYTHONHASHSEED": seed}
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(PROJECT_DIR),
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            outputs.append(proc.stdout.strip())

        self.assertEqual(len(set(outputs)), 1)
        dec_str, bin_str = outputs[0].split("|")
        self.assertEqual(int(dec_str), expected)
        self.assertEqual(len(bin_str), 64)

    def test_one_to_one_matching_prevents_double_counting(self) -> None:
        """
        Satu kalimat di Dokumen A yang mirip dengan beberapa kalimat di Dokumen B
        tidak boleh dihitung berulang kali pada persentase kemiripan.
        """
        doc_a = CorpusDocument(
            doc_id="A",
            filename="a.txt",
            sumber="Uji A",
            judul="Uji A",
            text="Program makan bergizi gratis berjalan di Yogyakarta.",
        )
        # Tiga kalimat identik di Dokumen B -> semua 3 jadi pasangan kandidat terhadap A-K1,
        # tetapi pencocokan 1-ke-1 hanya boleh menghitung M = 1!
        doc_b = CorpusDocument(
            doc_id="B",
            filename="b.txt",
            sumber="Uji B",
            judul="Uji B",
            text=(
                "Program makan bergizi gratis berjalan di Yogyakarta. "
                "Program makan bergizi gratis berjalan di Yogyakarta. "
                "Program makan bergizi gratis berjalan di Yogyakarta."
            ),
        )

        result = compare_documents(doc_a, doc_b, threshold=3)
        self.assertEqual(result.total_sentences_a, 1)
        self.assertEqual(result.total_sentences_b, 3)
        self.assertEqual(result.candidate_pair_count, 3)
        self.assertEqual(result.matched_pair_count, 1)
        # Rumus Dice: (2 * 1) / (1 + 3) * 100 = 50.0%
        self.assertAlmostEqual(result.similarity_percent, 50.0, places=4)
        self.assertLessEqual(result.similarity_percent, 100.0)

        # Pastikan tidak ada ID kalimat yang dipakai lebih dari sekali pada matched_pairs.
        used_a = [p.sentence_a.sentence_id for p in result.matched_pairs]
        used_b = [p.sentence_b.sentence_id for p in result.matched_pairs]
        self.assertEqual(len(used_a), len(set(used_a)))
        self.assertEqual(len(used_b), len(set(used_b)))

    def test_empty_document_handling(self) -> None:
        """Dokumen kosong (salah satu atau keduanya) harus ditangani aman tanpa error."""
        doc_empty = CorpusDocument("E1", "kosong.txt", "Uji", "Kosong", "")
        doc_non_empty = CorpusDocument(
            "N1", "isi.txt", "Uji", "Isi", "Kalimat pertama untuk uji dokumen kosong."
        )

        res1 = compare_documents(doc_empty, doc_non_empty, threshold=3)
        self.assertTrue(res1.is_empty_comparison)
        self.assertEqual(res1.similarity_percent, 0.0)
        self.assertEqual(res1.matched_pair_count, 0)
        self.assertIn("Kosong", res1.category)

        res2 = compare_documents(doc_empty, doc_empty, threshold=3)
        self.assertTrue(res2.is_empty_comparison)
        self.assertTrue(res2.is_same_document)
        self.assertEqual(res2.similarity_percent, 0.0)

    def test_same_document_comparison_handled(self) -> None:
        """Membandingkan dua dokumen yang sama ditandai is_same_document dan menghasilkan 100%."""
        docs = load_clean_corpus()
        res = compare_documents(docs[0], docs[0], threshold=0)
        self.assertTrue(res.is_same_document)
        self.assertEqual(res.matched_pair_count, res.total_sentences_a)
        self.assertAlmostEqual(res.similarity_percent, 100.0, places=4)
        self.assertTrue(all(p.hamming_distance == 0 for p in res.matched_pairs))

    def test_corpus_five_documents_ten_unique_pairs(self) -> None:
        """Korpus 5 dokumen harus menghasilkan 10 pasangan unik dan D1/D3/D5 identik (100%)."""
        docs = load_clean_corpus()
        self.assertEqual(len(docs), 5)

        all_pairs = compare_all_document_pairs(docs, threshold=3, shingle_mode="unigram")
        self.assertEqual(len(all_pairs), 10)

        by_key = {(r.doc_a.doc_id, r.doc_b.doc_id): r for r in all_pairs}
        # D1 (Pemprov Jateng), D3 (InfoPublik), dan D5 (Komdigi) berisi teks penjelasan identik.
        for pair_key in (("D1", "D3"), ("D1", "D5"), ("D3", "D5")):
            res = by_key[pair_key]
            self.assertAlmostEqual(res.similarity_percent, 100.0, places=4)
            self.assertEqual(res.matched_pair_count, 6)
            self.assertTrue(all(p.hamming_distance == 0 for p in res.matched_pairs))

        # Pastikan tidak ada stopword yang dihapus dan tidak ada stemming pada tokenisasi.
        sample_tokens = create_shingles(normalize_text("Di media sosial yang beredar."), mode="unigram")
        self.assertIn("di", sample_tokens)
        self.assertIn("yang", sample_tokens)
        self.assertIn("beredar", sample_tokens)

        # Pastikan opsi unigram + bigram juga berfungsi dan menghasilkan bigram berurutan.
        unigram_bigram = create_shingles(normalize_text("dana mbg pendidikan"), mode="unigram_bigram")
        self.assertEqual(
            unigram_bigram,
            ["dana", "mbg", "pendidikan", "dana mbg", "mbg pendidikan"],
        )

    def test_original_files_preserved_and_clean_folder_exists(self) -> None:
        """File asli dokumen1..5.txt harus tetap ada dan hasil bersih tersimpan di folder terpisah."""
        self.assertTrue(CLEAN_CORPUS_DIR.is_dir())
        for i in range(1, 6):
            orig = PROJECT_DIR / f"dokumen{i}.txt"
            clean = CLEAN_CORPUS_DIR / f"dokumen{i}.txt"
            self.assertTrue(orig.is_file(), f"File asli hilang: {orig}")
            self.assertTrue(clean.is_file(), f"File bersih hilang: {clean}")
            self.assertGreater(len(clean.read_text(encoding="utf-8").strip()), 0)

    def test_domain_and_quotes_not_broken_in_segmentation(self) -> None:
        """Domain situs (harianjogja.com) dan tanda baca dalam kutipan tidak memecah kalimat."""
        sample = (
            'Unggahan disertai narasi “SRI SULTAN X. MINTA DIHENTIKAN!. Dana Dialihkan”. '
            'Dilansir dari harianjogja.com, tuntutan disampaikan demonstran.'
        )
        sents = segment_sentences(sample)
        self.assertEqual(len(sents), 2)
        self.assertIn("harianjogja.com", sents[1])


if __name__ == "__main__":
    unittest.main()
