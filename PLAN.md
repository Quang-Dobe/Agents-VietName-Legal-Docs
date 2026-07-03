# Detail Plan — `vn-legal-docs-weekly`

> Kế hoạch chi tiết trước khi implement. Dựa trên brief `repo1vnlegaldocsweekly.md`.
> Yêu cầu bổ sung từ chủ dự án: **dark theme, UI đẹp, có logo + favicon, câu chữ đơn giản – dễ hiểu – ngắn**.

---

## 0. Kết quả verify nguồn (đã kiểm tra 2026-07-03)

| Hạng mục | Kết quả |
|---|---|
| `vanban.chinhphu.vn` | Hoạt động. Trang danh sách: `https://vanban.chinhphu.vn/he-thong-van-ban?classid=1&mode=1`. Có filter theo loại văn bản (`typegroupid=...`), cơ quan ban hành, khoảng ngày ban hành, lĩnh vực, trạng thái hiệu lực. |
| `congbao.chinhphu.vn` | Hoạt động. Văn bản mới đăng công báo: `https://congbao.chinhphu.vn/van-ban-dang-cong-bao.htm`, phân trang dạng `/van-ban-dang-cong-bao/trang-{N}.htm`. |
| Nguồn backup | `vbpl.vn` (CSDL quốc gia về VBQPPL, Bộ Tư pháp) — nguồn duy nhất có giá trị pháp lý tương đương bản giấy. Dùng khi 2 nguồn chính fail. |
| Fetch trực tiếp từ sandbox mặc định | **Bị chặn (proxy trả 403 CONNECT — policy denial)**. Đúng như brief cảnh báo → bắt buộc tạo custom cloud environment có allowlist domain (mục 6). |
| Cấu trúc HTML chi tiết (selectors) | **Chưa xác định được từ session này** (do bị chặn mạng). Giải quyết bằng **Run 0 — Recon** (mục 11): one-off routine chạy trong custom environment, dump HTML thật + robots.txt, ghi selectors vào `CLAUDE.md` trước khi viết parser hoàn chỉnh. |

---

## 1. Các quyết định chốt

| # | Câu hỏi | Quyết định |
|---|---|---|
| 1 | Phân loại lĩnh vực | **Taxonomy cố định 16 lĩnh vực** trong `CLAUDE.md`, agent map vào. Không rule-based (tên lĩnh vực trên nguồn không nhất quán). |
| 2 | Văn bản sửa đổi/thay thế | Văn bản mới ghi `sua_doi_thay_the: [số hiệu cũ]`. Script `update_status.py` tra `data/index.json`, cập nhật `trang_thai` văn bản cũ trong file tuần gốc + thêm trường ngược `bi_sua_doi_boi`. Index lưu `so_hieu → {tuan, trang_thai}` để tra nhanh. |
| 3 | Giới hạn độ dài khi tóm tắt | Tóm tắt từ **trích yếu + tối đa 4.000 ký tự đầu nội dung** + điều khoản hiệu lực (thường ở cuối — fetch riêng đoạn cuối nếu cần ngày hiệu lực). Không đọc toàn văn luật dài. |
| 4 | robots.txt & tần suất | Run 0 fetch robots.txt cả 2 nguồn, ghi kết luận vào `CLAUDE.md`. Rate limit **3s/request**, tối đa **~150 request/run**, User-Agent khai báo rõ ràng, chỉ crawl trang danh sách + trang chi tiết. |
| 5 | Deploy | Routine **push thẳng `main`** (bật "Allow unrestricted branch pushes"). GitHub Pages serve từ `main`, thư mục **`/docs`**. Không cần GitHub Actions. |
| 6 | Thư mục output site | **`docs/` chứ không phải `site/`** — GitHub Pages (branch-based) chỉ serve từ `/` hoặc `/docs`. Đây là điểm sửa so với brief. |
| 7 | Template engine | Python + **Jinja2** (pypi được phép trong environment mặc định). JS thuần cho filter client-side, không framework. |
| 8 | Font | Self-host **Be Vietnam Pro** (WOFF2, SIL OFL — hỗ trợ tiếng Việt tốt), fallback system font. Không phụ thuộc CDN ngoài. |

---

## 2. Cấu trúc repo

