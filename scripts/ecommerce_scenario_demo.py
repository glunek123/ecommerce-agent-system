"""
电商场景应用演示 - 展示客户端和商家端的不同使用场景

使用方法:
1. 启动 Mock 服务器: python scripts/mock_server.py
2. 启动 Agent API: uvicorn src.api.main:app --reload --port 8000
3. 运行此脚本: python scripts/ecommerce_scenario_demo.py
"""
import sys
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1/chat/"
HEALTH_URL = "http://localhost:8000/health/"


async def check_server() -> bool:
    """检查 API 服务器是否可用"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(HEALTH_URL)
            return resp.status_code == 200
    except httpx.ConnectError:
        return False


async def chat(session_id: str, user_id: str, message: str) -> dict:
    """
    发送对话请求

    Args:
        session_id: 会话ID
        user_id: 用户ID
        message: 用户消息

    Returns:
        API响应结果

    Raises:
        SystemExit: 服务器不可用时退出
    """
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.post(
                BASE_URL,
                json={"session_id": session_id, "user_id": user_id, "message": message}
            )
            if response.status_code != 200:
                print(f"\n❌ 请求失败 (HTTP {response.status_code}): {response.text[:300]}")
                return {"success": False, "message": f"请求失败: HTTP {response.status_code}", "tool_calls": []}
            return response.json()
    except httpx.ConnectError:
        print("\n❌ 无法连接到 API 服务器！请确认已启动:")
        print("   终端1: python scripts/mock_server.py")
        print("   终端2: uvicorn src.api.main:app --reload --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return {"success": False, "message": f"请求异常: {e}", "tool_calls": []}


async def customer_service_scenario():
    """
    场景一：客户端 - 普通用户购物咨询
    """
    print("\n" + "="*70)
    print("🛒 场景一：客户端 - 用户购物咨询")
    print("="*70)
    print("用户角色: 普通消费者")
    print("使用入口: 电商APP客服、网站在线客服、微信小程序")
    print("-"*70)
    
    session_id = "customer-session-001"
    user_id = "customer-001"
    
    conversations = [
        ("你好，我想买一部手机，有什么推荐吗？", "商品咨询"),
        ("iPhone 15 多少钱？有货吗？", "价格和库存查询"),
        ("什么时候能发货？", "物流咨询"),
        ("好的，帮我查一下我的订单 ORD123456", "订单查询"),
        ("能帮我取消这个订单吗？我不想要了", "订单取消"),
    ]
    
    for message, scenario in conversations:
        print(f"\n👤 用户 [{scenario}]: {message}")
        response = await chat(session_id, user_id, message)
        print(f"🤖 客服: {response['message'][:200]}...")
        if response.get('tool_calls'):
            tools = [tc['tool'] for tc in response['tool_calls']]
            print(f"   📌 调用工具: {', '.join(tools)}")


async def merchant_operation_scenario():
    """
    场景二：商家端 - 运营人员工作台
    """
    print("\n" + "="*70)
    print("👨‍💼 场景二：商家端 - 运营后台管理")
    print("="*70)
    print("用户角色: 运营人员/客服主管")
    print("使用入口: 运营后台智能助手、商家管理后台")
    print("-"*70)
    
    session_id = "merchant-session-001"
    user_id = "merchant-admin-001"
    
    conversations = [
        ("查看商品P001在北京仓的库存情况", "库存管理"),
        ("给用户customer-001发一张100元优惠券，有效期7天", "优惠券发放"),
        ("查看用户customer-001有哪些优惠券", "优惠券查询"),
        ("帮我统计一下今天的订单情况", "数据分析"),
    ]
    
    for message, scenario in conversations:
        print(f"\n👨‍💼 运营 [{scenario}]: {message}")
        response = await chat(session_id, user_id, message)
        print(f"🤖 助手: {response['message'][:200]}...")
        if response.get('tool_calls'):
            tools = [tc['tool'] for tc in response['tool_calls']]
            print(f"   📌 调用工具: {', '.join(tools)}")


async def after_sales_scenario():
    """
    场景三：客户端 - 售后服务
    """
    print("\n" + "="*70)
    print("🔧 场景三：客户端 - 售后服务")
    print("="*70)
    print("用户角色: 已购用户")
    print("使用入口: 订单详情页客服、售后入口")
    print("-"*70)
    
    session_id = "aftersales-session-001"
    user_id = "customer-002"
    
    conversations = [
        ("我买的商品什么时候能到？订单号是ORD123456", "物流查询"),
        ("我想修改收货地址，改成上海市浦东新区", "订单修改"),
        ("商品有质量问题，我想申请退款", "售后处理"),
    ]
    
    for message, scenario in conversations:
        print(f"\n👤 用户 [{scenario}]: {message}")
        response = await chat(session_id, user_id, message)
        print(f"🤖 客服: {response['message'][:200]}...")
        if response.get('tool_calls'):
            tools = [tc['tool'] for tc in response['tool_calls']]
            print(f"   📌 调用工具: {', '.join(tools)}")


async def marketing_scenario():
    """
    场景四：商家端 - 营销活动支持
    """
    print("\n" + "="*70)
    print("🎁 场景四：商家端 - 营销活动支持")
    print("="*70)
    print("用户角色: 营销人员")
    print("使用入口: 营销活动管理后台")
    print("-"*70)
    
    session_id = "marketing-session-001"
    user_id = "marketing-001"
    
    conversations = [
        ("帮我查一下有哪些用户最近7天没下单了", "用户分析"),
        ("给这些用户批量发放50元优惠券", "批量发券"),
        ("查看优惠券CPN-001的使用情况", "效果追踪"),
    ]
    
    for message, scenario in conversations:
        print(f"\n👩‍💼 营销 [{scenario}]: {message}")
        response = await chat(session_id, user_id, message)
        print(f"🤖 助手: {response['message'][:200]}...")
        if response.get('tool_calls'):
            tools = [tc['tool'] for tc in response['tool_calls']]
            print(f"   📌 调用工具: {', '.join(tools)}")


async def main():
    """
    主函数 - 运行所有场景演示
    """
    print("\n" + "🤖 " * 25)
    print("电商智能Agent系统 - 多场景应用演示")
    print("🤖 " * 25)

    if not await check_server():
        print("\n❌ API 服务器未启动！请先执行以下步骤:")
        print("   终端1: python scripts/mock_server.py")
        print("   终端2: uvicorn src.api.main:app --reload --port 8000")
        sys.exit(1)
    print("\n✅ API 服务器已连接")
    
    print("\n本系统支持以下应用场景:")
    print("┌─────────────────────────────────────────────────────┐")
    print("│  场景              │  使用端    │  主要功能          │")
    print("├─────────────────────────────────────────────────────┤")
    print("│  1. 购物咨询       │  客户端    │  商品搜索、价格查询 │")
    print("│  2. 订单服务       │  客户端    │  查询、修改、取消   │")
    print("│  3. 售后服务       │  客户端    │  退款、投诉处理     │")
    print("│  4. 库存管理       │  商家端    │  库存查询、预警     │")
    print("│  5. 优惠券管理     │  商家端    │  发放、查询、统计   │")
    print("│  6. 数据分析       │  商家端    │  订单统计、用户分析 │")
    print("└─────────────────────────────────────────────────────┘")
    
    print("\n选择要演示的场景:")
    print("1. 客户端 - 用户购物咨询")
    print("2. 商家端 - 运营后台管理")
    print("3. 客户端 - 售后服务")
    print("4. 商家端 - 营销活动支持")
    print("5. 运行所有场景")
    
    choice = input("\n请选择 (1-5): ").strip()
    
    if choice == "1":
        await customer_service_scenario()
    elif choice == "2":
        await merchant_operation_scenario()
    elif choice == "3":
        await after_sales_scenario()
    elif choice == "4":
        await marketing_scenario()
    else:
        await customer_service_scenario()
        await merchant_operation_scenario()
        await after_sales_scenario()
        await marketing_scenario()
    
    print("\n" + "="*70)
    print("📊 场景演示完成")
    print("="*70)
    print("\n💡 关键要点:")
    print("   • 客户端: 面向C端用户，提供购物咨询和订单服务")
    print("   • 商家端: 面向运营人员，提供库存和优惠券管理")
    print("   • 通过不同的 user_id 和权限控制区分两端")
    print("   • 工具调用对用户透明，Agent自动选择合适的工具")


if __name__ == "__main__":
    asyncio.run(main())
