#!/usr/bin/env python3
"""Crawl congbao.chinhphu.vn — nguồn đối chiếu.

Cách dùng:
    python3 scripts/crawl_congbao.py --from 2026-06-23 --to 2026-06-30 --out /tmp/congbao.json

Danh sách "Văn bản mới nhất" sort mới → cũ, phân trang:
    /van-ban-dang-cong-bao.htm , /van-ban-dang-cong-bao/trang-{N}.htm
→ duyệt từ trang 1, DỪNG khi gặp văn bản có ngày cũ hơn --from.

!!! RUN 0 RECON CHƯA CHẠY: SELECTORS bên dưới là phỏng đoán — xem CLAUDE.md.
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from common import MAX_REQUESTS, RATE_LIMIT_S, USER_AGENT

BASE = "https://congbao.chinhphu.vn"
FIRST_PAGE = f"{BASE}/van-ban-dang-cong-bao.htm"
PAGE_URL = BASE + "/van-ban-dang-cong-bao/trang-{n}.htm"
MAX_PAGES = 40

SELECTORS = {  # TODO(recon): selectors thật
    "row": ".list-vanban li, .doc-item, table tr",
    "title": "a",
}
VN_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
request_count = 0


def fetch(url):
    global request_count
    if request_count >= MAX_REQUESTS:
        raise RuntimeError(f"Chạm giới hạn {MAX_REQUESTS} request/run")
    if request_count:
        time.sleep(RATE_LIMIT_S)
    request_count += 1
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_vn_date(text):
    """'25/06/2026' → '2026-06-25' (lấy ngày đầu tiên xuất hiện trong text)."""
    m = VN_DATE_RE.search(text or "")
    if not m:
        return None
    d, mth, y = m.groups()
    return f"{y}-{int(mth):02d}-{int(d):02d}"


def parse_list_page(html):
    soup = BeautifulSoup(html, "html.parser")
    docs = []
    for row in soup.select(SELECTORS["row"]):
        link = row.select_one(SELECTORS["title"])
        if not link or not link.get("href"):
            continue
        href = link["href"]
        if href.startswith("/"):
            href = BASE + href
        row_text = row.get_text(" ", strip=True)
        docs.append({
            "trich_yeu": link.get_text(strip=True),
            "link_goc": href,
            "ngay_ban_hanh": parse_vn_date(row_text),
            "_row_text": row_text,
        })
    return docs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    collected = []
    for n in range(1, MAX_PAGES + 1):
        url = FIRST_PAGE if n == 1 else PAGE_URL.format(n=n)
        page_docs = parse_list_page(fetch(url))
        if not page_docs:
            if n == 1:
                print(
                    "KHÔNG PARSE ĐƯỢC VĂN BẢN NÀO Ở TRANG 1.\n"
                    "Selectors trong script chưa đúng (Run 0 recon chưa chạy) hoặc trang đổi\n"
                    "cấu trúc. Agent: fetch trang, parse tay, sửa SELECTORS + cập nhật CLAUDE.md.",
                    file=sys.stderr,
                )
                sys.exit(2)
            break
        stop = False
        for doc in page_docs:
            day = doc.get("ngay_ban_hanh")
            if day and day < args.from_date:
                stop = True
                break
            if day is None or day <= args.to_date:
                collected.append(doc)
        if stop:
            break

    out = {
        "source": "congbao.chinhphu.vn",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "from": args.from_date,
        "to": args.to_date,
        "request_count": request_count,
        "documents": collected,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(collected)} văn bản → {args.out} ({request_count} request)")


if __name__ == "__main__":
    main()