```
.claude/agents/
  crawler-chinhphu.md      # crawl vanban.chinhphu.vn
  crawler-congbao.md       # crawl congbao.chinhphu.vn
  summarizer.md            # tóm tắt + phân loại + viết Điểm tin tuần
  site-builder.md          # build HTML vào docs/
CLAUDE.md                  # schema, validate, taxonomy, selectors nguồn, ghi chú robots.txt
ROUTINE_PROMPT.md          # prompt routine hàng tuần (version control)
BACKFILL_PROMPTS.md        # chuỗi prompt one-off backfill
scripts/
  crawl_vanban.py          # crawl helper nguồn chính
  crawl_congbao.py         # crawl helper nguồn đối chiếu
  merge_dedupe.py          # gộp 2 nguồn, dedupe theo số hiệu
  validate_data.py         # validate JSON theo schema, exit != 0 nếu sai
  update_status.py         # cập nhật trạng thái văn bản bị sửa đổi/thay thế
  build_site.py            # render Jinja2 → docs/
site-src/
  templates/               # base.html, index.html, tuan.html, diem-tin.html, luu-tru.html
  assets/                  # style.css, app.js, logo.svg, favicon.svg + .png, fonts/
data/
  index.json               # so_hieu → {tuan, trang_thai}
  run-log.md               # log mỗi run
  backfill-progress.json   # checkpoint backfill
  2026/week-27.json        # văn bản theo tuần
  weekly-digest/2026-week-27.md
docs/                      # OUTPUT — GitHub Pages serve từ đây (không sửa tay)
```

---

## 3. Schema dữ liệu + quy tắc validate (nội dung sẽ nằm trong `CLAUDE.md`)

### 3.1 Schema mỗi văn bản

Giữ nguyên schema brief, bổ sung 2 trường:

```json
{
  "so_hieu": "15/2026/ND-CP",
  "loai": "Nghị định",
  "co_quan": "Chính phủ",
  "ngay_ban_hanh": "2026-06-28",
  "ngay_hieu_luc": "2026-08-15",
  "trich_yeu": "…",
  "linh_vuc": "Thuế - Phí - Lệ phí",
  "link_goc": "https://vanban.chinhphu.vn/…",
  "tom_tat_ai": "3-5 câu, văn phong đơn giản",
  "trang_thai": "chua_hieu_luc",
  "sua_doi_thay_the": [],
  "bi_sua_doi_boi": [],
  "nguon": "vanban.chinhphu.vn"
}
```

### 3.2 Quy tắc validate (`scripts/validate_data.py` — chạy trước mọi commit)

1. `so_hieu` khớp regex `^[\w.-]+/\d{4}/[\w-]+$` hoặc dạng đặc biệt (`\d+/\d{4}/(QH\d+|UBTVQH\d+)`); **duy nhất toàn index**.
2. `loai` ∈ {Luật, Nghị quyết, Nghị định, Quyết định, Thông tư, Thông tư liên tịch, Pháp lệnh, Lệnh, Văn bản hợp nhất}.
3. Ngày dạng ISO `YYYY-MM-DD`; `ngay_hieu_luc` ≥ `ngay_ban_hanh` hoặc `null` (nếu chưa xác định).
4. `linh_vuc` ∈ taxonomy 16 mục (3.3). `trang_thai` ∈ {`chua_hieu_luc`, `con_hieu_luc`, `het_hieu_luc_mot_phan`, `het_hieu_luc`}.
5. `link_goc` phải thuộc domain nguồn chính thống (allowlist mục 6).
6. `tom_tat_ai`: 3–5 câu, ≤ 120 từ, không chứa cụm "văn bản này quy định" lặp máy móc.
7. File tuần sort theo `ngay_ban_hanh` giảm dần; index.json sort theo key.

### 3.3 Taxonomy lĩnh vực (16, cố định)

`Thuế - Phí - Lệ phí` · `Đất đai - Nhà ở` · `Lao động - Tiền lương` · `Bảo hiểm` · `Doanh nghiệp - Đầu tư` · `Tài chính - Ngân hàng` · `Xây dựng - Đô thị` · `Giao thông - Vận tải` · `Y tế` · `Giáo dục` · `Khoa học - Công nghệ số` · `Tài nguyên - Môi trường` · `Quốc phòng - An ninh` · `Hành chính - Tổ chức` · `Tư pháp - Xử phạt` · `Khác`

Quy tắc: agent chọn **đúng 1** lĩnh vực sát nhất; chỉ dùng `Khác` khi thực sự không map được.

---

## 4. Subagents — nội dung `.claude/agents/*.md`

Khung chung mỗi file: frontmatter (`name`, `description`, `tools`), rồi nhiệm vụ + nguyên tắc self-healing.

