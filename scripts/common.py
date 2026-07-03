"""Hằng số schema + helper dùng chung cho các script của vn-legal-docs-weekly."""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
INDEX_PATH = DATA_DIR / "index.json"
DIGEST_DIR = DATA_DIR / "weekly-digest"
DOCS_DIR = REPO_ROOT / "docs"
SITE_SRC = REPO_ROOT / "site-src"

USER_AGENT = "vn-legal-docs-weekly/1.0 (+https://github.com/Quang-Dobe/Agents-VietName-Legal-Docs)"
RATE_LIMIT_S = 3
MAX_REQUESTS = 150

LOAI_HOP_LE = [
    "Luật", "Nghị quyết", "Nghị định", "Quyết định", "Thông tư",
    "Thông tư liên tịch", "Pháp lệnh", "Lệnh", "Văn bản hợp nhất",
]

TAXONOMY = [
    "Thuế - Phí - Lệ phí", "Đất đai - Nhà ở", "Lao động - Tiền lương", "Bảo hiểm",
    "Doanh nghiệp - Đầu tư", "Tài chính - Ngân hàng", "Xây dựng - Đô thị",
    "Giao thông - Vận tải", "Y tế", "Giáo dục", "Khoa học - Công nghệ số",
    "Tài nguyên - Môi trường", "Quốc phòng - An ninh", "Hành chính - Tổ chức",
    "Tư pháp - Xử phạt", "Khác",
]

TRANG_THAI_HOP_LE = ["chua_hieu_luc", "con_hieu_luc", "het_hieu_luc_mot_phan", "het_hieu_luc"]

NGUON_HOP_LE = ["vanban.chinhphu.vn", "congbao.chinhphu.vn", "vbpl.vn", "demo"]

ALLOWED_LINK_DOMAINS = ("chinhphu.vn", "vbpl.vn")

# vd: 15/2026/ND-CP, 68/2026/QH15, 03/2026/TT-BTC, 1234/QD-TTg
SO_HIEU_RE = re.compile(r"^[\w.-]+/((\d{4}/)?[\w-]+|[\w-]+/\d{4})$", re.UNICODE)

NGAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED_FIELDS = [
    "so_hieu", "loai", "co_quan", "ngay_ban_hanh", "ngay_hieu_luc", "trich_yeu",
    "linh_vuc", "link_goc", "tom_tat_ai", "trang_thai", "sua_doi_thay_the",
    "bi_sua_doi_boi", "nguon",
]


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


def iter_week_files():
    """Yield (path, dữ_liệu) cho mọi file data/<năm>/week-*.json, tuần mới nhất trước."""
    files = sorted(DATA_DIR.glob("2*/week-*.json"), reverse=True)
    for path in files:
        yield path, load_json(path)


def week_key_from_path(path):
    """data/2026/week-27.json → '2026/week-27' (định dạng dùng trong index.json)."""
    path = Path(path)
    return f"{path.parent.name}/{path.stem}"


def week_label(week_key):
    """'2026/week-27' → '2026-W27'."""
    year, week = week_key.split("/week-")
    return f"{year}-W{int(week):02d}"
