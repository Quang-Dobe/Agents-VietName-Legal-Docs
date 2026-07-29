#!/usr/bin/env python3
"""Crawl vanban.chinhphu.vn — nguồn chính.

Cách dùng:
    python3 scripts/crawl_vanban.py --from 2026-06-23 --to 2026-06-30 --out /tmp/vanban.json

Output: JSON {"source": ..., "fetched_at": ..., "documents": [...]}
(mỗi document theo schema CLAUDE.md, CHƯA có tom_tat_ai / linh_vuc / trang_thai).

Cấu trúc trang (chốt tại Run 0 recon, PHÂN TRANG xác nhận lại 2026-07-08 — xem "Ghi chú
cấu trúc trang" trong CLAUDE.md):
- Trang danh sách (`{LIST_URL}?classid=1&mode=1`, GET) trả về 50 văn bản MỚI NHẤT toàn hệ
  thống (trang 1), sort ngay_ban_hanh giảm dần — KHÔNG có param GET lọc khoảng ngày.
- Phân trang KHÔNG dùng query string mà dùng ASP.NET Web Forms postback đồng bộ (không
  phải AJAX/UpdatePanel — `Sys.WebForms.PageRequestManager._initialize` được gọi với danh
  sách UpdatePanel rỗng `[]`, tức là postback trả về FULL HTML mới, không phải delta).
  Link trang kế trong HTML dạng `javascript:__doPostBack('ctrl_191017_163$grvDocument',
  'Page$<N>')`. Để lấy trang N: POST lại `{LIST_URL}?classid=1&mode=1` với toàn bộ field
  ẩn/input/select hiện có của trang trước (đặc biệt `__VIEWSTATE`, `__VIEWSTATEGENERATOR`,
  `__EVENTVALIDATION`) cộng thêm `__EVENTTARGET=ctrl_191017_163$grvDocument` và
  `__EVENTARGUMENT=Page$<N>`. Không cần header AJAX (`X-MicrosoftAjax`/`__ASYNCPOST`) —
  thêm các header đó sẽ làm server trả lỗi (redirect JSON tới trang 500) vì trang này
  không có UpdatePanel thật.
  Script gọi trang danh sách lặp lại (GET trang 1, rồi POST các trang kế) cho tới khi ngày
  ban hành CŨ NHẤT trong trang hiện tại < --from (hoặc hết trang / chạm giới hạn request),
  rồi lọc toàn bộ theo [--from, --to] phía client.
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
LIST_PAGE_URL = f"{LIST_URL}?classid=1&mode=1"
PAGER_EVENT_TARGET = "ctrl_191017_163$grvDocument"
MAX_LIST_PAGES = 30  # an toàn, tránh vòng lặp vô hạn nếu trang đổi cấu trúc

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
request_count = 0


def fetch(url, method="GET", data=None, params=None, retries=3):
    global request_count
    if request_count >= MAX_REQUESTS:
        raise RuntimeError(f"Chạm giới hạn {MAX_REQUESTS} request/run")
    if request_count:
        time.sleep(RATE_LIMIT_S)
    request_count += 1
    last_exc = None
    for attempt in range(retries):
        try:
            if method == "POST":
                resp = session.post(url, data=data, timeout=30, headers={"Referer": LIST_PAGE_URL})
            else:
                resp = session.get(url, params=params or None, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            last_exc = exc
            if status in (502, 503, 504) and attempt < retries - 1:
                time.sleep(RATE_LIMIT_S)
                continue
            raise
    raise last_exc


# Một số so_hieu (và, xác nhận 2026-07-29, cả trich_yeu khi văn bản tham chiếu số hiệu văn
# bản khác — vd. "Thông tư số 87/2019/TT- BТC") trên trang nguồn lẫn ký tự Cyrillic trông
# giống hệt Latin (vd. 'Р' U+0420 thay cho 'P' U+0050) — chuẩn hoá về Latin để khớp
# SO_HIEU_RE, tránh trùng lặp giả trong index.json, và tránh rác ký tự trong trích yếu.
_CYRILLIC_TO_LATIN = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X",
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
})


def normalize_cyrillic(text):
    """Chuẩn hoá ký tự Cyrillic nhìn-giống-Latin về Latin. Dùng cho so_hieu VÀ trich_yeu
    (trích yếu đôi khi chứa số hiệu của văn bản khác bị lỗi tương tự)."""
    if not text:
        return text
    return text.translate(_CYRILLIC_TO_LATIN)


# Alias giữ tương thích tên cũ.
normalize_so_hieu = normalize_cyrillic


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


def extract_form_state(soup):
    """Gom mọi input/select/textarea hiện có (kể cả __VIEWSTATE...) để POST lại nguyên trạng
    khi chuyển trang (ASP.NET Web Forms postback đồng bộ)."""
    data = {}
    for inp in soup.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        typ = (inp.get("type") or "text").lower()
        if typ in ("submit", "button", "image", "file"):
            continue
        if typ in ("checkbox", "radio"):
            if inp.has_attr("checked"):
                data[name] = inp.get("value", "on")
            continue
        data[name] = inp.get("value", "")
    for sel in soup.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        data[name] = opt.get("value", "") if opt else ""
    for ta in soup.find_all("textarea"):
        name = ta.get("name")
        if name:
            data[name] = ta.text
    return data


def parse_list_page(soup):
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
            "so_hieu": normalize_cyrillic(code_span.get_text(strip=True)),
            "ngay_ban_hanh": vn_date_slash_to_iso(date_span.get_text(strip=True) if date_span else ""),
            "trich_yeu": normalize_cyrillic(substract.get_text(strip=True)) if substract else None,
            "link_goc": href,
        })
    return docs


PARSE_RETRIES = 3  # xem "Ghi chú độ tin cậy mạng" trong CLAUDE.md — thi thoảng một response 200
                    # hợp lệ về HTTP nhưng không parse ra dòng nào (flaky proxy/mạng), tự hồi
                    # phục bằng cách fetch lại trước khi kết luận hết trang/đổi cấu trúc.


def fetch_list_page(method="GET", data=None):
    """Fetch trang danh sách (GET trang 1 hoặc POST postback trang kế), retry tối đa
    PARSE_RETRIES lần nếu parse ra 0 dòng — tránh kết luận nhầm "hết trang"/"đổi cấu trúc"
    khi thực ra chỉ là một response bị lỗi thoáng qua."""
    soup, rows = None, []
    for _ in range(PARSE_RETRIES):
        html = fetch(LIST_PAGE_URL, method=method, data=data)
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_list_page(soup)
        if rows:
            return soup, rows
    return soup, rows


def fetch_all_list_rows(from_date):
    """GET trang 1, rồi POST (postback) các trang kế tiếp cho tới khi ngày ban hành cũ nhất
    của trang hiện tại < from_date, hoặc hết trang, hoặc chạm MAX_LIST_PAGES."""
    soup, rows = fetch_list_page(method="GET")
    all_rows = list(rows)

    page_num = 1
    while True:
        dated = [r["ngay_ban_hanh"] for r in rows if r.get("ngay_ban_hanh")]
        oldest = min(dated) if dated else None
        if not rows or oldest is None or oldest < from_date or page_num >= MAX_LIST_PAGES:
            break
        page_num += 1
        state = extract_form_state(soup)
        state["__EVENTTARGET"] = PAGER_EVENT_TARGET
        state["__EVENTARGUMENT"] = f"Page${page_num}"
        soup, rows = fetch_list_page(method="POST", data=state)
        if not rows:
            break
        all_rows.extend(rows)

    return all_rows


def parse_detail_page(html):
    soup = BeautifulSoup(html, "html.parser")
    info = {}
    for tr in soup.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2 and "col1" in (tds[0].get("class") or []):
            info[tds[0].get_text(strip=True)] = tds[1].get_text(" ", strip=True)
    return info


def fetch_detail_info(url):
    """Fetch + parse trang chi tiết, retry tối đa PARSE_RETRIES lần nếu không thấy nhãn
    'Số ký hiệu' (parse rỗng/hỏng do response lỗi thoáng qua)."""
    info = {}
    for _ in range(PARSE_RETRIES):
        html = fetch(url, method="GET")
        info = parse_detail_page(html)
        if info.get("Số ký hiệu"):
            return info
    return info


def enrich_with_detail(doc):
    info = fetch_detail_info(doc["link_goc"])
    if info.get("Số ký hiệu"):
        doc["so_hieu"] = normalize_cyrillic(info["Số ký hiệu"])
    doc["ngay_ban_hanh"] = vn_date_dash_to_iso(info.get("Ngày ban hành")) or doc.get("ngay_ban_hanh")
    doc["ngay_hieu_luc"] = vn_date_dash_to_iso(info.get("Ngày có hiệu lực"))
    doc["loai"] = info.get("Loại văn bản")
    doc["co_quan"] = info.get("Cơ quan ban hành")
    if info.get("Trích yếu"):
        doc["trich_yeu"] = normalize_cyrillic(info["Trích yếu"])
    doc["nguon"] = "vanban.chinhphu.vn"
    return doc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = fetch_all_list_rows(args.from_date)

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
    # Sau khi phân trang hết mức (MAX_LIST_PAGES hoặc chạm request limit) mà vẫn chưa lùi
    # được tới trước --from thì đánh dấu có thể sót.
    possibly_truncated = bool(oldest) and oldest >= args.from_date

    # Dedupe theo (so_hieu, link_goc) — cùng văn bản có thể lặp giữa 2 trang nếu postback lệch.
    seen = set()
    in_range = []
    for d in dated_rows:
        if not (args.from_date <= d["ngay_ban_hanh"] <= args.to_date):
            continue
        key = (d["so_hieu"], d["link_goc"])
        if key in seen:
            continue
        seen.add(key)
        in_range.append(d)

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
    note = " (CÓ THỂ SÓT — chưa lùi được tới trước --from, cần agent xử lý thêm)" if possibly_truncated else ""
    print(f"OK: {len(docs)} văn bản → {args.out} ({request_count} request){note}")


if __name__ == "__main__":
    main()