### 4.1 `crawler-chinhphu.md`

```markdown
---
name: crawler-chinhphu
description: Crawl văn bản mới từ vanban.chinhphu.vn trong khoảng ngày cho trước
tools: Bash, Read, Write, WebFetch
---
Nhiệm vụ: lấy danh sách văn bản ban hành trong khoảng [từ_ngày, đến_ngày] được giao.

Quy trình:
1. Chạy `python scripts/crawl_vanban.py --from {từ_ngày} --to {đến_ngày} --out {file_tạm}`.
2. Kiểm tra output: JSON hợp lệ, có ≥ 0 văn bản, đủ trường bắt buộc (so_hieu, loai, ngay_ban_hanh, trich_yeu, link_goc).
3. Nếu script fail hoặc output nghi ngờ (0 văn bản trong tuần có ngày làm việc, trường trống hàng loạt):
   fetch trực tiếp trang danh sách, đối chiếu HTML với selectors ghi trong CLAUDE.md,
   parse thủ công, SỬA LUÔN script + cập nhật ghi chú selectors trong CLAUDE.md.
4. Trả về: đường dẫn file JSON tạm + số lượng văn bản + ghi chú bất thường (nếu có).

Ràng buộc: rate limit 3s/request; không fetch quá 150 trang; không crawl nguồn ngoài allowlist.
```

### 4.2 `crawler-congbao.md`

Cùng khung với 4.1, khác biệt:
- Nguồn: `congbao.chinhphu.vn/van-ban-dang-cong-bao.htm` + phân trang `trang-{N}.htm`.
- Chạy `scripts/crawl_congbao.py`. Duyệt từ trang 1, **dừng khi gặp văn bản có ngày đăng cũ hơn `từ_ngày`** (danh sách sort mới → cũ) — không cần filter ngày phía server.
- Vai trò: **đối chiếu, bổ sung** — bắt văn bản nguồn chính bỏ sót (nhất là thông tư cấp bộ).

### 4.3 `summarizer.md`

```markdown
---
name: summarizer
description: Tóm tắt, phân loại văn bản mới và viết Điểm tin tuần
tools: Read, Write, WebFetch
---
Input: file JSON các văn bản MỚI (đã dedupe), chưa có tom_tat_ai / linh_vuc.

Với từng văn bản:
1. Đọc trich_yeu. Nếu chưa đủ để tóm tắt tốt: fetch link_goc, lấy tối đa 4.000 ký tự đầu
   + tìm điều khoản hiệu lực để điền ngay_hieu_luc.
2. Viết tom_tat_ai theo VĂN PHONG BẮT BUỘC:
   - 3–5 câu, mỗi câu ≤ 20 từ, mỗi câu một ý.
   - Trả lời: Ai bị ảnh hưởng? Thay đổi gì? Từ khi nào?
   - Không dùng từ pháp lý khó nếu có từ thường thay được
     (ví dụ: "bãi bỏ" → "bỏ", "kể từ thời điểm" → "từ ngày").
   - Không lặp lại nguyên văn trích yếu.
3. Gán đúng 1 linh_vuc theo taxonomy trong CLAUDE.md.
4. Suy ra trang_thai từ ngay_hieu_luc so với ngày chạy.
5. Nếu văn bản sửa đổi/thay thế văn bản khác: điền sua_doi_thay_the (chỉ số hiệu).

Sau khi xong tất cả: viết data/weekly-digest/{năm}-week-{tuần}.md — "Điểm tin tuần":
- Mở đầu 2–3 câu: tuần này có gì đáng chú ý nhất.
- 3–5 điểm nhấn, mỗi điểm 2–3 câu, chọn văn bản ảnh hưởng nhiều người nhất.
- Cuối: một dòng thống kê (tổng số văn bản, theo loại).
```

### 4.4 `site-builder.md`

```markdown
---
name: site-builder
description: Build static site từ data/ vào docs/
tools: Bash, Read, Write, Edit
---
1. Chạy `python scripts/validate_data.py` — dừng ngay nếu fail.
2. Chạy `python scripts/build_site.py` — render toàn bộ docs/.
3. Kiểm tra sanity: docs/index.html tồn tại, chứa số hiệu văn bản mới nhất tuần này,
   không có chuỗi template chưa render ({{ ... }}), mọi trang có <link rel="icon">.
4. Nếu template lỗi: sửa template trong site-src/, KHÔNG sửa tay file trong docs/.
```

