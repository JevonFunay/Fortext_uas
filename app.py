"""
Antarmuka Streamlit modern, minimalis, mudah dikustomisasi, dan ramah pengguna awam
untuk Tugas A Forensic Text: Deteksi Dokumen Duplikat/Hampir Duplikat dengan Simhash 64-bit.

Seluruh token warna, tipografi, label, dan preset UI dikelola terpusat di `ui_theme.py`.

Menjalankan aplikasi:
    python -m streamlit run app.py
"""

from __future__ import annotations

import html
import sys
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from comparison import (
    DEFAULT_DUPLICATE_MIN_PERCENT,
    DEFAULT_NEAR_DUPLICATE_MIN_PERCENT,
    CorpusDocument,
    DocumentComparisonResult,
    SentencePairComparison,
    compare_all_document_pairs,
    compare_documents,
)
from prepare_corpus import load_clean_corpus
from simhash_core import BIT_LENGTH_DEFAULT, SentenceFingerprint, build_document_fingerprints
from ui_theme import (
    APP_CONFIG,
    THEME_PRESETS,
    ThemePalette,
    build_theme_css,
    render_brand_header_html,
    render_how_it_works_html,
    render_kpi_strip_html,
    render_section_header_html,
    render_verdict_card_html,
    svg_icon,
)


SHINGLE_MODE_LABELS: Dict[str, str] = {
    "unigram": "Unigram — Per 1 Kata (Baku)",
    "unigram_bigram": "Unigram + Bigram (Opsi Panduan)",
}


def _describe_k(k: int) -> str:
    """Penjelasan singkat bahasa sehari-hari untuk nilai ambang jarak Hamming K."""
    if k == 0:
        return "Hanya kalimat dengan sidik jari 100% sama persis."
    if k <= 4:
        return "Ketat / standar — cocok untuk salinan langsung atau beda sangat kecil."
    if k <= 12:
        return "Sedang / longgar — menangkap kalimat mirip yang beda beberapa kata."
    return "Sangat longgar — banyak bit berbeda ditoleransi (rawan cocok kebetulan)."


def _set_threshold_preset(value: int) -> None:
    """Callback untuk menyinkronkan tombol preset dengan slider Ambang Jarak Hamming."""
    st.session_state["hamming_k"] = value


def _build_fingerprint_df(
    sentences: List[SentenceFingerprint],
    sort_by_decimal: bool = False,
) -> pd.DataFrame:
    """Menyusun tabel kalimat beserta fingerprint biner 64-bit dan desimal presisi penuh."""
    ordered = (
        sorted(sentences, key=lambda s: (s.fingerprint_dec, s.index))
        if sort_by_decimal
        else list(sentences)
    )
    return pd.DataFrame(
        [
            {
                "ID Kalimat": s.sentence_id,
                "Teks Kalimat": s.original_text,
                "Fingerprint Biner (64-bit)": s.fingerprint_bin,
                # Disimpan sebagai string agar angka 64-bit tidak dibulatkan di browser.
                "Fingerprint Desimal": str(s.fingerprint_dec),
            }
            for s in ordered
        ]
    )


def _find_closest_pair(
    sentences_a: List[SentenceFingerprint],
    sentences_b: List[SentenceFingerprint],
) -> Optional[Tuple[int, str, str]]:
    """Mencari jarak Hamming terkecil di antara dua dokumen untuk informasi bantu."""
    if not sentences_a or not sentences_b:
        return None
    best_dist = BIT_LENGTH_DEFAULT + 1
    best_a, best_b = "", ""
    for sa in sentences_a:
        for sb in sentences_b:
            dist = (sa.fingerprint_dec ^ sb.fingerprint_dec).bit_count()
            if dist < best_dist:
                best_dist, best_a, best_b = dist, sa.sentence_id, sb.sentence_id
    return best_dist, best_a, best_b


