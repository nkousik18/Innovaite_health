"""
Food Inventory API Routes
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.base import get_db
from models.inventory import FoodInventory, FoodCategory, WarehouseStock, ConsumptionPattern
from schemas.inventory import (
    FoodCategoryCreate, FoodCategoryResponse,
    InventoryCreate, InventoryUpdate, InventoryResponse,
    WarehouseStockCreate, WarehouseStockUpdate, WarehouseStockResponse,
    ConsumptionPatternCreate, ConsumptionPatternResponse,
    InventorySummary, InventoryByCategory
)
from schemas.common import PaginatedResponse

router = APIRouter()


# ==================== Food Categories ====================

@router.post("/categories", response_model=FoodCategoryResponse)
async def create_category(
    data: FoodCategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new food category."""
    category = FoodCategory(**data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.get("/categories", response_model=List[FoodCategoryResponse])
async def list_categories(
    is_active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all food categories."""
    result = await db.execute(
        select(FoodCategory).where(FoodCategory.is_active == is_active)
    )
    return list(result.scalars().all())


@router.get("/categories/{category_id}", response_model=FoodCategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific food category."""
    result = await db.execute(
        select(FoodCategory).where(FoodCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# ==================== Food Inventory ====================

@router.post("/", response_model=InventoryResponse)
async def record_inventory(
    data: InventoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record food inventory level."""
    inventory_data = data.model_dump()
    inventory_data["recorded_at"] = datetime.utcnow()

    # Calculate days of supply
    if data.quantity_tonnes and data.consumption_rate_tonnes_per_day:
        inventory_data["days_of_supply"] = (
            data.quantity_tonnes / data.consumption_rate_tonnes_per_day
        )

        # Determine stock status
        days = inventory_data["days_of_supply"]
        if days < 7:
            inventory_data["stock_status"] = "critical"
        elif days < 15:
            inventory_data["stock_status"] = "low"
        elif days < 30:
            inventory_data["stock_status"] = "adequate"
        else:
            inventory_data["stock_status"] = "surplus"

    inventory = FoodInventory(**inventory_data)
    db.add(inventory)
    await db.flush()
    await db.refresh(inventory)
    return inventory


@router.get("/region/{region_id}", response_model=List[InventoryResponse])
async def get_region_inventory(
    region_id: int,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get current inventory for a region."""
    query = select(FoodInventory).where(
        FoodInventory.region_id == region_id
    )

    if category_id:
        query = query.where(FoodInventory.category_id == category_id)

    query = query.order_by(FoodInventory.recorded_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/region/{region_id}/summary", response_model=InventorySummary)
async def get_inventory_summary(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get inventory summary for a region."""
    # Get latest inventory per category
    result = await db.execute(
        select(FoodInventory)
        .where(FoodInventory.region_id == region_id)
        .order_by(FoodInventory.recorded_at.desc())
    )
    inventories = result.scalars().all()

    # Group by category (keep latest)
    by_category = {}
    for inv in inventories:
        if inv.category_id not in by_category:
            by_category[inv.category_id] = inv

    total_tonnes = sum(inv.quantity_tonnes for inv in by_category.values())
    avg_days = (
        sum(inv.days_of_supply or 0 for inv in by_category.values()) / len(by_category)
        if by_category else 0
    )

    critical_count = sum(
        1 for inv in by_category.values()
        if inv.stock_status == "critical"
    )
    low_count = sum(
        1 for inv in by_category.values()
        if inv.stock_status == "low"
    )

    # Determine overall status
    if critical_count > 0:
        status = "critical"
    elif low_count > 0:
        status = "low"
    elif avg_days < 30:
        status = "adequate"
    else:
        status = "surplus"

    return InventorySummary(
        region_id=region_id,
        region_name=f"Region {region_id}",
        total_inventory_tonnes=total_tonnes,
        days_of_supply=avg_days,
        stock_status=status,
        categories_critical=critical_count,
        categories_low=low_count
    )


@router.patch("/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an inventory record."""
    result = await db.execute(
        select(FoodInventory).where(FoodInventory.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory record not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory, field, value)

    await db.flush()
    await db.refresh(inventory)
    return inventory


# ==================== Warehouse Stocks ====================

@router.post("/warehouse-stocks", response_model=WarehouseStockResponse)
async def record_warehouse_stock(
    data: WarehouseStockCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record warehouse stock level."""
    stock_data = data.model_dump()
    stock_data["recorded_at"] = datetime.utcnow()

    stock = WarehouseStock(**stock_data)
    db.add(stock)
    await db.flush()
    await db.refresh(stock)
    return stock


@router.get("/warehouse-stocks/{center_id}", response_model=List[WarehouseStockResponse])
async def get_warehouse_stocks(
    center_id: int,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get stock levels for a distribution center."""
    query = select(WarehouseStock).where(
        WarehouseStock.distribution_center_id == center_id
    )

    if category_id:
        query = query.where(WarehouseStock.category_id == category_id)

    query = query.order_by(WarehouseStock.recorded_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.patch("/warehouse-stocks/{stock_id}", response_model=WarehouseStockResponse)
async def update_warehouse_stock(
    stock_id: int,
    data: WarehouseStockUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update warehouse stock record."""
    result = await db.execute(
        select(WarehouseStock).where(WarehouseStock.id == stock_id)
    )
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock record not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stock, field, value)

    await db.flush()
    await db.refresh(stock)
    return stock


# ==================== Consumption Patterns ====================

@router.post("/consumption", response_model=ConsumptionPatternResponse)
async def record_consumption(
    data: ConsumptionPatternCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record consumption pattern data."""
    consumption = ConsumptionPattern(**data.model_dump())
    db.add(consumption)
    await db.flush()
    await db.refresh(consumption)
    return consumption


@router.get("/consumption/{region_id}", response_model=List[ConsumptionPatternResponse])
async def get_consumption_patterns(
    region_id: int,
    category_id: Optional[int] = None,
    period_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get consumption patterns for a region."""
    query = select(ConsumptionPattern).where(
        ConsumptionPattern.region_id == region_id
    )

    if category_id:
        query = query.where(ConsumptionPattern.category_id == category_id)
    if period_type:
        query = query.where(ConsumptionPattern.period_type == period_type)

    query = query.order_by(ConsumptionPattern.period_start.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/consumption/{region_id}/anomalies")
async def get_consumption_anomalies(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detected consumption anomalies for a region."""
    result = await db.execute(
        select(ConsumptionPattern)
        .where(
            ConsumptionPattern.region_id == region_id,
            ConsumptionPattern.anomaly_detected == True
        )
        .order_by(ConsumptionPattern.period_start.desc())
    )
    anomalies = result.scalars().all()

    return {
        "region_id": region_id,
        "anomalies_count": len(anomalies),
        "anomalies": [
            {
                "category_id": a.category_id,
                "period_start": a.period_start,
                "period_end": a.period_end,
                "anomaly_score": a.anomaly_score,
                "deviation_percentage": a.deviation_percentage
            }
            for a in anomalies
        ]
    }
