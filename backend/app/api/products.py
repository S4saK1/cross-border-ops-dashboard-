"""
产品管理API模块

提供产品的CRUD操作，包括：
- 产品列表查询和搜索
- 产品创建、更新、删除
- 产品分类和标签管理
- 产品一致性状态管理
"""
import math
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.product import Product
from app.core.audit import write_audit_log
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, ProductListResponse
from app.core.deps import require_viewer, require_editor, require_admin

router = APIRouter()

# ── Constants (F-62) ──
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
DEFAULT_PAGE: int = 1
logger = logging.getLogger(__name__)



@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    search: str = Query(None),
    category: str = Query(None),
    consistency_status: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_viewer),
):
    """
    获取产品列表
    
    支持分页、搜索和筛选功能
    """
    q = db.query(Product).filter(Product.is_deleted == False)
    if search:
        q = q.filter(
            or_(
                Product.product_name_zh.contains(search),
                Product.product_name_en.contains(search),
                Product.sku.contains(search),
            )
        )
    if category:
        q = q.filter(Product.category == category)
    if consistency_status:
        q = q.filter(Product.consistency_status == consistency_status)
    total = q.count()
    items = q.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ProductListResponse(
        items=[ProductOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    data: ProductCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor),
):
    existing = db.query(Product).filter(Product.sku == data.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")
    product = Product(**data.model_dump(), created_by=current_user.id)
    db.add(product)
    db.commit()
    db.refresh(product)
    logger.info(f"Product created: {product.sku} by user {current_user.id}")
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="create",
        subject_type="product",
        subject_id=product.id,
        after={"sku": product.sku},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return product


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_viewer),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_deleted == False).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    data: ProductUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_deleted == False).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    changed_fields = [k for k, v in data.model_dump(exclude_unset=True).items()
                      if getattr(product, k) != v]
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    product.updated_at = datetime.utcnow()
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="update",
        subject_type="product",
        subject_id=product.id,
        after={"changed_fields": changed_fields},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_deleted == False).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_deleted = True
    product.deleted_at = datetime.utcnow()
    write_audit_log(
        db=db,
        actor_id=current_user.id,
        action="delete",
        subject_type="product",
        subject_id=product.id,
        after={"sku": product.sku},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"message": "Product deleted"}