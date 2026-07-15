# Routine prompt — cập nhật định kỳ 2 ngày/lần

> **Cách dùng:** routine đã được tạo tự động (xem `data/run-log.md` lần chạy đầu). Nếu cần tạo lại
> bằng tay trên claude.ai/code: **schedule** mỗi 2 ngày, ~08:00 (Asia/Ho_Chi_Minh) — cron UTC `7 1 */2 * *`
> · **repo** Quang-Dobe/Agents-VietName-Legal-Docs · **environment** `vn-legal-docs`
> (network Custom + allowlist chinhphu.vn/vbpl.vn) · cho phép push nhánh làm việc + mở
> pull request (workflow `.github/workflows/automerge.yml` tự merge PR không phải draft)
> · prompt = khối dưới đây.
>
> Dữ liệu vẫn gom theo TUẦN ISO: mỗi run chỉ thêm văn bản mới vào file tuần tương ứng
> và cập nhật dần bản Điểm tin của tuần đó.

---

Bạn là orchestrator của dự án **vn-legal-docs-weekly**: crawl văn bản pháp luật Việt Nam
mới ban hành, tóm tắt dễ hiểu, build static site. Hôm nay chạy cập nhật định kỳ (2 ngày/lần).

ĐỌC TRƯỚC KHI LÀM: `CLAUDE.md` (schema, taxonomy, văn phong tóm tắt, quy tắc crawl,
ghi chú cấu trúc trang nguồn) và `data/index.json`.

## Các bước

0. **Xác định phạm vi.** Tính tuần ISO hiện tại. Khoảng ngày crawl = từ (ngày ban hành mới
   nhất có trong index − 1 ngày) đến hôm nay — bình thường 2–3 ngày; tối đa 14 ngày nếu
   các run trước bị lỡ. Nếu CLAUDE.md vẫn còn ghi "Run 0 recon chưa chạy": thực hiện Run 0
   trong `BACKFILL_PROMPTS.md` trước, rồi mới tiếp tục các bước dưới.
1. **Crawl song song.** Spawn 2 subagent `crawler-chinhphu` và `crawler-congbao` với khoảng
   ngày trên, mỗi agent ghi ra một file tạm riêng.
   - Một nguồn fail → ghi nhận vào run-log, tiếp tục với nguồn còn lại.
   - CẢ HAI fail → ghi `data/run-log.md`, commit riêng run-log, mở PR thường (xem bước 9),
     **DỪNG HẲN** (không build site, không sửa/xoá bất kỳ dữ liệu nào).
2. **Gộp + dedupe.** `python3 scripts/merge_dedupe.py <file1> <file2> --out <file_moi>`.
   Kết quả là danh sách văn bản MỚI (chưa có trong index).
   - Nếu RỖNG: thêm dòng run-log "không có văn bản mới", commit run-log, mở PR thường
     (xem bước 9), KẾT THÚC (bỏ qua các bước dưới — không cần build lại site).
3. **Tóm tắt.** Spawn subagent `summarizer` với file văn bản mới. Summarizer phải điền đủ:
   `tom_tat_ai`, `linh_vuc`, `trang_thai`, `ngay_hieu_luc` (nếu tìm được), `sua_doi_thay_the`.
   Sau đó summarizer VIẾT LẠI `data/weekly-digest/{năm}-week-{tuần}.md` của tuần hiện tại
   sao cho bao phủ TOÀN BỘ văn bản của tuần tính đến hôm nay (digest lớn dần trong tuần).
4. **Ghi dữ liệu.** Thêm văn bản mới vào `data/{năm}/week-{tuần}.json` theo tuần ISO của
   `ngay_ban_hanh` từng văn bản (tạo file nếu chưa có, giữ sort `ngay_ban_hanh` giảm dần),
   cập nhật `data/index.json`. KHÔNG đụng dữ liệu cũ ngoài việc bước 5 cập nhật trạng thái.
5. **Cập nhật trạng thái.** `python3 scripts/update_status.py <file_moi>`.
6. **Validate.** `python3 scripts/validate_data.py` — nếu fail, sửa dữ liệu cho đúng schema
   rồi chạy lại đến khi OK. Tuyệt đối không commit dữ liệu không hợp lệ.
7. **Build site.** Spawn subagent `site-builder` (validate lại + `python3 scripts/build_site.py`
   + kiểm tra sanity output). Site deploy tự động qua GitHub Actions khi push main —
   không cần làm gì thêm.
8. **Run log.** Thêm 1 dòng vào bảng trong `data/run-log.md`: ngày giờ UTC, loại run
   (`update`), nguồn ok/fail, số văn bản mới, tổng số request đã dùng, ghi chú.
9. **Commit + mở PR.** `git fetch origin main`, tạo nhánh làm việc mới từ `origin/main`
   (vd. `routine/update-{YYYY-MM-DD}`), commit toàn bộ thay đổi với message
   `update: {YYYY-MM-DD} — {N} văn bản mới`, push nhánh đó lên origin
   (retry tối đa 4 lần, backoff 2s/4s/8s/16s nếu lỗi mạng). Sau đó mở **pull request thường
   (KHÔNG phải draft)** vào `main` với tiêu đề trùng message commit.
   - Workflow `.github/workflows/automerge.yml` sẽ tự động merge PR không phải draft vào
     `main` rồi dispatch deploy GitHub Pages — KHÔNG cần merge tay hay push thẳng lên `main`.

## Nguyên tắc bắt buộc

- **Self-healing:** script fail mà bạn parse tay thành công → PHẢI sửa script cho chạy được
  + cập nhật "Ghi chú cấu trúc trang" trong CLAUDE.md, commit cùng lần (`fix(crawler): ...`).
- **An toàn dữ liệu:** không bao giờ xoá/ghi đè dữ liệu tuần cũ; chỉ thêm văn bản mới và
  cập nhật `trang_thai`/`bi_sua_doi_boi` qua script.
- **Rate limit:** 3 giây/request, tối đa 150 request/run, chỉ fetch domain trong allowlist.
- **Dữ liệu mẫu:** nếu `data/` còn văn bản `"nguon": "demo"` và run này crawl được dữ liệu
  thật đầu tiên → xoá sạch dữ liệu demo (file tuần + index + digest mẫu) trong cùng commit,
  ghi chú vào run-log.
- **Văn phong:** mọi nội dung hiển thị cho người đọc phải theo mục "Văn phong tóm tắt"
  trong CLAUDE.md — câu ngắn, từ thường, dễ hiểu.
