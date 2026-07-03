#!/usr/bin/env python3
"""Cập nhật trạng thái văn bản bị sửa đổi/thay thế bởi lô văn bản mới.

Cách dùng:
    python3 scripts/update_status.py /tmp/moi.json

Với mỗi văn bản mới có sua_doi_thay_the: tìm văn bản cũ qua index →
- trich_yeu văn bản mới chứa "thay thế"/"bãi bỏ" số hiệu đó → het_hieu_luc
- ngược lại (chỉ sửa đổi, bổ sung)                         → het_hieu_luc_mot_phan
Đồng thời thêm bi_sua_doi_boi (số hiệu văn bản mới) vào văn bản cũ, cập nhật cả index.
Văn bản đã het_hieu_luc thì giữ nguyên.
"""
import argparse

from common import DATA_DIR, INDEX_PATH, load_json, save_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("new_docs_file")
    args = parser.parse_args()

    payload = load_json(args.new_docs_file)
    new_docs = payload.get("documents", []) if isinstance(payload, dict) else payload
    index = load_json(INDEX_PATH, default={})
    touched_weeks = {}  # week_key → payload đã load
    n_updates = 0

    for new_doc in new_docs:
        for old_id in new_doc.get("sua_doi_thay_the", []):
            entry = index.get(old_id)
            if entry is None:
                print(f"  bỏ qua: {old_id} chưa có trong index (văn bản trước thời điểm theo dõi)")
                continue
            week_key = entry["tuan"]
            if week_key not in touched_weeks:
                touched_weeks[week_key] = load_json(DATA_DIR / f"{week_key}.json")
            week_payload = touched_weeks[week_key]
            for old_doc in week_payload.get("documents", []):
                if old_doc["so_hieu"] != old_id:
                    continue
                if new_doc["so_hieu"] not in old_doc.setdefault("bi_sua_doi_boi", []):
                    old_doc["bi_sua_doi_boi"].append(new_doc["so_hieu"])
                if old_doc["trang_thai"] != "het_hieu_luc":
                    text = (new_doc.get("trich_yeu") or "").lower()
                    replaced = "thay thế" in text or "bãi bỏ" in text
                    old_doc["trang_thai"] = "het_hieu_luc" if replaced else "het_hieu_luc_mot_phan"
                    entry["trang_thai"] = old_doc["trang_thai"]
                n_updates += 1

    for week_key, week_payload in touched_weeks.items():
        save_json(DATA_DIR / f"{week_key}.json", week_payload)
    save_json(INDEX_PATH, index)
    print(f"OK: cập nhật {n_updates} văn bản cũ trong {len(touched_weeks)} file tuần")


if __name__ == "__main__":
    main()
