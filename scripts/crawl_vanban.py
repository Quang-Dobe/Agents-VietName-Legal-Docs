#!/usr/bin/env python3
"""Crawl vanban.chinhphu.vn — nguồn chính.

Cách dùng:
    python3 scripts/crawl_vanban.py --from 2026-06-23 --to 2026-06-30 --out /tmp/vanban.json

Output: JSON {"source": ..., "fetched_at": ..., "documents": [...]}
(mỗi document theo schema CLAUDE.md, CHƯA có tom_tat_ai / linh_vuc / trang_thai).

!!! RUN 0 RECON CHƯA CHẠY: SELECTORS và DATE_PARAMS bên dưới là phỏng đoán.
Run 0 phải chốt giá trị thật từ HTML thực tế rồi cập nhật file này + CLAUDE.md.
Trước đó script sẽ exit(2) nếu không parse được gì, kèm hướng dẫn.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from common import MAX_REQUESTS, RATE_LIMIT_S, USER_AGENT

BASE = "https://vanban.chinhphu.vn"
LIST_URL = f"{BASE}/he-thong-van-ban"

# --- CẦN CHỐT SAU RUN 0 RECON ---------------------------------------------
# Param lọc theo khoảng ngày ban hành của form tìm kiếm nâng cao (chưa xác nhận).
DATE_PARAMS = {"from": "fromdate", "to": "todate"}  # TODO(recon): tên param thật
PAGE_PARAM = "page"                                  # TODO(recon): tên param phân trang thật
SELECTORS = {                                        # TODO(recon): selectors thật
    "row": ".box-list-vanban li, table.list-vanban tr, .item-vanban",
    "title": "a",
    "detail_meta_label": ".vb-info td:first-child, .thuoc-tinh dt",
}
# ---------------------------------------------------------------------------

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
request_count = 0


def fetch(url, **params):
    global request_count
    if request_count >= MAX_REQUESTS:
        raise RuntimeError(f"Chạm giới hạn {MAX_REQUESTS} request/run")
    if request_count:
        time.sleep(RATE_LIMIT_S)
    request_count += 1
    resp = session.get(url, params=params or None, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_list_page(html):
    """Parse 1 trang danh sách → list dict thô (chưa đủ trường)."""
    soup = BeautifulSoup(html, "html.parser")
    docs = []
    for row in soup.select(SELECTORS["row"]):
        link = row.select_one(SELECTORS["title"])
        if not link or not link.get("href"):
            continue
        href = link["href"]
        if href.startswith("/"):
            href = BASE + href
        docs.append({"trich_yeu": link.get_text(strip=True), "link_goc": href, "_row_text": row.get_text(" ", strip=True)})
    return docs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    params = {
        "classid": 1,
        "mode": 1,
        DATE_PARAMS["from"]: args.from_date,
        DATE_PARAMS["to"]: args.to_date,
    }
    html = fetch(LIST_URL, **params)
    docs = parse_list_page(html)

    if not docs:
        print(
            "KHÔNG PARSE ĐƯỢC VĂN BẢN NÀO.\n"
            "Nguyên nhân khả dĩ: (1) selectors/params trong script chưa đúng vì Run 0 recon\n"
            "chưa chạy — xem 'Ghi chú cấu trúc trang' trong CLAUDE.md; (2) trang đổi cấu trúc.\n"
            "Hướng xử lý cho agent: fetch trực tiếp trang danh sách, đối chiếu HTML, parse tay,\n"
            "rồi sửa DATE_PARAMS / PAGE_PARAM / SELECTORS trong script này và cập nhật CLAUDE.md.",
            file=sys.stderr,
        )
        sys.exit(2)

    # TODO(recon): phân trang (lặp PAGE_PARAM đến hết) + fetch trang chi tiết để lấy đủ
    # so_hieu / loai / co_quan / ngay_ban_hanh / ngay_hieu_luc.
    out = {
        "source": "vanban.chinhphu.vn",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "from": args.from_date,
        "to": args.to_date,
        "request_count": request_count,
        "documents": docs,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(docs)} văn bản → {args.out} ({request_count} request)")


if __name__ == "__main__":
    main()
