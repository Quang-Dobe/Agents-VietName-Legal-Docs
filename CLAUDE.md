# vn-legal-docs-weekly

Crawl văn bản pháp luật Việt Nam mới ban hành **mỗi 2 ngày một lần**, tóm tắt bằng AI,
gom dữ liệu theo tuần ISO, xuất static site lên GitHub Pages.

## Cấu trúc repo

```
.claude/agents/      # 4 subagent: crawler-chinhphu, crawler-congbao, summarizer, site-builder
ROUTINE_PROMPT.md    # prompt routine định kỳ 2 ngày/lần (dữ liệu vẫn gom theo tuần)
BACKFILL_PROMPTS.md  # chuỗi prompt backfill một lần
scripts/             # crawl / merge / validate / update_status / build_site
site-src/            # templates Jinja2 + assets (KHÔNG sửa docs/ bằng tay)
data/                # dữ liệu JSON theo tuần + index + run-log
docs/                # OUTPUT — GitHub Pages serve từ đây
```

## Nguồn dữ liệu

| Nguồn | URL | Vai trò |
|---|---|---|
| vanban.chinhphu.vn | `https://vanban.chinhphu.vn/he-thong-van-ban?classid=1&mode=1` | Chính |
| congbao.chinhphu.vn | `https://congbao.chinhphu.vn/van-ban-dang-cong-bao.htm` (phân trang `/van-ban-dang-cong-bao/trang-{N}.htm`, sort mới → cũ) | Đối chiếu |
| vbpl.vn | `https://vbpl.vn` | Backup khi 2 nguồn trên fail |

KHÔNG crawl thuvienphapluat.vn / luatvietnam.vn (nội dung trả phí, ToS chặt).

### Ghi chú cấu trúc trang (cập nhật sau mỗi lần selectors thay đổi)

> **Run 0 recon đã chạy (2026-07-08).** robots.txt cả 2 nguồn đều `Allow: /`, không có
> `Crawl-delay` — rate limit 3s/request của repo là đủ an toàn.

**vanban.chinhphu.vn** (nguồn chính, ASP.NET WebForms):
- Trang danh sách `{BASE}/he-thong-van-ban?classid=1&mode=1` (GET) trả về **50 văn bản mới
  nhất toàn hệ thống** (trang 1), sort `ngay_ban_hanh` giảm dần. Không có param GET lọc
  khoảng ngày; form nâng cao dùng postback ASP.NET (`__VIEWSTATE`).
- **Phân trang (xác nhận 2026-07-08):** link "trang kế" trong HTML là
  `javascript:__doPostBack('ctrl_191017_163$grvDocument','Page$<N>')` — đây là postback
  ĐỒNG BỘ (full-page), KHÔNG phải AJAX/UpdatePanel (`PageRequestManager._initialize` được
  gọi với danh sách UpdatePanel rỗng `[]`). Để lấy trang N: POST lại cùng URL với TOÀN BỘ
  input/select/textarea hiện có của trang trước (đặc biệt `__VIEWSTATE`,
  `__VIEWSTATEGENERATOR`, `__EVENTVALIDATION`) cộng `__EVENTTARGET=ctrl_191017_163$grvDocument`
  + `__EVENTARGUMENT=Page$<N>`. KHÔNG thêm header AJAX (`X-MicrosoftAjax`, `__ASYNCPOST`) —
  làm vậy server trả lỗi (redirect JSON tới trang 500) vì không có UpdatePanel thật.
  Script (`crawl_vanban.py::fetch_all_list_rows`) GET trang 1 rồi POST các trang kế tiếp cho
  tới khi ngày ban hành cũ nhất của trang hiện tại < `--from`, rồi lọc theo khoảng ngày phía
  client. Nếu vẫn chưa lùi đủ (hết trang / chạm `MAX_LIST_PAGES`/giới hạn request) →
  `possibly_truncated: true` trong output → agent tự fetch bù (xem "Self-healing").
- Trang chi tiết đôi khi trả `502 Bad Gateway` thoáng qua — script retry tối đa 3 lần cho
  status `502/503/504` (đã có sẵn trong `fetch()`).
