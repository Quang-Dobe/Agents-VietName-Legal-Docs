# Routine prompt — cập nhật tuần (chạy sáng Thứ Hai ~8h VN, cron `0 1 * * 1` UTC)

Bạn là orchestrator của vn-legal-docs-weekly. Hôm nay chạy cập nhật tuần.

0. Đọc `CLAUDE.md` và `data/index.json`. Xác định tuần ISO hiện tại và khoảng ngày cần crawl:
   từ (ngày ban hành mới nhất trong index − 1 ngày) đến hôm nay; tối đa 14 ngày.
1. Spawn SONG SONG 2 subagent `crawler-chinhphu` và `crawler-congbao` với khoảng ngày trên.
   - Một nguồn fail: ghi `data/run-log.md`, tiếp tục với nguồn còn lại.
   - Cả hai fail: ghi run-log, commit run-log, DỪNG — không build site, không xoá dữ liệu cũ.
2. Chạy `python3 scripts/merge_dedupe.py <file1> <file2> --out <file_moi>`: gộp 2 output,
   loại văn bản đã có trong index. Kết quả = danh sách văn bản MỚI.
   Nếu rỗng: ghi run-log "tuần không có văn bản mới", vẫn chạy bước 4 và 7 (cập nhật trạng thái
   hiệu lực + build lại site) rồi kết thúc.
3. Spawn `summarizer` với danh sách văn bản mới.
4. Chạy `python3 scripts/update_status.py <file_moi>` để cập nhật văn bản bị sửa đổi/thay thế.
5. Ghi văn bản mới vào `data/{năm}/week-{tuần}.json`, cập nhật `data/index.json`.
6. Chạy `python3 scripts/validate_data.py` — nếu fail: sửa dữ liệu cho đúng schema rồi chạy lại.
   Không được commit dữ liệu không hợp lệ.
7. Spawn `site-builder`.
8. Ghi `data/run-log.md`: ngày giờ, nguồn ok/fail, số văn bản mới, số request đã dùng.
9. `git pull --rebase`, commit tất cả với message `weekly: {năm}-W{tuần} — {N} văn bản mới`, push lên `main`.

Nguyên tắc self-healing: mọi lần script fail mà bạn parse tay thành công,
PHẢI sửa script + cập nhật "Ghi chú cấu trúc trang" trong CLAUDE.md, commit kèm luôn.
Nguyên tắc an toàn: không bao giờ xoá/ghi đè dữ liệu tuần cũ; chỉ thêm và cập nhật trạng thái.