---

## 5. `ROUTINE_PROMPT.md` — prompt routine hàng tuần (bản hoàn chỉnh)

```markdown
Bạn là orchestrator của vn-legal-docs-weekly. Hôm nay chạy cập nhật tuần.

0. Đọc CLAUDE.md và data/index.json. Xác định tuần ISO hiện tại và khoảng ngày cần crawl:
   từ (ngày ban hành mới nhất trong index − 1 ngày) đến hôm nay; tối đa 14 ngày.
1. Spawn SONG SONG 2 subagent: crawler-chinhphu và crawler-congbao với khoảng ngày trên.
   Nếu MỘT nguồn fail: ghi vào data/run-log.md, tiếp tục với nguồn còn lại.
   Nếu CẢ HAI fail: ghi run-log, commit run-log, DỪNG — không build site, không xoá dữ liệu cũ.
2. Chạy scripts/merge_dedupe.py: gộp 2 output, loại văn bản đã có trong index (theo so_hieu).
   Kết quả = danh sách văn bản MỚI. Nếu rỗng: ghi run-log "tuần không có văn bản mới",
   vẫn build lại site (để cập nhật trạng thái hiệu lực) rồi kết thúc.
3. Spawn summarizer với danh sách văn bản mới.
4. Chạy scripts/update_status.py để cập nhật văn bản bị sửa đổi/thay thế.
5. Ghi văn bản mới vào data/{năm}/week-{tuần}.json, cập nhật data/index.json.
6. Chạy scripts/validate_data.py — nếu fail: sửa dữ liệu cho đúng schema rồi chạy lại; 
   không được commit dữ liệu không hợp lệ.
7. Spawn site-builder.
8. Ghi data/run-log.md: ngày giờ, nguồn ok/fail, số văn bản mới, số request đã dùng.
9. Commit tất cả với message "weekly: {năm}-W{tuần} — {N} văn bản mới" và push lên main.

Nguyên tắc self-healing: mọi lần script fail mà bạn parse tay thành công,
PHẢI sửa script + cập nhật ghi chú cấu trúc trang trong CLAUDE.md, commit kèm luôn.
Nguyên tắc an toàn: không bao giờ xoá/ghi đè dữ liệu tuần cũ; chỉ thêm và cập nhật trạng thái.
```

---

## 6. Custom cloud environment — allowed domains

Đã xác nhận môi trường mặc định **chặn** các domain này (403 tại proxy). Environment mới cần allowlist:

| Domain | Vai trò |
|---|---|
| `vanban.chinhphu.vn` | Nguồn chính |
| `congbao.chinhphu.vn` | Nguồn đối chiếu |
| `chinhphu.vn`, `*.chinhphu.vn` | Redirect + file đính kèm (datafiles.chinhphu.vn) |
| `vbpl.vn` | Nguồn backup |

(GitHub, pypi.org đã nằm sẵn trong allowlist mặc định — không cần thêm.)

Setup script của environment: `pip install requests beautifulsoup4 jinja2`.

---

## 7. Backfill — chuỗi one-off prompts (`BACKFILL_PROMPTS.md`)

Phạm vi: **04/05/2026 → hiện tại** (~9 tuần). **3 one-off routines**, mỗi run ~3 tuần, không tính daily cap.

- **Run B1**: tuần 19–21 (04/05–24/05). **Run B2**: tuần 22–24 (25/05–14/06). **Run B3**: tuần 25–27 (15/06 → nay).
- Mỗi prompt = ROUTINE_PROMPT thu gọn với khoảng ngày cố định + 2 khác biệt:
  1. Trước khi crawl: đọc `data/backfill-progress.json`, bỏ qua tuần đã `done`.
  2. Sau mỗi tuần xử lý xong: cập nhật checkpoint + commit ngay (run sau resume được nếu đứt giữa chừng).
- Tóm tắt AI làm ngay trong từng run. Run B3 kết thúc bằng: kiểm tra index không trùng `so_hieu`, build site đầy đủ, commit "initial backfill complete".
- Lịch: B1 chạy trước, B2 sau B1 ~2 giờ, B3 sau B2 ~2 giờ (tránh chồng lấn push).

---

## 8. Scripts — skeleton

Tất cả script: Python 3, chỉ dùng `requests` + `beautifulsoup4`, in JSON ra file, exit code chuẩn để agent bắt lỗi.

