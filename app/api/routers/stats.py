from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from app.config import settings
import os

router = APIRouter()

security = HTTPBasic(auto_error=False)

def verify_credentials(
    credentials: HTTPBasicCredentials | None = Depends(security),
    u: str | None = None,
    p: str | None = None
):
    # Check query params first (for Telegram WebApp convenience)
    if u == "admin" and p == settings.DASHBOARD_PASSWORD:
        return "admin"
        
    # Standard Basic Auth fallback
    if credentials:
        correct_username = secrets.compare_digest(credentials.username, "admin")
        correct_password = secrets.compare_digest(credentials.password, settings.DASHBOARD_PASSWORD)
        if correct_username and correct_password:
            return credentials.username

    # Not authenticated: raise 401 with challenge
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": 'Basic realm="Sales Dashboard"'},
    )

def get_container():
    # Helper backward compat if needed, but not used now
    pass

@router.get("/api/stats")
async def get_stats(
    request: Request,
    period: str = "week", 
    user: str = Depends(verify_credentials)
):
    from app.services.transaction_service import TransactionService
    transaction_service: TransactionService = request.app.state.container.get("transaction_service")
    transactions = await transaction_service.get_admin_statistics(period)
    
    total_sales = len(transactions)
    total_revenue = sum(t.total_price for t in transactions)
    total_items = sum(t.amount for t in transactions)
    
    # Calculate revenue per product for pie chart
    from collections import defaultdict
    product_stats = defaultdict(lambda: {"count": 0, "revenue": 0})
    staff_stats = defaultdict(lambda: {"count": 0, "revenue": 0})
    
    for t in transactions:
        p_name = t.product.name if t.product else "O'chirilgan mahsulot"
        product_stats[p_name]["count"] += t.amount
        product_stats[p_name]["revenue"] += t.total_price
        
        u_name = t.user.username or f"ID:{t.user.tg_id}" if t.user else "Tizim"
        staff_stats[u_name]["count"] += t.amount
        staff_stats[u_name]["revenue"] += t.total_price
        
    return {
        "period": period,
        "total_transactions": total_sales,
        "total_revenue": total_revenue,
        "total_items": total_items,
        "products_breakdown": product_stats,
        "staff_breakdown": staff_stats
    }

@router.get("/api/inventory")
async def get_inventory(
    request: Request,
    user: str = Depends(verify_credentials)
):
    from app.services.product_service import ProductService
    product_service: ProductService = request.app.state.container.get("product_service")
    
    # We need products to be eager loaded with category or we fetch them manually.
    # ProductService.get_all_products() does not eager load `category`. Let's just return what we have and maybe map category.
    # To be safe and clean, let's fetch products and categories
    products = await product_service.get_all_products()
    from app.services.category_service import CategoryService
    category_service: CategoryService = request.app.state.container.get("category_service")
    categories = await category_service.get_all_categories()
    
    cat_map = {c.id: c.name for c in categories}
    
    inventory_data = []
    for p in products:
        inventory_data.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "quantity": p.quantity,
            "category": cat_map.get(p.category_id, "Kategoriyasiz")
        })
        
    return {"inventory": inventory_data}

@router.get("/", response_class=HTMLResponse)
async def dashboard_view(
    user: str = Depends(verify_credentials)
):
    import os
    file_path = os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
