#!/usr/bin/env python3
"""Crawl congbao.chinhphu.vn — nguồn đối chiếu.

Cách dùng:
    python3 scripts/crawl_congbao.py --from 2026-06-23 --to 2026-06-30 --out /tmp/congbao.json

Danh sách "Văn bản mới nhất" sort mới → cũ, phân trang:
    /van-ban-dang-cong-bao.htm , /van-ban-dang-cong-bao/trang-{N}.htm
→ duyệt từ trang 1, DỪNG khi gặp văn bản có ngày cũ hơn --from.

Cấu trúc trang (chốt tại Run 0 recon — xem "Ghi chú cấu trúc trang" trong CLAUDE.md):
- Mỗi văn bản: `div.box--list div.item--vb` > `span.kh` chứa text "Ký hiệu: {so_hieu}";
  `div.middle a.sapo` (title = trích yếu, href = link chi tiết dạng `/van-ban/...htm`);
  `div.bot span.days` chứa text "[Ban hành: DD/MM/YYYY]".
- Trang chi tiết: `div.document--focus div.row` > `span.name` (nhãn) + `div.value
  span.child-value` (giá trị) — nhãn dùng: "Số, ký hiệu", "Loại văn bản", "Cơ quan ban hành"
  (thường IN HOA, cần title-case lại), "Ngày ban hành" (DD/MM/YYYY), "Ngày hiệu lực"
  (DD/MM/YYYY, có thể rỗng), "Trích yếu".
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


def normalize_co_quan(text):
    if text and text.isupper():
        return text.title()
    return text


def parse_list_page(html):
    soup = BeautifulSoup(html, "html.parser")
    docs = []
    for item in soup.select("div.box--list div.item--vb"):
        kh = item.select_one("span.kh")
        so_hieu = None
        if kh:
            m = re.search(r"Ký hiệu:\s*(.+)", kh.get_text(" ", strip=True))
            so_hieu = m.group(1).strip() if m else None
        link = item.select_one("div.middle a.sapo")
        href = link.get("href") if link else None
        if href and href.startswith("/"):
            href = BASE + href
        trich_yeu = (link.get("title") or "").strip() if link else None
        days = item.select_one("div.bot span.days")
        ngay_ban_hanh = None
        if days:
            m = re.search(r"Ban hành:\s*(\d{1,2}/\d{1,2}/\d{4})", days.get_text(" ", strip=True))
            if m:
                ngay_ban_hanh = parse_vn_date(m.group(1))
        if not (so_hieu and href):
            continue
        docs.append({
            "so_hieu": so_hieu,
            "trich_yeu": trich_yeu,
            "link_goc": href,
            "ngay_ban_hanh": ngay_ban_hanh,
        })
    return docs


def parse_detail_page(html):
    soup = BeautifulSoup(html, "html.parser")
    info = {}
    for row in soup.select("div.document--focus div.row"):
        name_el = row.select_one("span.name")
        value_el = row.select_one("div.value span.child-value")
        if name_el and value_el:
            info[name_el.get_text(strip=True)] = value_el.get_text(strip=True)
    return info


def enrich_with_detail(doc):
    html = fetch(doc["link_goc"])
    info = parse_detail_page(html)
    if info.get("Số, ký hiệu"):
        doc["so_hieu"] = info["Số, ký hiệu"]
    doc["ngay_ban_hanh"] = parse_vn_date(info.get("Ngày ban hành")) or doc.get("ngay_ban_hanh")
    doc["ngay_hieu_luc"] = parse_vn_date(info.get("Ngày hiệu lực"))
    doc["loai"] = info.get("Loại văn bản")
    doc["co_quan"] = normalize_co_quan(info.get("Cơ quan ban hành"))
    if info.get("Trích yếu"):
        doc["trich_yeu"] = info["Trích yếu"]
    doc["nguon"] = "congbao.chinhphu.vn"
    return doc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    candidates = []
    for n in range(1, MAX_PAGES + 1):
        url = FIRST_PAGE if n == 1 else PAGE_URL.format(n=n)
        page_docs = parse_list_page(fetch(url))
        if not page_docs:
            if n == 1:
                print(
                    "KHÔNG PARSE ĐƯỢC VĂN BẢN NÀO Ở TRANG 1.\n"
                    "Trang có thể đã đổi cấu trúc so với ghi chú trong CLAUDE.md, hoặc lỗi\n"
                    "mạng/allowlist. Agent: fetch trang, parse tay, sửa SELECTORS + cập nhật CLAUDE.md.",
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
                candidates.append(doc)
        if stop:
            break

    in_range = [d for d in candidates if d.get("ngay_ban_hanh") and args.from_date <= d["ngay_ban_hanh"] <= args.to_date]
    docs = [enrich_with_detail(d) for d in in_range]

    out = {
        "source": "congbao.chinhphu.vn",
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
