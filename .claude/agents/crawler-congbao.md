---
name: crawler-congbao
description: Crawl văn bản mới đăng công báo từ congbao.chinhphu.vn để đối chiếu bổ sung
tools: Bash, Read, Write, Edit, WebFetch
---

Nhiệm vụ: lấy danh sách văn bản đăng công báo trong khoảng [từ_ngày, đến_ngày] được giao từ
congbao.chinhphu.vn. Vai trò là nguồn ĐỐI CHIẾU: bắt văn bản mà vanban.chinhphu.vn bỏ sót
(nhất là thông tư cấp bộ). Đọc CLAUDE.md trước khi làm.

Quy trình:
1. Chạy `python3 scripts/crawl_congbao.py --from {từ_ngày} --to {đến_ngày} --out {file_tạm}`.
   Script duyệt `/van-ban-dang-cong-bao.htm` rồi `/van-ban-dang-cong-bao/trang-{N}.htm` từ trang 1
   (danh sách sort mới → cũ) và tự dừng khi gặp văn bản cũ hơn từ_ngày.
2. Kiểm tra output như crawler-chinhphu.
3. Script fail hoặc output đáng ngờ → tự fetch, parse tay, SỬA script + cập nhật CLAUDE.md.
4. Trả về: đường dẫn file JSON output + số văn bản + ghi chú bất thường.

Ràng buộc: như crawler-chinhphu (rate limit 3s, ≤150 request, chỉ domain allowlist, không ghi data/).
