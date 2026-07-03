---
name: site-builder
description: Build static site từ data/ vào docs/
tools: Bash, Read, Write, Edit
---

Nhiệm vụ: build lại toàn bộ site.

1. Chạy `python3 scripts/validate_data.py` — DỪNG ngay nếu fail, báo lỗi về orchestrator.
2. Chạy `python3 scripts/build_site.py` — render toàn bộ `docs/` từ `data/` + `site-src/`.
3. Kiểm tra sanity:
   - `docs/index.html` tồn tại và chứa số hiệu văn bản mới nhất của tuần mới nhất.
   - Không còn chuỗi template chưa render (`{{` hoặc `{%`) trong bất kỳ file HTML nào.
   - Mọi trang HTML có `<link rel="icon"`.
   - `docs/assets/style.css`, `docs/assets/app.js`, fonts, logo, favicon đã được copy.
4. Nếu lỗi do template/asset: sửa trong `site-src/`, chạy lại build. KHÔNG sửa tay file trong `docs/`.

Trả về: OK/FAIL + số trang đã render + vấn đề gặp phải (nếu có).
