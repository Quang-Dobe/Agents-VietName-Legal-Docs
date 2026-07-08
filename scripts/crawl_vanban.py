#!/usr/bin/env python3
"""Crawl vanban.chinhphu.vn — nguồn chính.

Cách dùng:
    python3 scripts/crawl_vanban.py --from 2026-06-23 --to 2026-06-30 --out /tmp/vanban.json

Output: JSON {"source": ..., "fetched_at": ..., "documents": [...]}
(mỗi document theo schema CLAUDE.md, CHƯA có tom_tat_ai / linh_vuc / trang_thai).

Cấu trúc trang (chốt tại Run 0 recon — xem "Ghi chú cấu trúc trang" trong CLAUDE.md):
- Trang danh sách mặc định (`{LIST_URL}?classid=1&mode=1`, GET) trả về 50 văn bản MỚI
  NHẤT toàn hệ thống, sort ngay_ban_hanh giảm dần — KHÔNG có param GET lọc khoảng ngày
  (form nâng cao dùng ASP.NET postback/__VIEWSTATE, không thay bằng query string được).
  Do đó script lấy 50 dòng mặc định rồi lọc theo [--from, --to] phía client; nếu văn bản
  cũ nhất trong 50 dòng vẫn >= --from thì có khả năng còn sót (possibly_truncated=true
  trong output) — cần agent tự fetch/xử lý thêm (xem self-healing trong CLAUDE.md).
- Mỗi dòng: `table.search-result tr` > `span.code` (so_hieu) + thẻ `a` cha (link_goc,
  dạng `/?pageid=...&docid=...&classid=1`) + `span.issued-date` (ngày ban hành, DD/MM/YYYY)
  + `span.substract` (trích yếu rút gọn).
- Trang chi tiết: bảng `td.col1` (nhãn) + `td` kế tiếp (giá trị) — các nhãn dùng:
  "Số ký hiệu", "Ngày ban hành" (DD-MM-YYYY), "Ngày có hiệu lực" (DD-MM-YYYY, có thể vắng),
  "Loại văn bản", "Cơ quan ban hành", "Trích yếu".
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

BASE = "https://vanban.chinhphu.vn"
LIST_URL = f"{BASE}/he-thong-van-ban"

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


def vn_date_slash_to_iso(text):
    """'04/07/2026' → '2026-07-04'."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text or "")
    if not m:
        return None
    d, mth, y = m.groups()
    return f"{y}-{int(mth):02d}-{int(d):02d}"


def vn_date_dash_to_iso(text):
    """'04-07-2026' → '2026-07-04'."""
    m = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", text or "")
    if not m:
        return None
    d, mth, y = m.groups()
    return f"{y}-{int(mth):02d}-{int(d):02d}"


def parse_list_page(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.search-result")
    docs = []
    if not table:
        return docs
    for tr in table.select("tr"):
        code_span = tr.select_one("span.code")
        if not code_span:
            continue
        link = code_span.find_parent("a")
        href = link["href"] if link and link.get("href") else None
        if href and href.startswith("/"):
            href = BASE + href
        date_span = tr.select_one("span.issued-date")
        substract = tr.select_one("span.substract")
        docs.append({
            "so_hieu": code_span.get_text(strip=True),
            "ngay_ban_hanh": vn_date_slash_to_iso(date_span.get_text(strip=True) if date_span else ""),
            "trich_yeu": substract.get_text(strip=True) if substract else None,
            "link_goc": href,
        })
    return docs


def parse_detail_page(html):
    soup = BeautifulSoup(html, "html.parser")
    info = {}
    for tr in soup.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2 and "col1" in (tds[0].get("class") or []):
            info[tds[0].get_text(strip=True)] = tds[1].get_text(" ", strip=True)
    return info


def enrich_with_detail(doc):
    html = fetch(doc["link_goc"])
    info = parse_detail_page(html)
    if info.get("Số ký hiệu"):
        doc["so_hieu"] = info["Số ký hiệu"]
    doc["ngay_ban_hanh"] = vn_date_dash_to_iso(info.get("Ngày ban hành")) or doc.get("ngay_ban_hanh")
    doc["ngay_hieu_luc"] = vn_date_dash_to_iso(info.get("Ngày có hiệu lực"))
    doc["loai"] = info.get("Loại văn bản")
    doc["co_quan"] = info.get("Cơ quan ban hành")
    if info.get("Trích yếu"):
        doc["trich_yeu"] = info["Trích yếu"]
    doc["nguon"] = "vanban.chinhphu.vn"
    return doc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    html = fetch(LIST_URL, classid=1, mode=1)
    rows = parse_list_page(html)

    if not rows:
        print(
            "KHÔNG PARSE ĐƯỢC VĂN BẢN NÀO.\n"
            "Nguyên nhân khả dĩ: (1) trang đổi cấu trúc so với ghi chú trong CLAUDE.md;\n"
            "(2) lỗi mạng/allowlist. Agent: fetch trực tiếp trang danh sách, đối chiếu HTML,\n"
            "parse tay, rồi sửa SELECTORS trong script này và cập nhật CLAUDE.md.",
            file=sys.stderr,
        )
        sys.exit(2)

    dated_rows = [d for d in rows if d.get("ngay_ban_hanh")]
    oldest = min((d["ngay_ban_hanh"] for d in dated_rows), default=None)
    possibly_truncated = bool(oldest) and oldest >= args.from_date and len(rows) >= 50

    in_range = [d for d in dated_rows if args.from_date <= d["ngay_ban_hanh"] <= args.to_date]
    docs = [enrich_with_detail(d) for d in in_range]

    out = {
        "source": "vanban.chinhphu.vn",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "from": args.from_date,
        "to": args.to_date,
        "request_count": request_count,
        "possibly_truncated": possibly_truncated,
        "documents": docs,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    note = " (CÓ THỂ SÓT — 50 dòng mặc định chưa phủ hết khoảng ngày, cần fetch thêm tay)" if possibly_truncated else ""
    print(f"OK: {len(docs)} văn bản → {args.out} ({request_count} request){note}")


if __name__ == "__main__":
    main()
