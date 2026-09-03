"""
Coupon Sentinel - Analytics Routes (Milestone 5)

GET /api/analytics/savings aggregates OptimizedPlanRecord rows — populated
when an authenticated user calls POST /api/optimize (see backend/app.py).
Real numbers from real persisted rows, not a mock.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.db_models import OptimizedPlanRecord, User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/savings")
async def get_savings_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Total and average savings across all of this user's past optimizations."""
    optimization_count, total_savings = (
        db.query(
            func.count(OptimizedPlanRecord.id),
            func.coalesce(func.sum(OptimizedPlanRecord.total_savings), 0),
        )
        .filter(OptimizedPlanRecord.user_id == user.id)
        .one()
    )
    total_savings = float(total_savings)
    average_savings = total_savings / optimization_count if optimization_count else 0.0

    return {
        "optimization_count": optimization_count,
        "total_savings": round(total_savings, 2),
        "average_savings_per_optimization": round(average_savings, 2),
    }
