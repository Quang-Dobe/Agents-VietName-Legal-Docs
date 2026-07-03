#!/usr/bin/env python3
"""Render static site: data/ + site-src/ → docs/ (GitHub Pages).

Cách dùng: python3 scripts/build_site.py
Luôn build lại toàn bộ docs/. Không sửa tay file trong docs/.
"""
import json
import re
import shutil

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import DIGEST_DIR, DOCS_DIR, SITE_SRC, iter_week_files, week_key_from_path, week_label

LOAI_SLUG = {
    "Luật": "luat", "Nghị định": "nghi-dinh", "Thông tư": "thong-tu",
    "Thông tư liên tịch": "thong-tu", "Quyết định": "quyet-dinh",
    "Nghị quyết": "nghi-quyet", "Pháp lệnh": "khac", "Lệnh": "khac",
    "Văn bản hợp nhất": "khac",
}
TRANG_THAI_LABEL = {
    "chua_hieu_luc": "Chưa hiệu lực",
    "con_hieu_luc": "Đang hiệu lực",
    "het_hieu_luc_mot_phan": "Hết hiệu lực một phần",
    "het_hieu_luc": "Hết hiệu lực",
}
DIGEST_NAME_RE = re.compile(r"^(\d{4})-week-(\d+)$")


def fmt_date(iso):
    if not iso:
        return None
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def enrich(doc):
    doc = dict(doc)
    doc["loai_slug"] = LOAI_SLUG.get(doc.get("loai"), "khac")
    doc["ngay_ban_hanh_fmt"] = fmt_date(doc.get("ngay_ban_hanh"))
    doc["ngay_hieu_luc_fmt"] = fmt_date(doc.get("ngay_hieu_luc")) or "chưa rõ"
    doc["trang_thai_label"] = TRANG_THAI_LABEL.get(doc.get("trang_thai"), doc.get("trang_thai"))
    doc["search_text"] = " ".join(
        str(doc.get(k) or "") for k in ("so_hieu", "trich_yeu", "tom_tat_ai", "co_quan", "linh_vuc")
    ).lower()
    return doc


def filter_options(docs):
    return {
        "loai": sorted({d["loai"] for d in docs if d.get("loai")}),
        "co_quan": sorted({d["co_quan"] for d in docs if d.get("co_quan")}),
        "linh_vuc": sorted({d["linh_vuc"] for d in docs if d.get("linh_vuc")}),
    }


def load_weeks():
    weeks = []
    for path, payload in iter_week_files():
        key = week_key_from_path(path)
        docs = [enrich(d) for d in payload.get("documents", [])]
        weeks.append({
            "key": key,
            "label": week_label(key),
            "year": key.split("/")[0],
            "documents": docs,
            "count": len(docs),
        })
    return weeks


def load_digests():
    digests = {}
    md = markdown.Markdown(extensions=["extra"])
    for path in sorted(DIGEST_DIR.glob("*.md"), reverse=True):
        m = DIGEST_NAME_RE.match(path.stem)
        if not m:
            continue
        label = f"{m.group(1)}-W{int(m.group(2)):02d}"
        digests[label] = md.reset().convert(path.read_text(encoding="utf-8"))
    return digests


def main():
    weeks = load_weeks()
    digests = load_digests()
    latest = weeks[0] if weeks else None
    demo_mode = any(d.get("nguon") == "demo" for w in weeks for d in w["documents"])

    env = Environment(
        loader=FileSystemLoader(SITE_SRC / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    common_ctx = {
        "demo_mode": demo_mode,
        "latest_week": latest["label"] if latest else None,
        "has_digest_latest": bool(latest and latest["label"] in digests),
    }

    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)
    (DOCS_DIR / ".nojekyll").write_text("")
    shutil.copytree(SITE_SRC / "assets", DOCS_DIR / "assets")

    def render(template, out_path, root, **ctx):
        html = env.get_template(template).render(root=root, **common_ctx, **ctx)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")

    n_pages = 0
    if latest:
        render("index.html", DOCS_DIR / "index.html", "",
               week=latest, filters=filter_options(latest["documents"]))
        n_pages += 1
    for week in weeks:
        render("tuan.html", DOCS_DIR / "tuan" / f"{week['label']}.html", "../",
               week=week, filters=filter_options(week["documents"]),
               digest_available=week["label"] in digests)
        n_pages += 1
    for label, content in digests.items():
        render("diem-tin.html", DOCS_DIR / "diem-tin" / f"{label}.html", "../",
               label=label, content=content, all_digests=list(digests))
        n_pages += 1
    years = {}
    for week in weeks:
        years.setdefault(week["year"], []).append(
            {**week, "digest_available": week["label"] in digests})
    render("luu-tru.html", DOCS_DIR / "luu-tru.html", "", years=years)
    n_pages += 1

    all_docs = [
        {k: d.get(k) for k in ("so_hieu", "loai", "co_quan", "ngay_ban_hanh",
                               "trich_yeu", "linh_vuc", "trang_thai")} | {"tuan": w["label"]}
        for w in weeks for d in w["documents"]
    ]
    (DOCS_DIR / "data").mkdir()
    (DOCS_DIR / "data" / "all.json").write_text(
        json.dumps(all_docs, ensure_ascii=False), encoding="utf-8")

    print(f"OK: {n_pages} trang, {len(all_docs)} văn bản → docs/")


if __name__ == "__main__":
    main()