def _render_side_by_side_sentences(res: DocumentComparisonResult) -> None:
    """Menampilkan kalimat Dokumen A dan B berdampingan dengan penanda warna lembut."""
    matched_a: Dict[str, SentencePairComparison] = {
        p.sentence_a.sentence_id: p for p in res.matched_pairs
    }
    matched_b: Dict[str, SentencePairComparison] = {
        p.sentence_b.sentence_id: p for p in res.matched_pairs
    }
    cand_a = {p.sentence_a.sentence_id for p in res.candidate_pairs}
    cand_b = {p.sentence_b.sentence_id for p in res.candidate_pairs}

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**{res.doc_a.doc_id} — {res.doc_a.sumber}** ({res.total_sentences_a} kalimat)")
        if not res.sentences_a:
            st.info("Dokumen A kosong (0 kalimat).")
        for s in res.sentences_a:
            if s.sentence_id in matched_a:
                p = matched_a[s.sentence_id]
                cls = "ft-sent ft-sent--match"
                meta = f"{s.sentence_id}  •  Cocok dengan {p.sentence_b.sentence_id} (selisih {p.hamming_distance} bit)"
            elif s.sentence_id in cand_a:
                cls = "ft-sent ft-sent--cand"
                meta = f"{s.sentence_id}  •  Kandidat tambahan (tidak dihitung ulang)"
            else:
                cls = "ft-sent"
                meta = s.sentence_id
            st.markdown(
                f'<div class="{cls}">'
                f'<div class="ft-sent-meta">{html.escape(meta)}</div>'
                f"<div>{html.escape(s.original_text)}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    with col_b:
        st.markdown(f"**{res.doc_b.doc_id} — {res.doc_b.sumber}** ({res.total_sentences_b} kalimat)")
        if not res.sentences_b:
            st.info("Dokumen B kosong (0 kalimat).")
        for s in res.sentences_b:
            if s.sentence_id in matched_b:
                p = matched_b[s.sentence_id]
                cls = "ft-sent ft-sent--match"
                meta = f"{s.sentence_id}  •  Cocok dengan {p.sentence_a.sentence_id} (selisih {p.hamming_distance} bit)"
            elif s.sentence_id in cand_b:
                cls = "ft-sent ft-sent--cand"
                meta = f"{s.sentence_id}  •  Kandidat tambahan (tidak dihitung ulang)"
            else:
                cls = "ft-sent"
                meta = s.sentence_id
            st.markdown(
                f'<div class="{cls}">'
                f'<div class="ft-sent-meta">{html.escape(meta)}</div>'
                f"<div>{html.escape(s.original_text)}</div>"
                "</div>",
                unsafe_allow_html=True,
            )


def _render_sidebar() -> Tuple[int, str, bool, float, float, ThemePalette]:
    """Merender panel kontrol sidebar yang rapi, mudah dipahami, dan mudah dikustomisasi."""
    if "hamming_k" not in st.session_state:
        st.session_state["hamming_k"] = int(APP_CONFIG["default_threshold"])

    with st.sidebar:
        st.markdown(
            f'<div class="ft-section-title" style="margin-top:0;">'
            f'{svg_icon("sliders", 17)} Pengaturan Analisis</div>',
            unsafe_allow_html=True,
        )

        # Preset cepat untuk pengguna biasa (1 klik langsung ubah slider K).
        st.caption("Pilih tingkat ketelitian cepat:")
        preset_cols = st.columns(3)
        presets = APP_CONFIG["threshold_presets"]
        for col, (label, val, tip) in zip(preset_cols, presets):
            col.button(
                f"{label} ({val})",
                key=f"preset_k_{val}",
                on_click=_set_threshold_preset,
                args=(val,),
                help=tip,
                width="stretch",
            )

        threshold = st.slider(
            "Ambang Jarak Hamming (K)",
            min_value=0,
            max_value=BIT_LENGTH_DEFAULT,
            step=1,
            key="hamming_k",
            help="Jumlah maksimal bit berbeda (dari 64 bit) agar dua kalimat dianggap mirip.",
        )
        st.markdown(
            f'<div class="ft-rule-box">'
            f"<strong>Aturan aktif: Jarak Hamming &lt;= {threshold}</strong><br>"
            f"{html.escape(_describe_k(threshold))}"
            "</div>",
            unsafe_allow_html=True,
        )

        shingle_mode = st.selectbox(
            "Mode Pemecahan Kata (Shingle)",
            options=["unigram", "unigram_bigram"],
            format_func=lambda m: SHINGLE_MODE_LABELS[m],
            key="shingle_mode",
            help="Unigram (1 kata) sesuai langkah wajib. Unigram + Bigram disediakan sesuai catatan panduan.",
        )

        # Kustomisasi tampilan & batas kategori (dilipat agar sidebar tetap tenang).
        with st.expander("Kustomisasi Tampilan & Kategori"):
            theme_name = st.selectbox(
                "Tema Warna",
                options=list(THEME_PRESETS.keys()),
                index=0,
                key="theme_name",
                help="Ubah palet warna seluruh antarmuka secara langsung (token juga bisa diedit di ui_theme.py).",
            )
            theme = THEME_PRESETS[theme_name]
            st.caption(theme.description)

            sort_by_decimal = st.checkbox(
                "Urutkan tabel fingerprint menurut nilai desimal",
                value=False,
                key="sort_by_decimal",
                help="Mengurutkan tampilan tabel fingerprint tanpa mengubah nilai 64-bit aslinya.",
            )

            st.markdown("**Batas Kategori Kemiripan***")
            duplicate_min = st.slider(
                "Minimum Duplikat (%)",
                min_value=50.0,
                max_value=100.0,
                value=DEFAULT_DUPLICATE_MIN_PERCENT,
                step=5.0,
                key="dup_min",
            )
            near_duplicate_min = st.slider(
                "Minimum Hampir Duplikat (%)",
                min_value=5.0,
                max_value=min(95.0, duplicate_min - 5.0),
                value=min(DEFAULT_NEAR_DUPLICATE_MIN_PERCENT, duplicate_min - 5.0),
                step=5.0,
                key="near_dup_min",
            )
            st.caption(
                "*Batas kategori adalah pilihan implementasi yang dapat disesuaikan, bukan ketentuan resmi dosen."
            )

        st.divider()
        st.caption(
            "Catatan Forensik: Hasil menunjukkan kemiripan teks berbasis Simhash 64-bit, "
            "bukan vonis plagiarisme terhadap penerbit."
        )

    return threshold, shingle_mode, sort_by_decimal, duplicate_min, near_duplicate_min, theme


def main() -> None:
    st.set_page_config(
        page_title=str(APP_CONFIG["page_title"]),
        layout="wide",
    )

    # Render sidebar lebih dulu untuk mendapatkan tema & parameter aktif.
    threshold, shingle_mode, sort_by_decimal, duplicate_min, near_duplicate_min, theme = _render_sidebar()

    # Terapkan CSS tema aktif secara global.
    st.markdown(build_theme_css(theme), unsafe_allow_html=True)

    # Header minimalis + panduan singkat yang bisa dibuka bila diperlukan.
    st.markdown(render_brand_header_html(), unsafe_allow_html=True)
    with st.expander("Baru pertama kali membuka? Lihat cara kerja singkat dalam 3 langkah"):
        st.markdown(render_how_it_works_html(), unsafe_allow_html=True)

    corpus_docs = load_clean_corpus()

    # 3 tab utama yang tenang tanpa tab bertumpuk.
    tab_banding, tab_semua, tab_korpus = st.tabs(
        [
            "Bandingkan 2 Dokumen",
            "Semua 10 Pasangan",
            "Korpus & Cara Kerja",
        ]
    )

    # ==================================================================
    # TAB 1: BANDINGKAN 2 DOKUMEN
    # ==================================================================
    with tab_banding:
        with st.container(border=True):
            c_top1, c_top2 = st.columns([3, 2])
            with c_top1:
                st.markdown("**Pilih dua dokumen berita yang ingin dibandingkan**")
            with c_top2:
                include_empty_demo = st.checkbox(
                    "Sertakan Dokumen Uji Kosong (D0)",
                    value=False,
                    key="include_empty_demo",
                    help="Aktifkan untuk menguji bahwa program tetap aman bila menerima dokumen kosong.",
                )

            selectable_docs = list(corpus_docs)
            if include_empty_demo:
                selectable_docs.append(
                    CorpusDocument(
                        doc_id="D0",
                        filename="uji_kosong.txt",
                        sumber="Uji Dokumen Kosong",
                        judul="(Dokumen Kosong)",
                        text="",
                    )
                )
            docs_by_id = {d.doc_id: d for d in selectable_docs}
            doc_ids = list(docs_by_id.keys())

            sel_a, sel_b = st.columns(2)
            with sel_a:
                doc_a_id = st.selectbox(
                    "Dokumen A",
                    options=doc_ids,
                    index=0,
                    format_func=lambda did: docs_by_id[did].display_label if did in docs_by_id else did,
                    key="select_doc_a",
                )
            with sel_b:
                doc_b_id = st.selectbox(
                    "Dokumen B",
                    options=doc_ids,
                    index=2 if len(doc_ids) > 2 else 0,
                    format_func=lambda did: docs_by_id[did].display_label if did in docs_by_id else did,
                    key="select_doc_b",
                )

        res = compare_documents(
            doc_a=docs_by_id[doc_a_id],
            doc_b=docs_by_id[doc_b_id],
            threshold=threshold,
            shingle_mode=shingle_mode,
            bit_length=BIT_LENGTH_DEFAULT,
            duplicate_min_percent=duplicate_min,
            near_duplicate_min_percent=near_duplicate_min,
        )

        if res.notice:
            st.warning(res.notice)

        # Kartu kesimpulan bahasa awam dengan skor besar & bar progres.
        headline = f"{res.doc_a.sumber} ({res.doc_a.doc_id}) dibandingkan dengan {res.doc_b.sumber} ({res.doc_b.doc_id})"
        if res.is_empty_comparison:
            explanation_html = (
                "Salah satu atau kedua dokumen tidak berisi kalimat, sehingga persentase kemiripan "
                "ditetapkan <strong>0.00%</strong>."
            )
        elif res.matched_pair_count > 0:
            explanation_html = (
                f"Dari <strong>{res.total_sentences_a} kalimat</strong> di {html.escape(res.doc_a.sumber)} dan "
                f"<strong>{res.total_sentences_b} kalimat</strong> di {html.escape(res.doc_b.sumber)}, "
                f"ditemukan <strong>{res.matched_pair_count} pasang kalimat cocok satu-ke-satu</strong> "
                f"pada aturan <code>{html.escape(res.threshold_rule)}</code>. "
                f"Cakupan isi: <strong>{res.coverage_a_percent:.1f}%</strong> pada Dokumen A dan "
                f"<strong>{res.coverage_b_percent:.1f}%</strong> pada Dokumen B."
            )
        else:
            closest = _find_closest_pair(res.sentences_a, res.sentences_b)
            closest_html = ""
            if closest is not None:
                closest_html = (
                    f" Pasangan kalimat paling mendekati adalah <code>{html.escape(closest[1])}</code> dan "
                    f"<code>{html.escape(closest[2])}</code> dengan selisih <strong>{closest[0]} dari 64 bit</strong> "
                    f"(pilih preset <strong>Longgar</strong> atau geser ambang K ke <strong>{closest[0]}</strong> di panel kiri untuk melihatnya)."
                )
            explanation_html = (
                f"Pada aturan <code>{html.escape(res.threshold_rule)}</code>, belum ada pasangan kalimat yang "
                f"memenuhi batas kemiripan dari <strong>{res.total_sentences_a}</strong> vs "
                f"<strong>{res.total_sentences_b}</strong> kalimat.{closest_html}"
            )

        st.markdown(
            render_verdict_card_html(
                similarity_percent=res.similarity_percent,
                category=res.category,
                headline=headline,
                explanation_html=explanation_html,
                theme=theme,
                is_empty=res.is_empty_comparison,
            ),
            unsafe_allow_html=True,
        )

        # 4 KPI ringkas & jelas.
        st.markdown(
            render_kpi_strip_html(
                [
                    (
                        "Kalimat (Dok A / Dok B)",
                        f"{res.total_sentences_a} / {res.total_sentences_b}",
                        f"{res.total_pairs_evaluated} kombinasi kalimat diperiksa",
                    ),
                    (
                        "Kandidat / Cocok 1-ke-1",
                        f"{res.candidate_pair_count} / {res.matched_pair_count}",
                        "Cocok 1-ke-1 dipakai untuk persentase",
                    ),
                    (
                        "Cakupan Dokumen A",
                        f"{res.coverage_a_percent:.1f}%",
                        f"{res.matched_pair_count} dari {res.total_sentences_a} kalimat",
                    ),
                    (
                        "Cakupan Dokumen B",
                        f"{res.coverage_b_percent:.1f}%",
                        f"{res.matched_pair_count} dari {res.total_sentences_b} kalimat",
                    ),
                ]
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            f"Kategori memakai batas yang dapat dikustomisasi (Duplikat >= {res.duplicate_min_percent:.0f}%, "
            f"Hampir Duplikat >= {res.near_duplicate_min_percent:.0f}%) — bukan ketentuan resmi dosen dan bukan vonis plagiarisme."
        )

        # Pilihan tampilan kalimat: Tabel Pasangan Mirip / Baca Berdampingan / Fingerprint.
        st.markdown(
            render_section_header_html(
                "compare",
                "Detail Hasil Perbandingan",
                "Pilih tampilan yang paling nyaman: ringkasan pasangan mirip, baca artikel berdampingan, atau tabel sidik jari 64-bit.",
            ),
            unsafe_allow_html=True,
        )
        view_mode = st.radio(
            "Tampilan detail:",
            options=[
                f"Pasangan Kalimat Mirip ({res.candidate_pair_count})",
                "Baca Artikel Berdampingan (Highlight)",
                "Tabel Kalimat & Fingerprint (Biner & Desimal)",
            ],
            horizontal=True,
            label_visibility="collapsed",
            key="detail_view_mode",
        )

        if view_mode.startswith("Pasangan"):
            if res.candidate_pairs:
                only_1_to_1 = st.checkbox(
                    f"Hanya tampilkan pasangan cocok 1-ke-1 ({res.matched_pair_count} pasang)",
                    value=False,
                    key="only_1_to_1",
                )
                shown = res.matched_pairs if only_1_to_1 else res.candidate_pairs
                pair_df = pd.DataFrame(
                    [
                        {
                            "ID A": p.sentence_a.sentence_id,
                            "ID B": p.sentence_b.sentence_id,
                            "Jarak Hamming": p.hamming_distance,
                            "Kemiripan Bit (%)": round(((64 - p.hamming_distance) / 64.0) * 100.0, 1),
                            "Status": "Dipakai (1-ke-1)" if p.is_matched_one_to_one else "Kandidat Tambahan",
                            "Teks Kalimat A": p.sentence_a.original_text,
                            "Teks Kalimat B": p.sentence_b.original_text,
                        }
                        for p in shown
                    ]
                )
                st.dataframe(
                    pair_df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Kemiripan Bit (%)": st.column_config.ProgressColumn(
                            "Kemiripan Bit",
                            format="%.1f%%",
                            min_value=0,
                            max_value=100,
                        )
                    },
                )
            else:
                st.info(
                    f"Belum ada pasangan kalimat dengan `{res.threshold_rule}`. "
                    "Gunakan preset di sidebar atau naikkan slider K untuk mengeksplorasi kemiripan sebagian."
                )

        elif view_mode.startswith("Baca"):
            st.caption("Warna hijau = kalimat cocok 1-ke-1 • Warna kuning = kandidat tambahan • Polos = belum cocok pada ambang saat ini.")
            _render_side_by_side_sentences(res)

        else:
            fp_choice = st.radio(
                "Pilih dokumen:",
                options=["Dokumen A", "Dokumen B"],
                horizontal=True,
                key="radio_fp_doc",
            )
            target_sentences = res.sentences_a if fp_choice == "Dokumen A" else res.sentences_b
            if target_sentences:
                if sort_by_decimal:
                    st.caption("Diurutkan berdasarkan nilai desimal fingerprint menaik (nilai 64-bit asli tetap utuh).")
                st.dataframe(
                    _build_fingerprint_df(target_sentences, sort_by_decimal=sort_by_decimal),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Dokumen yang dipilih kosong (0 kalimat).")

        # Penjelasan rumus tersimpan rapi agar layar tetap lega.
        with st.expander("Lihat rumus persentase kemiripan dan pencocokan satu-ke-satu"):
            st.latex(r"\text{Persentase Kemiripan} = \frac{2 \times M}{N_A + N_B} \times 100\%")
            st.markdown(
                f"""
                - **Pasangan Kandidat (`{res.candidate_pair_count}`)**: semua pasangan kalimat dengan `{res.threshold_rule}`.
                - **Pasangan Cocok Satu-ke-Satu (`M = {res.matched_pair_count}`)**: dipilih dari jarak Hamming terkecil terlebih dahulu agar setiap kalimat hanya dihitung **maksimal 1 kali** (`M <= min(N_A, N_B)`).
                - **Perhitungan saat ini:** `(2 × {res.matched_pair_count}) / ({res.total_sentences_a} + {res.total_sentences_b}) × 100%` = **`{res.similarity_percent:.2f}%`**.
                """
            )

    # ==================================================================
    # TAB 2: SEMUA 10 PASANGAN UNIK
    # ==================================================================
    with tab_semua:
        all_results = compare_all_document_pairs(
            documents=corpus_docs,
            threshold=threshold,
            shingle_mode=shingle_mode,
            bit_length=BIT_LENGTH_DEFAULT,
            duplicate_min_percent=duplicate_min,
            near_duplicate_min_percent=near_duplicate_min,
        )
        n_dup = sum(1 for r in all_results if r.category == "Duplikat")
        n_near = sum(1 for r in all_results if r.category == "Hampir Duplikat")
        n_low = sum(1 for r in all_results if r.category == "Kemiripan Rendah")

        st.markdown(
            render_kpi_strip_html(
                [
                    ("Total Pasangan Unik", f"{len(all_results)} pasangan", "Dari 5 dokumen korpus: C(5, 2)"),
                    ("Duplikat*", f"{n_dup} pasangan", f"Persentase >= {duplicate_min:.0f}%"),
                    ("Hampir Duplikat*", f"{n_near} pasangan", f"{near_duplicate_min:.0f}% – < {duplicate_min:.0f}%"),
                    ("Kemiripan Rendah*", f"{n_low} pasangan", f"Persentase < {near_duplicate_min:.0f}%"),
                ]
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            render_section_header_html(
                "compare",
                "Ringkasan 10 Pasangan Dokumen",
                f"Diurutkan dari kemiripan tertinggi • Aturan: {all_results[0].threshold_rule} • Mode: {SHINGLE_MODE_LABELS[shingle_mode]}",
            ),
            unsafe_allow_html=True,
        )
        sorted_all = sorted(
            all_results,
            key=lambda r: (-r.similarity_percent, r.doc_a.doc_id, r.doc_b.doc_id),
        )
        all_df = pd.DataFrame(
            [
                {
                    "Pasangan": f"{r.doc_a.doc_id} vs {r.doc_b.doc_id}",
                    "Dokumen A": r.doc_a.sumber,
                    "Dokumen B": r.doc_b.sumber,
                    "Kalimat (A/B)": f"{r.total_sentences_a} / {r.total_sentences_b}",
                    "Kandidat": r.candidate_pair_count,
                    "Cocok 1-ke-1": r.matched_pair_count,
                    "Kemiripan (%)": round(r.similarity_percent, 2),
                    "Kategori*": r.category,
                }
                for r in sorted_all
            ]
        )
        st.dataframe(
            all_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Kemiripan (%)": st.column_config.ProgressColumn(
                    "Kemiripan (%)",
                    format="%.2f%%",
                    min_value=0,
                    max_value=100,
                )
            },
        )

        st.markdown(
            render_section_header_html(
                "file",
                "Matriks Kemiripan (5 × 5)",
                "Pertemukan baris dan kolom dua dokumen untuk melihat persentase kemiripannya secara cepat.",
            ),
            unsafe_allow_html=True,
        )
        doc_labels = {d.doc_id: f"{d.doc_id} ({d.sumber})" for d in corpus_docs}
        matrix_num: Dict[str, Dict[str, float]] = {
            doc_labels[rd.doc_id]: {
                doc_labels[cd.doc_id]: (100.0 if rd.doc_id == cd.doc_id else 0.0)
                for cd in corpus_docs
            }
            for rd in corpus_docs
        }
        for r in all_results:
            la, lb = doc_labels[r.doc_a.doc_id], doc_labels[r.doc_b.doc_id]
            matrix_num[la][lb] = round(r.similarity_percent, 2)
            matrix_num[lb][la] = round(r.similarity_percent, 2)

        def _style_cell(val: float) -> str:
            if val >= duplicate_min:
                return f"background-color: {theme.success_soft}; color: {theme.success}; font-weight: 700;"
            if val >= near_duplicate_min:
                return f"background-color: {theme.warning_soft}; color: {theme.warning}; font-weight: 600;"
            if val > 0:
                return f"background-color: {theme.info_soft}; color: {theme.info};"
            return ""

        st.dataframe(
            pd.DataFrame(matrix_num).style.format("{:.2f}%").map(_style_cell),
            width="stretch",
        )
        st.caption(
            "*Batas kategori dapat disesuaikan di sidebar (bukan ketentuan resmi dosen) dan hasil ini bukan vonis plagiarisme."
        )

    # ==================================================================
    # TAB 3: DAFTAR KORPUS, INSPEKSI SIMHASH & CATATAN DOSEN
    # ==================================================================
    with tab_korpus:
        fp_cache: Dict[str, List[SentenceFingerprint]] = {
            d.doc_id: build_document_fingerprints(d.doc_id, d.text, shingle_mode=shingle_mode)
            for d in corpus_docs
        }

        st.markdown(
            render_section_header_html(
                "file",
                "Daftar 5 Dokumen Korpus",
                "File asli (dokumen1.txt–dokumen5.txt) tetap utuh. Hasil pemisahan metadata disimpan terpisah di folder korpus_bersih/.",
            ),
            unsafe_allow_html=True,
        )
        corpus_df = pd.DataFrame(
            [
                {
                    "ID": d.doc_id,
                    "Sumber": d.sumber,
                    "File Asli": d.filename,
                    "Judul Artikel": d.judul,
                    "Penulis": d.metadata.get("penulis") or "-",
                    "Tanggal": d.metadata.get("tanggal") or "-",
                    "Kalimat Isi": len(fp_cache[d.doc_id]),
                }
                for d in corpus_docs
            ]
        )
        st.dataframe(corpus_df, width="stretch", hide_index=True)

        with st.expander("Periksa Metadata & Bandingkan Teks Asli vs Teks Bersih"):
            view_doc_id = st.selectbox(
                "Pilih dokumen:",
                options=[d.doc_id for d in corpus_docs],
                format_func=lambda did: next(d.display_label for d in corpus_docs if d.doc_id == did),
                key="view_clean_doc",
            )
            chosen_doc = next(d for d in corpus_docs if d.doc_id == view_doc_id)
            meta = chosen_doc.metadata
            st.markdown(
                f"**Judul:** {meta.get('judul') or '-'}  \n"
                f"**Penulis:** {meta.get('penulis') or 'Tidak tercantum'}  •  "
                f"**Tanggal:** {meta.get('tanggal') or '-'}  •  "
                f"**URL:** {meta.get('url') or 'Tidak tercantum'}  \n"
                f"**Elemen non-isi yang dipisahkan:** "
                f"{', '.join(meta.get('elemen_non_isi_dipisahkan', [])) or 'Tidak ada'}"
            )
            col_raw, col_clean = st.columns(2)
            with col_raw:
                st.markdown("**Teks Asli (Tidak Diubah)**")
                st.text_area(
                    "Teks Asli",
                    value=str(meta.get("teks_asli", "")),
                    height=220,
                    disabled=True,
                    label_visibility="collapsed",
                )
            with col_clean:
                st.markdown("**Teks Bersih (`korpus_bersih/`)**")
                st.text_area(
                    "Teks Bersih",
                    value=chosen_doc.text,
                    height=220,
                    disabled=True,
                    label_visibility="collapsed",
                )

        with st.expander("Inspeksi Langkah Simhash pada 1 Kalimat (Untuk Belajar)"):
            ic1, ic2 = st.columns(2)
            with ic1:
                insp_doc_id = st.selectbox(
                    "Dokumen:",
                    options=[d.doc_id for d in corpus_docs],
                    format_func=lambda did: next(d.display_label for d in corpus_docs if d.doc_id == did),
                    key="insp_doc",
                )
            insp_fps = fp_cache[insp_doc_id]
            fps_by_id = {fp.sentence_id: fp for fp in insp_fps}
            with ic2:
                insp_sent_id = st.selectbox(
                    "Kalimat:",
                    options=list(fps_by_id.keys()),
                    format_func=lambda sid: (
                        f"{sid}: {fps_by_id[sid].original_text[:65]}..."
                        if sid in fps_by_id
                        else sid
                    ),
                    key="insp_sent",
                )
            sf = fps_by_id[insp_sent_id]
            st.markdown(f"**Normalisasi huruf kecil:** `{sf.normalized_text}`")
            token_df = pd.DataFrame(
                [
                    {
                        "Shingle / Token": td.token,
                        "Bobot TF": td.tf,
                        "Hash SHA-256 64-bit (Biner)": td.hash_bin,
                    }
                    for td in sf.token_details
                ]
            )
            st.dataframe(token_df, width="stretch", hide_index=True, height=220)
            st.success(
                f"**Fingerprint Biner (64-bit):** `{sf.fingerprint_bin}`  \n"
                f"**Fingerprint Desimal:** `{sf.fingerprint_dec}`"
            )

        st.warning(
            "**Bagian Panduan yang Masih Perlu Dikonfirmasi kepada Dosen:** "
            "File PDF panduan tugas maupun materi kuliah tidak ditemukan di folder proyek. "
            "Harap konfirmasikan: (1) kewajiban **Unigram** vs **Unigram + Bigram** (keduanya tersedia di sidebar), "
            "dan (2) maksud pasti notasi shift kanan **`2 >> B`** beserta pengurutan nilai desimal "
            "(program tidak menebak bahwa artinya `fingerprint >> 2`; fingerprint 64-bit asli dan jarak Hamming dasar dipertahankan utuh)."
        )


if __name__ == "__main__":
    if get_script_run_ctx(suppress_warning=True) is None:
        print("\n" + "=" * 68)
        print("INFO: Aplikasi ini memakai antarmuka web Streamlit.")
        print("Jalankan perintah berikut di terminal / PowerShell:")
        print("\n    python -m streamlit run app.py\n")
        print("=" * 68 + "\n")
        sys.exit(0)
    main()