```python
# scripts/crawl_vanban.py (khung)
# usage: python crawl_vanban.py --from 2026-06-23 --to 2026-06-30 --out /tmp/vanban.json
BASE = "https://vanban.chinhphu.vn/he-thong-van-ban"
HEADERS = {"User-Agent": "vn-legal-docs-weekly/1.0 (+https://github.com/quang-dobe/agents-vietname-legal-docs)"}
RATE_LIMIT_S = 3

def fetch_list(from_date, to_date):
    # classid=1&mode=1 + params lọc ngày — CHỐT PARAM THẬT SAU RUN 0 RECON
    # phân trang: lặp đến khi hết kết quả hoặc chạm MAX_PAGES
    ...
def parse_row(html_row) -> dict:  # → dict theo schema, thiếu tom_tat_ai/linh_vuc
    ...
def main():  # argparse → fetch → parse → ghi JSON {"documents": [...], "fetched_at": ..., "source": ...}
    ...
```

- `crawl_congbao.py`: cùng khung; duyệt `trang-{N}.htm` từ 1, dừng khi ngày đăng < `--from`.
- `merge_dedupe.py`: đọc N file input + `data/index.json` → in danh sách văn bản mới; ưu tiên bản ghi từ vanban.chinhphu.vn khi trùng số hiệu.
- `validate_data.py`: toàn bộ rule mục 3.2; in từng lỗi kèm số hiệu văn bản; exit 1 nếu có lỗi.
- `update_status.py`: với mỗi văn bản mới có `sua_doi_thay_the` → tìm tuần chứa văn bản cũ qua index → cập nhật `trang_thai` + `bi_sua_doi_boi` → ghi lại file tuần + index.
- `build_site.py`: load toàn bộ `data/` → render Jinja2 → `docs/`; copy assets; sinh `docs/data/all.json` (rút gọn) cho filter/search client-side.

---

## 9. Website — thiết kế UI (dark theme)

### 9.1 Tên site & giọng văn

- Tên: **"Văn Bản Mới"** — tagline: *"Điểm tin pháp luật Việt Nam, mỗi tuần một bản."*
- Giọng văn toàn site: **câu ngắn, từ thường, không thuật ngữ nếu tránh được**. Mọi label UI ≤ 3 từ ("Tuần này", "Điểm tin", "Lưu trữ", "Lọc theo…").

### 9.2 Design tokens (dark theme mặc định — và duy nhất, không cần toggle ở v1)

```css
:root {
  --bg: #0f172a;          /* nền chính — xanh đen slate */
  --surface: #1e293b;     /* card */
  --surface-2: #273449;   /* card hover / header */
  --text: #e2e8f0;        /* chữ chính */
  --muted: #94a3b8;       /* chữ phụ */
  --accent: #fbbf24;      /* vàng hổ phách — link, điểm nhấn, sao trên logo */
  --accent-red: #ef4444;  /* đỏ — badge "Mới", cột mốc hiệu lực gần */
  --border: #33415580;
  --radius: 12px;
}
```

- Badge màu theo **loại văn bản**: Luật `#f59e0b` · Nghị định `#38bdf8` · Thông tư `#a78bfa` · Quyết định `#34d399` · Nghị quyết `#f472b6` · khác `#94a3b8` (nền badge = màu 15% opacity, chữ = màu đậm — đủ tương phản trên nền tối).
- Font: **Be Vietnam Pro** (400/600/700, WOFF2 self-host tại `site-src/assets/fonts/`), fallback `system-ui`. Cỡ chữ nền 16px, line-height 1.6.
- Layout: max-width 1080px, card grid; mobile-first, 1 cột < 640px.

### 9.3 Logo + favicon

- **Concept**: khiên/trang giấy bo góc màu `--surface-2`, viền `--accent`, bên trong **ngôi sao vàng 5 cánh** (gợi quốc kỳ) phía trên **3 vạch ngang** (gợi dòng văn bản). Đơn giản, nhận diện được ở 16×16.
- File: `logo.svg` (header, kèm wordmark "Văn Bản Mới"), `favicon.svg` + `favicon-32.png` + `apple-touch-icon.png` (180×180) sinh từ cùng một SVG.
- Mọi trang: `<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">` + fallback PNG → **logo hiện trên tab trình duyệt**.

### 9.4 Trang & tính năng

