from langchain_core.tools import tool
from db import get_engine
from sqlalchemy import text
import requests
from typing import Any, List, Dict


def _rows_to_list(result) -> List[Dict[str, Any]]:
    try:
        return [dict(row) for row in result.mappings().all()]
    except Exception:
        return [dict(r) for r in result.fetchall()]


@tool
def get_overdue_customers(days: int, org_id: str) -> Any:
    """Get customers who haven't paid in X days for a specific organization."""
    engine = get_engine()
    sql = text(
        """
        SELECT c.name, SUM(i.amount) AS total_due
        FROM customers c
        JOIN invoices i ON c.id = i.customer_id
        WHERE c.organizationId = :org_id
        AND i.status = 'unpaid'
        AND i.due_date < NOW() - (:days || ' days')::interval
        GROUP BY c.name
        """
    )
    try:
        with engine.connect() as conn:
            res = conn.execute(sql, {"days": str(days), "org_id": org_id})
            rows = _rows_to_list(res)
        return rows if rows else "No overdue customers found."
    except Exception as e:
        return f"Error querying overdue customers: {e}"


@tool
def get_top_selling_products(limit: int = 5, org_id: str | None = None) -> Any:
    """Get top selling products by quantity, optionally limited to an organization."""
    engine = get_engine()
    if org_id:
        sql = text(
            """
            SELECT p.name, SUM(oi.quantity) AS total_sold
            FROM products p
            JOIN order_items oi ON p.id = oi.product_id
            WHERE p.organizationId = :org_id
            GROUP BY p.name
            ORDER BY total_sold DESC
            LIMIT :limit
            """
        )
        params = {"limit": limit, "org_id": org_id}
    else:
        sql = text(
            """
            SELECT p.name, SUM(oi.quantity) AS total_sold
            FROM products p
            JOIN order_items oi ON p.id = oi.product_id
            GROUP BY p.name
            ORDER BY total_sold DESC
            LIMIT :limit
            """
        )
        params = {"limit": limit}

    try:
        with engine.connect() as conn:
            res = conn.execute(sql, params)
            rows = _rows_to_list(res)
        return rows if rows else "No sales data found."
    except Exception as e:
        return f"Error querying top products: {e}"


@tool
def get_revenue_summary(period: str, org_id: str) -> Any:
    """Get revenue summary for a given period (e.g., 'last_month', 'last_quarter') scoped to an organization."""
    engine = get_engine()
    if period == "last_month":
        sql = text(
            """
            SELECT DATE_TRUNC('month', createdAt) as period, SUM(totalAmount) as revenue
            FROM orders
            WHERE organizationId = :org_id
            AND createdAt >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')
            GROUP BY period
            """
        )
    elif period == "last_quarter":
        sql = text(
            """
            SELECT DATE_TRUNC('quarter', createdAt) as period, SUM(totalAmount) as revenue
            FROM orders
            WHERE organizationId = :org_id
            AND createdAt >= DATE_TRUNC('quarter', NOW() - INTERVAL '1 quarter')
            GROUP BY period
            """
        )
    else:
        return "Invalid period specified. Use 'last_month' or 'last_quarter'."

    try:
        with engine.connect() as conn:
            res = conn.execute(sql, {"org_id": org_id})
            rows = _rows_to_list(res)
        return rows if rows else "No revenue data found."
    except Exception as e:
        return f"Error querying revenue summary: {e}"


@tool
def get_default_risk_customers(org_id: str) -> Any:
    """Compute customers in `org_id` with unpaid invoices older than 30 days.

    Returns a list of dicts: {id, name, total_due, unpaid_count, last_due_date} ordered by total_due desc.
    """
    engine = get_engine()
    sql = text(
        """
        SELECT c.id, c.name, SUM(i.amount) AS total_due,
               COUNT(i.*) AS unpaid_count, MAX(i.due_date) AS last_due_date
        FROM customers c
        JOIN invoices i ON c.id = i.customer_id
        WHERE c.organizationId = :org_id
          AND i.status = 'unpaid'
          AND i.due_date < NOW() - INTERVAL '30 days'
        GROUP BY c.id, c.name
        ORDER BY total_due DESC
        """
    )
    try:
        with engine.connect() as conn:
            res = conn.execute(sql, {"org_id": org_id})
            rows = _rows_to_list(res)
        return rows if rows else []
    except Exception as e:
        return f"Error computing default risk customers: {e}"


@tool
def draft_payment_reminder(customer_name: str, amount: float, days_overdue: int, org_id: str | None = None) -> str:
    """Draft a payment reminder message for a customer. Optionally include org scope."""
    header = f"[Org: {org_id}]\n\n" if org_id else ""
    return (
        header
        + f"Dear {customer_name},\n\n"
        f"This is a friendly reminder that your payment of NPR {amount:,.0f} "
        f"is overdue by {days_overdue} days.\n\n"
        "Please arrange payment at your earliest convenience.\n\n"
        "Thank you,\n"
        "OpScale"
    )
