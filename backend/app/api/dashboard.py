from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
from app.db.session import get_session
from app.models.order import Order
from sqlmodel import select, func
import logging
from starlette.responses import HTMLResponse

logger = logging.getLogger(__name__)
router = APIRouter()

def _render_summary_html(total: int, revenue: float, pending: int) -> str:
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Dashboard Summary</title>
  <style>
    body {{ font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; background:#f3f4f6; padding:24px; }}
    .container {{ max-width:1100px; margin:0 auto; }}
    .cards {{ display:flex; gap:16px; margin-bottom:20px; }}
    .card {{ background:white;padding:20px;border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.06); flex:1 }}
    .title {{ color:#6b7280; font-size:13px }}
    .value {{ font-size:28px; font-weight:700; margin-top:6px }}
    table {{ width:100%; border-collapse:collapse; margin-top:12px; background:white; border-radius:8px; overflow:hidden }}
    th, td {{ padding:12px; text-align:left; border-bottom:1px solid #eef2f7 }}
    thead {{ background:#f9fafb }}
    .nav {{ margin-bottom:18px }}
    .nav a {{ margin-right:12px; color:#2563eb; text-decoration:none }}
  </style>
</head>
<body>
  <div class="container">
    <div class="nav"><a href="/">Home</a> <a href="/dashboard">Dashboard</a> <a href="/orders">Orders</a></div>
    <h1>Dashboard Summary</h1>
    <div class="cards">
      <div class="card"><div class="title">Total Orders</div><div class="value">{total}</div></div>
      <div class="card"><div class="title">Revenue</div><div class="value">${revenue:.2f}</div></div>
      <div class="card"><div class="title">Pending Reviews</div><div class="value">{pending}</div></div>
    </div>
    <h2>Recent Orders</h2>
    <table>
      <thead><tr><th>ID</th><th>Product</th><th>Qty</th><th>Status</th><th>Price</th><th>Issues</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <script>
      // Use string concatenation (avoid JS template literals) so Python f-strings don't interfere
      fetch('/dashboard/orders').then(function(r){{ return r.json(); }}).then(function(rows){{
        var tbody = document.getElementById('rows');
        rows.slice().reverse().slice(0,20).forEach(function(o){{
          var tr = document.createElement('tr');
          var id = o.id !== undefined ? o.id : '';
          var product = o.product_type || '—';
          var qty = o.quantity !== undefined && o.quantity !== null ? o.quantity : '—';
          var status = o.status || '—';
          var price = (o.final_price != null) ? ('$' + o.final_price) : '—';
          var issues = o.issues || '';
          tr.innerHTML = '<td>' + id + '</td>' + '<td>' + product + '</td>' + '<td>' + qty + '</td>' + '<td>' + status + '</td>' + '<td>' + price + '</td>' + '<td>' + issues + '</td>';
          tbody.appendChild(tr);
        }});
      }});
    </script>
  </div>
</body>
</html>
"""

@router.get("/summary")
async def summary(request: Request) -> Any:
    session = get_session()
    try:
        total = session.exec(select(func.count()).select_from(Order)).one()
        if isinstance(total, tuple):
            total = total[0]
        total = int(total or 0)
        rows = session.exec(select(Order)).all()
        total_revenue = sum((o.final_price or 0) for o in rows)
        pending = session.exec(select(func.count()).select_from(Order).where(Order.status == "needs_review")).one()
        if isinstance(pending, tuple):
            pending = pending[0]
        pending = int(pending or 0)

        accept = request.headers.get('accept','')
        if 'text/html' in accept:
            html = _render_summary_html(total, total_revenue, pending)
            return HTMLResponse(content=html)

        return {"total_orders": total, "revenue": total_revenue, "pending": pending}
    except Exception as e:
        logger.exception("Failed to compute summary: %s", e)
        raise HTTPException(status_code=500, detail="Failed to compute dashboard summary")
    finally:
        session.close()

@router.get("/orders")
async def orders(request: Request):
    session = get_session()
    try:
        rows = session.exec(select(Order).order_by(Order.id)).all()
        result = []
        for o in rows:
            result.append({
                "id": o.id,
                "product_type": o.product_type,
                "quantity": o.quantity,
                "status": o.status,
                "final_price": o.final_price,
                "email": getattr(o, 'email', None),
                "issues": o.issues,
            })

        accept = request.headers.get('accept','')
        if 'text/html' in accept:
            # simple HTML table view
            rows_html = ''.join([f"<tr><td>{r['id']}</td><td>{r['product_type'] or '—'}</td><td>{r['quantity'] or '—'}</td><td>{r['status']}</td><td>{r['final_price'] if r['final_price']!=None else '—'}</td><td>{r.get('email') or ''}</td><td>{r['issues'] or ''}</td></tr>" for r in result])
            html = f"""
<!doctype html>
<html><head><meta charset='utf-8' /><title>Orders</title>
<style>body{{font-family:Inter,system-ui, -apple-system, 'Segoe UI', Roboto; background:#f3f4f6; padding:24px}} table{{width:100%; border-collapse:collapse; background:white}}th,td{{padding:12px;border-bottom:1px solid #eef2f7}}thead{{background:#f9fafb}}</style>
</head><body><div class='container'><h1>Orders</h1><table><thead><tr><th>ID</th><th>Product</th><th>Qty</th><th>Status</th><th>Price</th><th>Email</th><th>Issues</th></tr></thead><tbody>{rows_html}</tbody></table></div></body></html>
"""
            return HTMLResponse(content=html)

        return result
    finally:
        session.close()

@router.get("/stats")
async def stats(request: Request):
    session = get_session()
    try:
        rows = session.exec(select(Order)).all()
        by_status: Dict[str, int] = {}
        for o in rows:
            by_status[o.status or "unknown"] = by_status.get(o.status or "unknown", 0) + 1

        accept = request.headers.get('accept','')
        if 'text/html' in accept:
            items = ''.join([f"<li><strong>{k}</strong>: {v}</li>" for k,v in by_status.items()])
            html = f"""
<!doctype html>
<html><head><meta charset='utf-8' /><title>Stats</title>
<style>body{{font-family:Inter,system-ui, -apple-system, 'Segoe UI', Roboto; background:#f3f4f6; padding:24px}} ul{{background:white;padding:20px;border-radius:8px;}}</style>
</head><body><div class='container'><h1>Stats</h1><ul>{items}</ul></div></body></html>
"""
            return HTMLResponse(content=html)

        return {"by_status": by_status}
    finally:
        session.close()
