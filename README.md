# Văn Bản Mới — vn-legal-docs-weekly

Điểm tin pháp luật Việt Nam, mỗi tuần một bản. Crawl văn bản mới ban hành từ nguồn công khai
của Chính phủ, tóm tắt ngắn gọn bằng AI (chạy trong Claude Code Routine), xuất static site
lên GitHub Pages.

- **Site:** GitHub Pages, deploy tự động qua Actions (`.github/workflows/deploy-pages.yml`) khi push `main`
- **Kế hoạch chi tiết:** [`PLAN.md`](PLAN.md)
- **Quy tắc dữ liệu + vận hành cho agent:** [`CLAUDE.md`](CLAUDE.md)
- **Prompt routine hàng tuần:** [`ROUTINE_PROMPT.md`](ROUTINE_PROMPT.md)
- **Backfill + recon:** [`BACKFILL_PROMPTS.md`](BACKFILL_PROMPTS.md)

## Build site tại chỗ

```bash
pip install requests beautifulsoup4 jinja2 markdown
python3 scripts/validate_data.py
python3 scripts/build_site.py
# mở docs/index.html
```

## Trạng thái

Repo đang ở giai đoạn scaffold: dữ liệu trong `data/` là **dữ liệu mẫu** (nguồn `demo`)
để xem giao diện. Chưa chạy Run 0 recon — xem `BACKFILL_PROMPTS.md`.
