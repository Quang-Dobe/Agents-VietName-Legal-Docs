# vn-legal-docs-weekly

Crawl văn bản pháp luật Việt Nam mới ban hành hàng tuần, tóm tắt bằng AI, xuất static site lên GitHub Pages.

## Cấu trúc repo

```
.claude/agents/      # 4 subagent: crawler-chinhphu, crawler-congbao, summarizer, site-builder
ROUTINE_PROMPT.md    # prompt routine hàng tuần
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

> **TODO — Run 0 recon chưa chạy.** Chưa xác nhận: param lọc ngày của vanban.chinhphu.vn,
> selectors của cả 2 trang, nội dung robots.txt. Run 0 phải: fetch robots.txt cả 2 nguồn,
> dump HTML trang danh sách + 1 trang chi tiết, chốt selectors, điền vào mục này, và sửa
> `scripts/crawl_*.py` cho khớp. Trước đó, 2 script crawl sẽ báo lỗi rõ ràng nếu parse ra 0 kết quả.

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
- **Commit:** dữ liệu tuần → `weekly: {năm}-W{tuần} — {N} văn bản mới`; sửa script → `fix(crawler): ...` kèm lý do.
- Cả 2 nguồn fail → ghi `data/run-log.md`, commit run-log, DỪNG (không build, không xoá gì).

## Môi trường

- Custom cloud environment cần allowlist: `vanban.chinhphu.vn`, `congbao.chinhphu.vn`, `*.chinhphu.vn`, `vbpl.vn`.
- Setup: `pip install requests beautifulsoup4 jinja2 markdown`.
- GitHub Pages: branch `main`, thư mục `/docs`.