- **Flaky parse thoáng qua (xác nhận 2026-07-21):** đôi khi cả trang danh sách (GET trang 1)
  lẫn trang chi tiết trả về HTTP 200 nhưng nội dung không parse ra dòng/nhãn nào (không phải
  đổi cấu trúc trang — fetch lại vài giây sau parse bình thường; nghi do mạng/proxy chập
  chờn, không phải lỗi từ phía vanban.chinhphu.vn). Script (`fetch_list_page`,
  `fetch_detail_info`) giờ tự retry tối đa `PARSE_RETRIES = 3` lần khi parse ra rỗng
  (0 dòng danh sách, hoặc thiếu nhãn "Số ký hiệu" ở trang chi tiết) trước khi chấp nhận kết
  quả rỗng/hỏng — KHÔNG tính là "đổi cấu trúc trang" trừ khi rỗng cả 3 lần liên tiếp.
- **Ký tự Cyrillic giả Latin trong so_hieu (mở rộng sang trich_yeu, xác nhận 2026-07-29):**
  một số bản ghi trên trang nguồn có `so_hieu` lẫn ký tự Cyrillic nhìn giống hệt Latin
  (vd. `Р` U+0420 thay cho `P` U+0050). Đồng thời phát hiện cùng lỗi này xuất hiện cả trong
  `trich_yeu` khi trích yếu có nhắc tới số hiệu của một văn bản KHÁC bị lỗi tương tự (vd. văn
  bản `105/2026/TT-BTC` có trích yếu "Bãi bỏ Thông tư số 87/2019/TT- BТC..." — chữ `Т` trong
  "BТC" là Cyrillic U+0422). Script (`normalize_cyrillic`, tên cũ `normalize_so_hieu` vẫn còn
  alias) tự chuẩn hoá các ký tự nhìn-giống-Latin (А В Е К М Н О Р С Т Х và chữ thường tương
  ứng) về Latin trước khi ghi — áp dụng cho CẢ `so_hieu` LẪN `trich_yeu`, lấy từ cả trang danh
  sách và trang chi tiết.
- **Dữ liệu nguồn có thể tự mâu thuẫn (quan sát 2026-07-29):** văn bản `106/2026/TT-BTC` có
  "Ngày ban hành" = `22-07-2026` nhưng "Ngày có hiệu lực" hiển thị = `22-07-2025` (SỚM HƠN 1
  năm so với ngày ban hành) ngay trên trang chi tiết của chính vanban.chinhphu.vn — đã xác
  nhận đây là lỗi nhập liệu của nguồn (không phải lỗi parse của script, HTML thô đã kiểm tra
  trực tiếp cho kết quả tương tự). Trường hợp này sẽ FAIL rule validate #3
  (`ngay_hieu_luc ≥ ngay_ban_hanh`) — agent gộp/validate dữ liệu cần tự quyết định xử lý
  (vd. đặt `ngay_hieu_luc: null` kèm ghi chú, hoặc giữ nguyên và note bất thường) thay vì coi
  đây là bug crawler.
- Mỗi dòng trong `table.search-result tr`: `span.code` (so_hieu) nằm trong thẻ `a` cha
  (`link_goc`, dạng `/?pageid=...&docid=...&classid=1`), `span.issued-date` (ngày ban hành,
  `DD/MM/YYYY`), `span.substract` (trích yếu rút gọn).
- Trang chi tiết: bảng gồm các `<tr><td class="col1">Nhãn</td><td>Giá trị</td></tr>`. Nhãn dùng:
  `Số ký hiệu`, `Ngày ban hành` (`DD-MM-YYYY`), `Ngày có hiệu lực` (`DD-MM-YYYY`, dòng có thể
  vắng nếu chưa xác định), `Loại văn bản` (khớp thẳng taxonomy `loai`), `Cơ quan ban hành`,
  `Người ký`, `Trích yếu` (đầy đủ hơn bản rút gọn ở trang danh sách).

