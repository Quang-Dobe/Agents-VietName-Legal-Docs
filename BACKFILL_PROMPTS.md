# Backfill — chuỗi one-off routines (chạy 1 lần, theo thứ tự, cách nhau ≥ 2 giờ)

Phạm vi: 04/05/2026 → hiện tại. 3 run, mỗi run ~3 tuần. Checkpoint: `data/backfill-progress.json`
dạng `{"weeks": {"2026-W19": "done", ...}}` — commit sau MỖI tuần xử lý xong để run sau resume được.

> Chạy TRƯỚC backfill: **Run 0 — Recon** (bên dưới). Không chạy B1–B3 khi CLAUDE.md còn ghi
> "Run 0 recon chưa chạy".

---

## Run 0 — Recon (one-off, chạy đầu tiên trong custom environment)

Bạn đang chuẩn bị hạ tầng crawl cho vn-legal-docs-weekly. Đọc CLAUDE.md trước.

1. Fetch `https://vanban.chinhphu.vn/robots.txt` và `https://congbao.chinhphu.vn/robots.txt`.
   Ghi kết luận (path nào bị cấm, crawl-delay nếu có) vào mục "Ghi chú cấu trúc trang" của CLAUDE.md.
2. Fetch trang danh sách vanban.chinhphu.vn (`/he-thong-van-ban?classid=1&mode=1`), tìm cách lọc
   theo khoảng ngày ban hành (thử form tìm kiếm nâng cao, quan sát query params). Fetch 1 trang
   chi tiết văn bản. Ghi lại: URL pattern + params + CSS selectors của mọi trường trong schema.
3. Làm tương tự với congbao.chinhphu.vn (`/van-ban-dang-cong-bao.htm` + `/van-ban-dang-cong-bao/trang-2.htm`).
4. Sửa `scripts/crawl_vanban.py` và `scripts/crawl_congbao.py` theo selectors thật.
   Chạy thử mỗi script với khoảng ngày 7 ngày gần nhất; lặp sửa đến khi output qua được
   `scripts/validate_data.py` (bỏ qua 2 trường tom_tat_ai/linh_vuc ở bước này bằng flag `--partial`).
5. Xoá dòng "TODO — Run 0 recon chưa chạy" trong CLAUDE.md, điền ghi chú thật.
6. Commit `recon: chốt selectors + robots.txt cho 2 nguồn` và push lên main.
   KHÔNG ghi dữ liệu vào data/ ở run này.

---

## Run B1 — tuần 2026-W19 → W21 (04/05 – 24/05)

Bạn là orchestrator backfill của vn-legal-docs-weekly. Đọc CLAUDE.md và data/backfill-progress.json.
Xử lý các tuần ISO 2026-W19, W20, W21 — bỏ qua tuần đã "done" trong checkpoint.

Với TỪNG tuần (tuần cũ trước):
1. Spawn song song crawler-chinhphu + crawler-congbao với khoảng ngày của tuần đó.
2. `python3 scripts/merge_dedupe.py ... --out ...` để lấy văn bản mới (dedupe với index).
3. Spawn summarizer cho danh sách đó (tóm tắt làm ngay trong run này).
4. `python3 scripts/update_status.py ...`, ghi file tuần + index, `python3 scripts/validate_data.py`.
5. Cập nhật checkpoint tuần đó = "done", commit `backfill: 2026-W{tuần} — {N} văn bản`, push.

KHÔNG build site ở run này (site build 1 lần ở Run B3). Rate limit theo CLAUDE.md.
Nếu một tuần fail hẳn cả 2 nguồn: đánh dấu checkpoint "failed", ghi run-log, sang tuần kế tiếp.

## Run B2 — tuần 2026-W22 → W24 (25/05 – 14/06)

(Nguyên văn Run B1, thay danh sách tuần: 2026-W22, W23, W24.)

## Run B3 — tuần 2026-W25 → tuần hiện tại (15/06 → nay)

(Nguyên văn Run B1, thay danh sách tuần: 2026-W25 đến tuần hiện tại.) Sau khi xong các tuần:
1. Kiểm tra `data/index.json` không trùng so_hieu, chạy `python3 scripts/validate_data.py` toàn bộ.
2. XOÁ toàn bộ dữ liệu mẫu (documents có `"nguon": "demo"` + digest mẫu) nếu còn.
3. Spawn site-builder để build site đầy đủ.
4. Đánh dấu checkpoint `"backfill_complete": true`, commit `initial backfill complete`, push.