| Trang | Nội dung |
|---|---|
| `index.html` — "Tuần này" | Hero nhỏ: tuần số + 1 câu dẫn từ Điểm tin. Bộ lọc 3 dropdown (Loại / Cơ quan / Lĩnh vực) + ô tìm nhanh — JS thuần, lọc trên `docs/data/all.json`. Card văn bản: badge loại, số hiệu, trích yếu, tóm tắt AI (mở rộng khi bấm), ngày hiệu lực, nút "Bản gốc ↗". |
| `diem-tin/{năm}-{tuần}.html` | Bản Điểm tin tuần (render từ markdown) — điểm nhấn giá trị nhất của site, được link nổi bật từ trang chủ. |
| `tuan/{năm}-{tuần}.html` | Archive từng tuần, cùng layout card với trang chủ. |
| `luu-tru.html` | Danh sách tuần theo tháng/năm + số văn bản mỗi tuần. |

- Chi tiết văn bản = **card mở rộng** (details/summary), không sinh trang riêng cho từng văn bản ở v1 (tránh nghìn file HTML).
- Accessibility: contrast ≥ 4.5:1, focus ring rõ, `<html lang="vi">`.

### 9.5 Template skeleton (`site-src/templates/base.html`)

```html
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Văn Bản Mới{% endblock %}</title>
  <meta name="description" content="{% block desc %}Điểm tin pháp luật Việt Nam hàng tuần{% endblock %}">
  <link rel="icon" type="image/svg+xml" href="{{ root }}assets/favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="{{ root }}assets/favicon-32.png">
  <link rel="stylesheet" href="{{ root }}assets/style.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{{ root }}"><img src="{{ root }}assets/logo.svg" alt="" width="28" height="28"> Văn Bản Mới</a>
    <nav><a href="{{ root }}">Tuần này</a><a href="{{ root }}diem-tin/{{ latest_week }}.html">Điểm tin</a><a href="{{ root }}luu-tru.html">Lưu trữ</a></nav>
  </header>
  <main>{% block content %}{% endblock %}</main>
  <footer>Dữ liệu từ nguồn công khai của Chính phủ. Tóm tắt do AI viết — kiểm tra bản gốc trước khi áp dụng.</footer>
  <script src="{{ root }}assets/app.js" defer></script>
</body>
</html>
```

---

## 10. Lộ trình triển khai

| Phase | Việc | Điều kiện xong |
|---|---|---|
| **P0 — Plan** (PR này) | Chốt plan | Plan được duyệt |
| **P1 — Scaffold** | `CLAUDE.md`, 4 agent files, `ROUTINE_PROMPT.md`, `BACKFILL_PROMPTS.md`, skeleton scripts, tạo custom environment + allowlist | Repo đủ khung; validate chạy được với data mẫu |
| **P2 — Recon (Run 0)** | One-off routine trong custom env: fetch robots.txt + dump HTML 2 nguồn, chốt selectors/params thật vào `CLAUDE.md`, hoàn thiện 2 script crawl | Crawl thử 1 tuần gần nhất ra JSON hợp lệ |
| **P3 — Site** | Logo/favicon, CSS dark theme, templates, `build_site.py`; build với dữ liệu Run 0; bật GitHub Pages (`main` + `/docs`) | Site chạy trên Pages, đẹp trên mobile + desktop |
| **P4 — Backfill** | 3 one-off runs B1→B3 | Index đủ ~9 tuần, không trùng số hiệu |
| **P5 — Weekly live** | Bật routine hàng tuần (Thứ Hai ~8h VN = **1h UTC, cron `0 1 * * 1`**), theo dõi 2 run đầu | 2 run liên tiếp xanh, run-log sạch |

## 11. Rủi ro chính & đối phó

| Rủi ro | Đối phó |
|---|---|
| Nguồn đổi cấu trúc HTML | Self-healing: agent parse tay → sửa script → cập nhật CLAUDE.md, cùng 1 commit. |
| Cả 2 nguồn fail 1 tuần | Routine dừng an toàn, giữ nguyên site cũ; tuần sau crawl bù (khoảng ngày tính từ index, tối đa 14 ngày). |
| Chặn bot / captcha | Rate limit 3s, UA khai báo rõ. Nếu vẫn chặn: chuyển `vbpl.vn` làm nguồn chính (đã trong allowlist). |
| Tóm tắt AI sai nội dung pháp lý | Footer disclaimer + luôn kèm link bản gốc; văn phong "ai/cái gì/từ khi nào" giảm suy diễn. |
| Push conflict giữa các run | Backfill chạy cách nhau 2h; routine tuần chỉ 1 run; luôn `git pull --rebase` trước push. |