**congbao.chinhphu.vn** (nguồn đối chiếu):
- Danh sách "Văn bản mới nhất": `/van-ban-dang-cong-bao.htm` rồi `/van-ban-dang-cong-bao/trang-{N}.htm`,
  sort mới → cũ. Mỗi văn bản là `div.box--list div.item--vb`: `span.kh` chứa text
  `"Ký hiệu: {so_hieu}"`; `div.middle a.sapo` (`title` = trích yếu, `href` = link chi tiết
  `/van-ban/....htm`); `div.bot span.days` chứa text `"[Ban hành: DD/MM/YYYY]"`.
- Trang chi tiết: `div.document--focus div.row` > `span.name` (nhãn) + `div.value
  span.child-value` (giá trị). Nhãn dùng: `Số, ký hiệu`, `Loại văn bản`, `Cơ quan ban hành`
  (thường IN HOA — script title-case lại cho nhất quán), `Ngày ban hành` (`DD/MM/YYYY`),
  `Ngày hiệu lực` (`DD/MM/YYYY`, có thể rỗng), `Trích yếu`.
- Một số văn bản congbao thuộc loại ngoài enum `loai` của schema (vd. công điện, chỉ thị) —
  các văn bản này bị loại khi validate; chỉ giữ văn bản khớp `LOAI_HOP_LE`.
- **Độ trễ đăng công báo (quan sát 2026-07-15, xác nhận lại 2026-08-11, 2026-08-16):** danh
  sách "Văn bản mới nhất" sort đúng theo `ngay_ban_hanh` giảm dần, nhưng việc đăng lên công báo
  có độ trễ so với ngày ban hành thực tế (dao động, đã thấy từ ~6 đến ~10 ngày, không phải
  hằng số cố định ~1 tuần). Vì vậy khi crawl với `--to` gần ngày hiện tại, kết quả `0 văn bản`
  sau đúng 1 request (dừng ngay ở trang 1 vì văn bản mới nhất đã cũ hơn `--from`) là **kết quả
  hợp lệ**, KHÔNG phải lỗi script — cần xác nhận bằng cách fetch tay 2-3 trang đầu xem ngày có
  giảm dần đơn điệu hay không trước khi kết luận có bug. Run 2026-08-11
  (`--from 2026-08-02 --to 2026-08-11`, ngày chạy = 2026-08-11): văn bản mới nhất trên công báo
  tại thời điểm đó có `ngay_ban_hanh = 2026-08-05` → độ trễ ~6 ngày. Run 2026-08-16
  (`--from 2026-08-12 --to 2026-08-16`, ngày chạy = 2026-08-16): văn bản mới nhất trên công báo
  có `ngay_ban_hanh = 2026-08-06` → độ trễ ~10 ngày (kiểm tra tay 10 mục đầu trang 1, ngày giảm
  dần đơn điệu 06/08 → 05/08 → 04/08...).
- **Bug console Windows (xác nhận 2026-08-11, sửa tận gốc 2026-08-11):** `print()` dòng tổng
  kết cuối script chứa tiếng Việt có dấu → trên console Windows mặc định (codepage `cp1252`,
  không phải UTF-8) ném `UnicodeEncodeError` và script exit code `1` **dù file JSON đã được
  ghi thành công** trước đó (lỗi xảy ra ở dòng `print` cuối, sau `json.dump`). Ban đầu vá
  riêng trong `crawl_congbao.py`, sau đó phát hiện `merge_dedupe.py` gặp lỗi tương tự → sửa
  tận gốc trong `scripts/common.py` (ép `sys.stdout`/`sys.stderr` sang `encoding="utf-8"` qua
  `reconfigure()` ngay khi import `common`) vì **mọi** script (`crawl_vanban`, `crawl_congbao`,
  `merge_dedupe`, `update_status`, `validate_data`, `build_site`) đều import module này. Nếu
  caller/CI kiểm tra exit code để quyết định fail/success, cần lưu ý bug này đã được vá —
  không phải lỗi cấu trúc trang hay dữ liệu.

### Quy tắc crawl

- Rate limit **3 giây/request**. Tối đa **150 request/run**.
- User-Agent: `vn-legal-docs-weekly/1.0 (+https://github.com/Quang-Dobe/Agents-VietName-Legal-Docs)`
- Chỉ fetch trang danh sách + trang chi tiết văn bản. Tôn trọng robots.txt (ghi chú kết luận ở trên sau Run 0).

## Schema văn bản

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

