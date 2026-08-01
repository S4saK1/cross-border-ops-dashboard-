import csv
import io
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.product import Product
from app.core.deps import require_reviewer
from app.utils.csv_utils import sanitize_csv_cell
import json as _json
import os as _os
import csv as _csv
import io as _io

router = APIRouter()


class ExportRequest(BaseModel):
    platform: str
    product_ids: list[str]


@router.post("/csv")
def export_csv(  # noqa: C901
    req: ExportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_reviewer),
):
    platform = req.platform
    product_ids = req.product_ids
    if platform not in ("amazon", "alibaba"):
        raise HTTPException(status_code=400, detail="Platform must be 'amazon' or 'alibaba'")

    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.is_deleted.is_(False),
    ).all()

    # ── 导出一致性阻断（F-10） ──
    from app.core.consistency import ConsistencyEngine, get_consistency_status
    engine = ConsistencyEngine(db)
    all_issues = []
    # Batch check (single DB query for terms, avoids N+1)
    all_issues = engine.check_products_batch(products)
    # 跨产品一致性检查
    cross_issues = engine.check_all_products()
    all_issues.extend(cross_issues)

    if get_consistency_status(all_issues) == 'error':
        # HTTPException already imported at top of file
        error_details = [i for i in all_issues if i['severity'] == 'ERROR']
        raise HTTPException(
            status_code=409,
            detail={"message": "Export blocked due to consistency errors", "issues": error_details},
        )

    # ── 审计日志 ──
    from app.core.audit import write_audit_log
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action='export_csv',
        subject_type='product',
        subject_id=','.join(product_ids),
        after={"platform": platform, "product_count": len(products), "product_ids": product_ids},
    )
    db.commit()

    if not products:
        raise HTTPException(status_code=404, detail="No products found")

    # F-41: Load platform template
    _templates_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "data", "export_templates.json")
    try:
        with open(_templates_path, "r", encoding="utf-8-sig") as _tf:
            _templates = _json.load(_tf)
    except (FileNotFoundError, _json.JSONDecodeError):
        _templates = {}
    template = _templates.get(platform)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown platform or missing template: {platform}")

    headers = template["headers"]
    mapping = template["field_mapping"]

    # F-32: True streaming CSV
    def _generate_csv():
        yield "\ufeff"
        _buf = _io.StringIO()
        _w = _csv.writer(_buf)
        _w.writerow(headers)
        yield _buf.getvalue()
        _buf.seek(0)
        _buf.truncate()
        for p in products:
            row = []
            for col in mapping:
                if "static" in col:
                    row.append(sanitize_csv_cell(str(col["static"])))
                else:
                    val = getattr(p, col["field"], None)
                    if val is None:
                        val = col.get("default", "")
                    cell = sanitize_csv_cell(str(val))  # Always sanitize numeric/text fields
                    row.append(cell)
            _w.writerow(row)
            yield _buf.getvalue()
            _buf.seek(0)
            _buf.truncate()

    return StreamingResponse(
        _generate_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={platform}_export.csv"},
    )
