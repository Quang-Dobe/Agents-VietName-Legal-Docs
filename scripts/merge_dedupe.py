#!/usr/bin/env python3
"""Gộp output các crawler, loại văn bản đã có trong data/index.json.

Cách dùng:
    python3 scripts/merge_dedupe.py /tmp/vanban.json /tmp/congbao.json --out /tmp/moi.json

Ưu tiên khi trùng số hiệu giữa các nguồn: vanban.chinhphu.vn > congbao.chinhphu.vn > vbpl.vn.
Văn bản chưa có so_hieu (crawler chỉ lấy được từ trang danh sách) vẫn được giữ và
đánh dấu "_can_fetch_detail": true để summarizer/orchestrator xử lý tiếp.
"""
import argparse
import json

from common import INDEX_PATH, load_json

SOURCE_PRIORITY = {"vanban.chinhphu.vn": 0, "congbao.chinhphu.vn": 1, "vbpl.vn": 2}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="các file output crawler")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    index = load_json(INDEX_PATH, default={})
    best = {}      # so_hieu → doc
    no_id = []     # chưa parse được so_hieu

    for path in args.inputs:
        payload = load_json(path)
        if not payload:
            continue
        source = payload.get("source", "")
        for doc in payload.get("documents", []):
            doc.setdefault("nguon", source)
            so_hieu = doc.get("so_hieu")
            if not so_hieu:
                doc["_can_fetch_detail"] = True
                no_id.append(doc)
                continue
            if so_hieu in index:
                continue  # đã có từ tuần trước
            prio = SOURCE_PRIORITY.get(doc["nguon"], 9)
            if so_hieu not in best or prio < SOURCE_PRIORITY.get(best[so_hieu]["nguon"], 9):
                best[so_hieu] = doc

    documents = list(best.values()) + no_id
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"documents": documents}, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(best)} văn bản mới có số hiệu, {len(no_id)} cần fetch chi tiết → {args.out}")


if __name__ == "__main__":
    main()
