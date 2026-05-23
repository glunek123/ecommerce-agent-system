"""
电商 Mock 服务器 - 模拟所有电商 API 端点，供本地开发和测试使用。
启动: python scripts/mock_server.py
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="电商 Mock API")


@app.get("/inventory/query")
def inventory_query(product_id: str, warehouse: str = "北京仓"):
    return {
        "product_id": product_id,
        "warehouse": warehouse,
        "stock": 128,
        "available": True,
        "estimated_ship_date": "2026-05-24"
    }


@app.post("/inventory/reserve")
async def inventory_reserve(request: Request):
    body = await request.json()
    return {
        "reserve_id": f"RSV-{body['order_id']}",
        "product_id": body["product_id"],
        "quantity": body["quantity"],
        "status": "reserved"
    }


@app.get("/product/search")
def product_search(keyword: str, category: str = None, page: int = 1, page_size: int = 10):
    products = [
        {"id": f"P00{i}", "name": f"{keyword} 商品{i}", "price": 99.0 * i,
         "category": category or "数码", "stock": 50}
        for i in range(1, 4)
    ]
    return {"total": len(products), "page": page, "items": products}


@app.get("/product/{product_id}")
def product_detail(product_id: str):
    return {
        "id": product_id,
        "name": f"商品 {product_id}",
        "price": 299.0,
        "category": "数码",
        "specs": {"颜色": "黑色", "内存": "256GB"},
        "stock": 88,
        "description": "这是一款优质商品"
    }


@app.get("/order/detail")
def order_detail(order_id: str, user_id: str = None):
    return {
        "order_id": order_id,
        "user_id": user_id or "U001",
        "status": "shipped",
        "items": [{"product_id": "P001", "name": "示例商品", "quantity": 1, "price": 299.0}],
        "total": 299.0,
        "address": "北京市朝阳区某街道1号",
        "logistics": {"company": "顺丰", "tracking_no": "SF1234567890", "status": "运输中"}
    }


@app.put("/order/modify")
async def order_modify(request: Request):
    body = await request.json()
    return {
        "order_id": body["order_id"],
        "modification_type": body["modification_type"],
        "status": "modified",
        "message": "订单修改成功"
    }


@app.post("/order/cancel")
async def order_cancel(request: Request):
    body = await request.json()
    return {
        "order_id": body["order_id"],
        "status": "cancelled",
        "reason": body["reason"],
        "refund_amount": 299.0
    }


@app.post("/coupon/send")
async def coupon_send(request: Request):
    body = await request.json()
    return {
        "coupon_id": f"CPN-{body['user_id']}-001",
        "user_id": body["user_id"],
        "amount": body["amount"],
        "expire_days": body.get("expire_days", 7),
        "status": "sent"
    }


@app.get("/coupon/list")
def coupon_list(user_id: str, status: str = None):
    coupons = [
        {"coupon_id": "CPN-001", "amount": 1000, "type": "满减券",
         "status": "valid", "expire_date": "2026-06-01"},
        {"coupon_id": "CPN-002", "amount": 500, "type": "折扣券",
         "status": "valid", "expire_date": "2026-05-31"},
    ]
    if status:
        coupons = [c for c in coupons if c["status"] == status]
    return {"user_id": user_id, "total": len(coupons), "coupons": coupons}


if __name__ == "__main__":
    print("启动电商 Mock 服务器: http://localhost:9000")
    print("API 文档: http://localhost:9000/docs")
    uvicorn.run(app, host="0.0.0.0", port=9000)
