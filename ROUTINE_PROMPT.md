# Routine prompt — cập nhật tuần

> **Cách dùng:** copy toàn bộ phần trong khối dưới đây vào ô prompt khi tạo Routine trên claude.ai/code.
> Cấu hình routine: **schedule** weekly, Thứ Hai 08:00 (Asia/Ho_Chi_Minh) · **repo** Quang-Dobe/Agents-VietName-Legal-Docs
> · **environment** `vn-legal-docs` (network Custom + allowlist chinhphu.vn/vbpl.vn) · cho phép push branch `main`.

---

Bạn là orchestrator của dự án **vn-legal-docs-weekly**: crawl văn bản pháp luật Việt Nam
mới ban hành trong tuần, tóm tắt dễ hiểu, build static site. Hôm nay chạy cập nhật tuần.

ĐỌC TRƯỚC KHI LÀM: `CLAUDE.md` (schema, taxonomy, văn phong tóm tắt, quy tắc crawl,
ghi chú cấu trúc trang nguồn) và `data/index.json`.

## Các bước

0. **Xác định phạm vi.** Tính tuần ISO hiện tại. Khoảng ngày crawl = từ (ngày ban hành mới
   nhất có trong index − 1 ngày) đến hôm nay, nhưng không quá 14 ngày. Nếu CLAUDE.md vẫn còn
   ghi "Run 0 recon chưa chạy": thực hiện Run 0 trong `BACKFILL_PROMPTS.md` trước, rồi mới
   tiếp tục các bước dưới.
1. **Crawl song song.** Spawn 2 subagent `crawler-chinhphu` và `crawler-congbao` với khoảng
   ngày trên, mỗi agent ghi ra một file tạm riêng.
   - Một nguồn fail → ghi nhận vào run-log, tiếp tục với nguồn còn lại.
   - CẢ HAI fail → ghi `data/run-log.md`, commit riêng run-log, push, **DỪNG HẲN**
     (không build site, không sửa/xoá bất kỳ dữ liệu nào).
2. **Gộp + dedupe.** `python3 scripts/merge_dedupe.py <file1> <file2> --out <file_moi>`.
   Kết quả là danh sách văn bản MỚI (chưa có trong index). Nếu rỗng: ghi run-log
   "không có văn bản mới", vẫn làm bước 6–7 (cập nhật trạng thái hiệu lực + build) rồi kết thúc.
3. **Tóm tắt.** Spawn subagent `summarizer` với file văn bản mới. Summarizer phải điền đủ:
   `tom_tat_ai`, `linh_vuc`, `trang_thai`, `ngay_hieu_luc` (nếu tìm được), `sua_doi_thay_the`,
   và viết `data/weekly-digest/{năm}-week-{tuần}.md`.
4. **Ghi dữ liệu.** Thêm văn bản mới vào `data/{năm}/week-{tuần}.json` (tạo file nếu chưa có,
   sort `ngay_ban_hanh` giảm dần), cập nhật `data/index.json`. KHÔNG đụng dữ liệu tuần cũ
   ngoài việc bước 5 cập nhật trạng thái.
5. **Cập nhật trạng thái.** `python3 scripts/update_status.py <file_moi>`.
6. **Validate.** `python3 scripts/validate_data.py` — nếu fail, sửa dữ liệu cho đúng schema
   rồi chạy lại đến khi OK. Tuyệt đối không commit dữ liệu không hợp lệ.
7. **Build site.** Spawn subagent `site-builder` (validate lại + `python3 scripts/build_site.py`
   + kiểm tra sanity output). Site deploy tự động qua GitHub Actions khi push main —
   không cần làm gì thêm.
8. **Run log.** Thêm 1 dòng vào bảng trong `data/run-log.md`: ngày giờ UTC, loại run
   (`weekly`), nguồn ok/fail, số văn bản mới, tổng số request đã dùng, ghi chú.
9. **Commit + push.** `git pull --rebase origin main`, commit toàn bộ thay đổi với message
   `weekly: {năm}-W{tuần} — {N} văn bản mới`, push lên `main`
   (retry tối đa 4 lần, backoff 2s/4s/8s/16s nếu lỗi mạng).

## Nguyên tắc bắt buộc

- **Self-healing:** script fail mà bạn parse tay thành công → PHẢI sửa script cho chạy được
  + cập nhật "Ghi chú cấu trúc trang" trong CLAUDE.md, commit cùng lần (`fix(crawler): ...`).
- **An toàn dữ liệu:** không bao giờ xoá/ghi đè dữ liệu tuần cũ; chỉ thêm văn bản mới và
  cập nhật `trang_thai`/`bi_sua_doi_boi` qua script.
- **Rate limit:** 3 giây/request, tối đa 150 request/run, chỉ fetch domain trong allowlist.
- **Dữ liệu mẫu:** nếu `data/` còn văn bản `"nguon": "demo"` và tuần này crawl được dữ liệu
  thật đầu tiên → xoá sạch dữ liệu demo (file tuần + index + digest mẫu) trong cùng commit,
  ghi chú vào run-log.
- **Văn phong:** mọi nội dung hiển thị cho người đọc phải theo mục "Văn phong tóm tắt"
  trong CLAUDE.md — câu ngắn, từ thường, dễ hiểu.
