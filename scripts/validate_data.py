#!/usr/bin/env python3
"""Validate toàn bộ data/ theo schema trong CLAUDE.md. Exit 1 nếu có lỗi.

Cách dùng:
    python3 scripts/validate_data.py             # validate đầy đủ
    python3 scripts/validate_data.py --partial   # bỏ qua tom_tat_ai/linh_vuc (dùng khi recon)
    python3 scripts/validate_data.py --file X    # validate 1 file output crawler (list văn bản thô)
"""
import argparse
import re
import sys
from datetime import date

from common import (
    ALLOWED_LINK_DOMAINS, INDEX_PATH, LOAI_HOP_LE, NGAY_RE, NGUON_HOP_LE,
    REQUIRED_FIELDS, SO_HIEU_RE, TAXONOMY, TRANG_THAI_HOP_LE,
    iter_week_files, load_json, week_key_from_path,
)

errors = []


def err(so_hieu, msg):
    errors.append(f"  [{so_hieu}] {msg}")


def check_date(so_hieu, field, value, allow_null=False):
    if value is None:
        if not allow_null:
            err(so_hieu, f"{field} không được null")
        return None
    if not isinstance(value, str) or not NGAY_RE.match(value):
        err(so_hieu, f"{field} phải dạng YYYY-MM-DD, gặp: {value!r}")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        err(so_hieu, f"{field} không phải ngày hợp lệ: {value!r}")
        return None


def count_sentences(text):
    return len([s for s in re.split(r"[.!?…]+\s*", text.strip()) if s])


def check_doc(doc, partial=False):
    so_hieu = doc.get("so_hieu", "<thiếu số hiệu>")
    for field in REQUIRED_FIELDS:
        if field not in doc:
            err(so_hieu, f"thiếu trường {field}")
    if "so_hieu" in doc and not SO_HIEU_RE.match(doc["so_hieu"]):
        err(so_hieu, "so_hieu không khớp định dạng")
    if doc.get("loai") and doc["loai"] not in LOAI_HOP_LE:
        err(so_hieu, f"loai không hợp lệ: {doc['loai']!r}")
    if doc.get("nguon") and doc["nguon"] not in NGUON_HOP_LE:
        err(so_hieu, f"nguon không hợp lệ: {doc['nguon']!r}")

    d_bh = check_date(so_hieu, "ngay_ban_hanh", doc.get("ngay_ban_hanh"))
    d_hl = check_date(so_hieu, "ngay_hieu_luc", doc.get("ngay_hieu_luc"), allow_null=True)
    if d_bh and d_hl and d_hl < d_bh:
        err(so_hieu, f"ngay_hieu_luc ({d_hl}) trước ngay_ban_hanh ({d_bh})")

    link = doc.get("link_goc") or ""
    if not any(f".{dom}/" in link + "/" or f"//{dom}" in link for dom in ALLOWED_LINK_DOMAINS):
        err(so_hieu, f"link_goc không thuộc domain chính thống: {link!r}")

    if doc.get("trang_thai") and doc["trang_thai"] not in TRANG_THAI_HOP_LE:
        err(so_hieu, f"trang_thai không hợp lệ: {doc['trang_thai']!r}")

    if not partial:
        if doc.get("linh_vuc") not in TAXONOMY:
            err(so_hieu, f"linh_vuc ngoài taxonomy: {doc.get('linh_vuc')!r}")
        tom_tat = doc.get("tom_tat_ai") or ""
        n_sent = count_sentences(tom_tat)
        n_words = len(tom_tat.split())
        if not 3 <= n_sent <= 5:
            err(so_hieu, f"tom_tat_ai phải 3-5 câu, đang {n_sent} câu")
        if n_words > 120:
            err(so_hieu, f"tom_tat_ai quá dài ({n_words} từ, tối đa 120)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", action="store_true",
                        help="bỏ qua kiểm tra tom_tat_ai / linh_vuc (dùng khi recon)")
    parser.add_argument("--file", help="chỉ validate 1 file crawler output (JSON có key documents)")
    args = parser.parse_args()

    if args.file:
        payload = load_json(args.file)
        docs = payload.get("documents", payload) if isinstance(payload, dict) else payload
        for doc in docs:
            check_doc(doc, partial=True)
    else:
        index = load_json(INDEX_PATH, default={})
        seen = {}
        for path, payload in iter_week_files():
            week_key = week_key_from_path(path)
            for doc in payload.get("documents", []):
                check_doc(doc, partial=args.partial)
                so_hieu = doc.get("so_hieu")
                if so_hieu in seen:
                    err(so_hieu, f"trùng số hiệu giữa {seen[so_hieu]} và {week_key}")
                seen[so_hieu] = week_key
                entry = index.get(so_hieu)
                if entry is None:
                    err(so_hieu, "không có trong data/index.json")
                elif entry.get("tuan") != week_key:
                    err(so_hieu, f"index ghi tuần {entry.get('tuan')!r}, thực tế ở {week_key!r}")
            # file tuần phải sort theo ngày ban hành giảm dần
            days = [d.get("ngay_ban_hanh") or "" for d in payload.get("documents", [])]
            if days != sorted(days, reverse=True):
                errors.append(f"  [{week_key}] documents chưa sort theo ngay_ban_hanh giảm dần")
        for so_hieu in index:
            if so_hieu not in seen:
                err(so_hieu, "có trong index nhưng không thấy trong file tuần nào")

    if errors:
        print(f"VALIDATE FAIL — {len(errors)} lỗi:")
        print("\n".join(errors))
        sys.exit(1)
    print("VALIDATE OK")


if __name__ == "__main__":
    main()
