from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent import Agent
from app.models.provider import Provider
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    spent_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.status.in_(
                [TransactionStatus.PAYMENT_VERIFIED, TransactionStatus.SERVICE_COMPLETED]
            ),
            Transaction.created_at >= start_of_day,
        )
    )
    today_spending = Decimal(spent_result.scalar_one())

    successful_result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.status.in_(
                [TransactionStatus.PAYMENT_VERIFIED, TransactionStatus.SERVICE_COMPLETED]
            ),
            Transaction.created_at >= start_of_day,
        )
    )
    successful_today = successful_result.scalar_one()

    blocked_result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.status == TransactionStatus.POLICY_BLOCKED,
            Transaction.created_at >= start_of_day,
        )
    )
    blocked_today = blocked_result.scalar_one()

    avg_result = await db.execute(
        select(func.coalesce(func.avg(Transaction.amount), 0)).where(
            Transaction.status.in_(
                [TransactionStatus.PAYMENT_VERIFIED, TransactionStatus.SERVICE_COMPLETED]
            )
        )
    )
    average_transaction_value = Decimal(avg_result.scalar_one())

    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar_one()
    total_providers = (await db.execute(select(func.count(Provider.id)))).scalar_one()

    return DashboardStats(
        wallet_balance_placeholder="N/A - AgentVault does not custody funds",
        today_spending=today_spending,
        successful_payments_today=successful_today,
        blocked_payments_today=blocked_today,
        average_transaction_value=average_transaction_value,
        total_agents=total_agents,
        total_providers=total_providers,
    )
