"""
Skrip persiapan korpus untuk Tugas A Forensic Text.

Membaca lima dokumen korpus asli (`dokumen1.txt` sampai `dokumen5.txt`) di folder proyek
TANPA mengubah file asli, memisahkan metadata (judul, subjudul, penulis, redaktur, tanggal,
kategori, URL) serta elemen non-isi situs, lalu menyimpan hasil teks bersih dan metadata ke
folder terpisah `korpus_bersih/`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from comparison import CorpusDocument
from text_processing import (
    SUMBER_KORPUS_BAKU,
    CleanedDocumentResult,
    clean_and_extract_metadata,
)


PROJECT_DIR = Path(__file__).resolve().parent
CLEAN_CORPUS_DIR = PROJECT_DIR / "korpus_bersih"
METADATA_FILE = CLEAN_CORPUS_DIR / "metadata_korpus.json"

CORPUS_FILENAMES: List[str] = [
    "dokumen1.txt",
    "dokumen2.txt",
    "dokumen3.txt",
    "dokumen4.txt",
    "dokumen5.txt",
]


def prepare_clean_corpus(
    source_dir: Path = PROJECT_DIR,
    output_dir: Path = CLEAN_CORPUS_DIR,
) -> List[CleanedDocumentResult]:
    """
    Memproses lima dokumen korpus dari `source_dir` dan menyimpan teks bersih serta
    file metadata JSON ke `output_dir`. File asli tidak pernah disentuh/diubah.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cleaned_results: List[CleanedDocumentResult] = []
    metadata_records: List[Dict[str, object]] = []

    for idx, filename in enumerate(CORPUS_FILENAMES, start=1):
        doc_id = f"D{idx}"
        source_path = source_dir / filename
        if not source_path.exists():
            raise FileNotFoundError(
                f"Dokumen korpus asli tidak ditemukan: {source_path}"
            )

        raw_text = source_path.read_text(encoding="utf-8")
        cleaned = clean_and_extract_metadata(
            raw_text=raw_text,
            doc_id=doc_id,
            filename=filename,
            sumber=SUMBER_KORPUS_BAKU.get(filename),
        )

        # Simpan isi bersih ke folder terpisah `korpus_bersih/`.
        clean_file_path = output_dir / filename
        clean_file_path.write_text(cleaned.teks_bersih, encoding="utf-8")

        cleaned_results.append(cleaned)
        record = cleaned.to_metadata_dict()
        record["file_asli"] = str(source_path.name)
        record["file_bersih"] = f"{output_dir.name}/{filename}"
        metadata_records.append(record)

    metadata_path = output_dir / "metadata_korpus.json"
    metadata_path.write_text(
        json.dumps(metadata_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cleaned_results


def load_clean_corpus(
    source_dir: Path = PROJECT_DIR,
    clean_dir: Path = CLEAN_CORPUS_DIR,
) -> List[CorpusDocument]:
    """
    Memuat lima dokumen korpus bersih beserta metadatanya untuk dipakai oleh aplikasi.
    Jika folder `korpus_bersih/` belum tersedia, otomatis menjalankannya terlebih dahulu.
    """
    metadata_path = clean_dir / "metadata_korpus.json"
    if not metadata_path.exists():
        prepare_clean_corpus(source_dir=source_dir, output_dir=clean_dir)

    metadata_records = json.loads(metadata_path.read_text(encoding="utf-8"))
    documents: List[CorpusDocument] = []

    for rec in metadata_records:
        filename = str(rec["filename"])
        clean_path = clean_dir / filename
        raw_path = source_dir / filename
        clean_text = clean_path.read_text(encoding="utf-8") if clean_path.exists() else ""
        raw_text = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""

        meta_with_raw = dict(rec)
        meta_with_raw["teks_asli"] = raw_text

        documents.append(
            CorpusDocument(
                doc_id=str(rec["doc_id"]),
                filename=filename,
                sumber=str(rec.get("sumber", "")),
                judul=str(rec.get("judul", "")),
                text=clean_text,
                metadata=meta_with_raw,
            )
        )

    return documents


if __name__ == "__main__":
    hasil_list = prepare_clean_corpus()
    print(f"Berhasil menyiapkan {len(hasil_list)} dokumen bersih di: {CLEAN_CORPUS_DIR}")
    for item in hasil_list:
        print(
            f"- {item.doc_id} ({item.filename} | {item.sumber}): "
            f"judul={item.judul!r}, tanggal={item.tanggal!r}, penulis={item.penulis!r}, "
            f"non_isi={item.elemen_non_isi_dipisahkan}"
        )