- File tuần: `data/{năm}/week-{tuần ISO}.json` — `{"tuan": "2026-W27", "documents": [...]}`, sort `ngay_ban_hanh` giảm dần.
- Index: `data/index.json` — `{"<so_hieu>": {"tuan": "2026/week-27", "trang_thai": "..."}}`, dùng để dedupe + tra cứu.
- `ngay_hieu_luc` có thể `null` nếu chưa xác định được.
- `nguon` ∈ {`vanban.chinhphu.vn`, `congbao.chinhphu.vn`, `vbpl.vn`, `demo`} (`demo` chỉ cho dữ liệu mẫu xem giao diện — phải xoá sạch khi có dữ liệu thật).

## Quy tắc validate (chạy `python3 scripts/validate_data.py` trước MỌI commit dữ liệu)

1. `so_hieu` duy nhất toàn index; khớp regex trong `validate_data.py`.
2. `loai` ∈ {Luật, Nghị quyết, Nghị định, Quyết định, Thông tư, Thông tư liên tịch, Pháp lệnh, Lệnh, Văn bản hợp nhất}.
3. Ngày dạng `YYYY-MM-DD`; `ngay_hieu_luc` ≥ `ngay_ban_hanh` hoặc `null`.
4. `linh_vuc` thuộc taxonomy 16 mục bên dưới. `trang_thai` ∈ {`chua_hieu_luc`, `con_hieu_luc`, `het_hieu_luc_mot_phan`, `het_hieu_luc`}.
5. `link_goc` thuộc domain nguồn chính thống.
6. `tom_tat_ai`: 3–5 câu, ≤ 120 từ.

## Taxonomy lĩnh vực (16 — cố định, chọn đúng 1)

`Thuế - Phí - Lệ phí` · `Đất đai - Nhà ở` · `Lao động - Tiền lương` · `Bảo hiểm` · `Doanh nghiệp - Đầu tư` · `Tài chính - Ngân hàng` · `Xây dựng - Đô thị` · `Giao thông - Vận tải` · `Y tế` · `Giáo dục` · `Khoa học - Công nghệ số` · `Tài nguyên - Môi trường` · `Quốc phòng - An ninh` · `Hành chính - Tổ chức` · `Tư pháp - Xử phạt` · `Khác`

Chỉ dùng `Khác` khi thực sự không map được.

## Văn phong tóm tắt (bắt buộc)

- 3–5 câu, mỗi câu ≤ 20 từ, mỗi câu một ý.
- Trả lời: **Ai bị ảnh hưởng? Thay đổi gì? Từ khi nào?**
- Từ thường thay từ pháp lý khó ("bãi bỏ" → "bỏ", "kể từ thời điểm" → "từ ngày").
- Không lặp nguyên văn trích yếu.

## Nguyên tắc vận hành

- **Self-healing:** script fail → agent tự fetch và parse tay → nếu thành công, PHẢI sửa script + cập nhật "Ghi chú cấu trúc trang" ở trên, commit cùng lần.
- **An toàn dữ liệu:** không bao giờ xoá/ghi đè dữ liệu tuần cũ; chỉ thêm văn bản mới và cập nhật `trang_thai`/`bi_sua_doi_boi`.
- **Build site:** chỉ qua `python3 scripts/build_site.py`; không sửa tay file trong `docs/`.
- **Commit:** run định kỳ → `update: {YYYY-MM-DD} — {N} văn bản mới`; backfill →
  `backfill: {năm}-W{tuần} — {N} văn bản`; sửa script → `fix(crawler): ...` kèm lý do.
- Cả 2 nguồn fail → ghi `data/run-log.md`, commit run-log, DỪNG (không build, không xoá gì).

## Môi trường

- Custom cloud environment cần allowlist: `vanban.chinhphu.vn`, `congbao.chinhphu.vn`, `*.chinhphu.vn`, `vbpl.vn`.
- Setup: `pip install requests beautifulsoup4 jinja2 markdown`.
- GitHub Pages: deploy tự động qua GitHub Actions (`.github/workflows/deploy-pages.yml`,
  upload artifact `docs/` khi push `main`). Yêu cầu Settings → Pages → Source = "GitHub Actions".
