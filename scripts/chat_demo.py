"""
电商Agent系统使用示例 - 演示如何通过API进行多轮对话

使用方法:
1. 先启动 Mock 服务器: python scripts/mock_server.py
2. 再启动 Agent API: uvicorn src.api.main:app --reload --port 8000
3. 运行此脚本: python scripts/chat_demo.py
"""
import sys
import httpx
import asyncio
import json

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
        session_id: 会话ID，相同ID保持对话上下文
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
                json={
                    "session_id": session_id,
                    "user_id": user_id,
                    "message": message
                }
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


async def clear_session(session_id: str, user_id: str) -> dict:
    """
    清除会话记忆

    Args:
        session_id: 会话ID
        user_id: 用户ID

    Returns:
        清除结果
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.post(
                f"{BASE_URL}clear",
                json={"session_id": session_id, "user_id": user_id}
            )
            if response.status_code != 200:
                print(f"\n❌ 清除会话失败 (HTTP {response.status_code})")
                return {"success": False, "message": f"清除失败: HTTP {response.status_code}"}
            return response.json()
    except httpx.ConnectError:
        print("\n❌ 无法连接到 API 服务器！")
        return {"success": False, "message": "服务器不可用"}
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return {"success": False, "message": f"请求异常: {e}"}


def print_response(response: dict, round_num: int):
    """
    格式化打印响应
    
    Args:
        response: API响应
        round_num: 轮次编号
    """
    print(f"\n{'='*60}")
    print(f"第 {round_num} 轮对话")
    print(f"{'='*60}")
    print(f"✅ 成功: {response['success']}")
    print(f"📝 Agent回复:\n{response['message']}")
    if response.get('tool_calls'):
        print(f"\n🔧 调用的工具:")
        for tc in response['tool_calls']:
            print(f"   - {tc['tool']}: {tc['input']}")


async def demo_multi_round_conversation():
    """
    演示多轮对话场景
    """
    session_id = "demo-session-001"
    user_id = "user-001"

    print("\n" + "🤖 " * 20)
    print("电商智能客服多轮对话演示")
    print("🤖 " * 20)

    conversations = [
        "你好，我想问问有没有手机？",
        "那iPhone 15多少钱？",
        "有货吗？什么时候能发货？",
        "帮我查一下我的订单，订单号是 ORD123456",
        "好的，谢谢！"
    ]

    for i, message in enumerate(conversations, 1):
        print(f"\n👤 用户: {message}")
        response = await chat(session_id, user_id, message)
        print_response(response, i)

    print("\n" + "="*60)
    print("📊 多轮对话总结:")
    print("   - 使用相同的 session_id 保持对话上下文")
    print("   - Agent 会记住之前的对话内容")
    print("   - 自动调用相关工具获取实时数据")
    print("="*60)


async def demo_different_sessions():
    """
    演示不同会话之间相互独立
    """
    print("\n" + "🔄 " * 20)
    print("不同会话独立性演示")
    print("🔄 " * 20)

    user_id = "user-001"

    print("\n--- 会话A ---")
    print("👤 用户: 有没有笔记本电脑？")
    resp_a1 = await chat("session-A", user_id, "有没有笔记本电脑？")
    print(f"🤖 Agent: {resp_a1['message'][:100]}...")

    print("\n--- 会话B (新会话) ---")
    print("👤 用户: 多少钱？")
    resp_b1 = await chat("session-B", user_id, "多少钱？")
    print(f"🤖 Agent: {resp_b1['message'][:100]}...")
    print("   (注意: 新会话不知道之前问的是笔记本电脑)")

    print("\n--- 会话A (继续) ---")
    print("👤 用户: 有现货吗？")
    resp_a2 = await chat("session-A", user_id, "有现货吗？")
    print(f"🤖 Agent: {resp_a2['message'][:100]}...")
    print("   (注意: 会话A还记得之前问的是笔记本电脑)")


async def interactive_chat():
    """
    交互式命令行对话
    """
    session_id = input("请输入会话ID (直接回车使用默认): ").strip() or "cli-session"
    user_id = input("请输入用户ID (直接回车使用默认): ").strip() or "cli-user"

    print(f"\n开始对话 (session: {session_id}, user: {user_id})")
    print("输入 'quit' 退出, 'clear' 清除会话\n")

    round_num = 1
    while True:
        message = input("👤 你: ").strip()
        if message.lower() == 'quit':
            break
        if message.lower() == 'clear':
            await clear_session(session_id, user_id)
            print("✅ 会话已清除\n")
            round_num = 1
            continue
        if not message:
            continue

        response = await chat(session_id, user_id, message)
        print(f"🤖 Agent: {response['message']}")
        if response.get('tool_calls'):
            tools = [tc['tool'] for tc in response['tool_calls']]
            print(f"   [调用工具: {', '.join(tools)}]")
        round_num += 1


async def main():
    """
    主函数 - 选择演示模式
    """
    if not await check_server():
        print("\n❌ API 服务器未启动！请先执行以下步骤:")
        print("   终端1: python scripts/mock_server.py")
        print("   终端2: uvicorn src.api.main:app --reload --port 8000")
        sys.exit(1)
    print("✅ API 服务器已连接\n")

    print("选择演示模式:")
    print("1. 多轮对话演示 (自动)")
    print("2. 不同会话独立性演示")
    print("3. 交互式对话")

    choice = input("\n请选择 (1/2/3): ").strip()

    if choice == "1":
        await demo_multi_round_conversation()
    elif choice == "2":
        await demo_different_sessions()
    elif choice == "3":
        await interactive_chat()
    else:
        print("运行多轮对话演示...")
        await demo_multi_round_conversation()


if __name__ == "__main__":
    asyncio.run(main())
