from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
import os

router = APIRouter()

def get_container(request: Request):
    return request.app.state.container

@router.get("/api/stats")
async def get_stats(period: str = "week", container = Depends(get_container)):
    from app.services.transaction_service import TransactionService
    transaction_service: TransactionService = container.get("transaction_service")
    transactions = await transaction_service.get_admin_statistics(period)
    
    total_sales = len(transactions)
    total_revenue = sum(t.total_price for t in transactions)
    total_items = sum(t.amount for t in transactions)
    
    # Calculate revenue per product for pie chart
    from collections import defaultdict
    product_stats = defaultdict(lambda: {"count": 0, "revenue": 0})
    staff_stats = defaultdict(lambda: {"count": 0, "revenue": 0})
    
    for t in transactions:
        p_name = t.product.name if t.product else "Удаленный товар"
        product_stats[p_name]["count"] += t.amount
        product_stats[p_name]["revenue"] += t.total_price
        
        u_name = t.user.username or f"ID:{t.user.tg_id}" if t.user else "Tizim"
        staff_stats[u_name]["count"] += 1
        staff_stats[u_name]["revenue"] += t.total_price
        
    return {
        "period": period,
        "total_transactions": total_sales,
        "total_revenue": total_revenue,
        "total_items": total_items,
        "products_breakdown": product_stats,
        "staff_breakdown": staff_stats
    }

@router.get("/", response_class=HTMLResponse)
async def dashboard_view():
    import os
    file_path = os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
