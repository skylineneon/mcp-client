import asyncio
import sys
from mcp import ClientSession
from contextlib import AsyncExitStack
from openai import OpenAI
import os
from dotenv import load_dotenv

import json
from typing import Optional
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client  # 基于参数启动标准输入输出客户端

load_dotenv()


class MCPClient:
    def __init__(self):
        """初始化 MCP 客户端"""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.base_url = os.getenv("BASE_URL")
        self.model = os.getenv("MODEL")
        self.api_key = os.getenv("API_KEY")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    async def llm(self, query):
        """接入模型"""
        messages = [
            # {"role": "system", "content": "如果用户询问天气，使用工具查询天气。"},
            {"role": "user", "content": query},
        ]
        # 把当前所有的外部工具放在list里
        response = await self.session.list_tools()
        print(f"response1:{response}", end="\n\n")
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                },
            }
            for tool in response.tools
        ]
        # print(f"available_tools:{available_tools}")
        # 默认返回元组
        # response = await asyncio.get_event_loop().run_in_executor(
        #     None,
        #     lambda: self.client.chat.completions.create(
        #         model=self.model, messages=messages, stream=False, tools=available_tools
        #     ),
        # )
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=available_tools
        )

        # 处理返回的内容
        print(f"response2:{response}", end="\n\n")
        
        content = response.choices[0]
        # print(f"content.finish_reason: {content.finish_reason}")
        if content.finish_reason == "tool_calls":
            length = len(response.choices[0].message.tool_calls)
            print(f"地点数量:{length}", end="\n\n")
            for i in range(length):
                # print(f"{i}:{content.message.tool_calls[i]}", end="\n\n")

                # 解析工具名称和参数
                tool_call = content.message.tool_calls[i]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                print(f"\n\n[Calling tool {tool_name} with args {tool_args}]\n\n")
                # 执行工具
                result = await self.session.call_tool(tool_name, tool_args)
                print("tool_result:", result, end="\n\n")
                # 将模型返回的调用哪个工具数据和工具执行完成后的数据都存入messages中

                # content.message.model_dump()["tool_calls"]=content.message.model_dump()["tool_calls"][i]
                messages_dict = content.message.model_dump()
                messages_dict["tool_calls"][:] = [
                    content.message.model_dump()["tool_calls"][i]
                ]
                # print(f"content.message.model_dump():{messages_dict}")
                messages.append(
                    messages_dict
                )  # 消息内容序列化成一种可以存储或传输的格式，这里是字典类型
                # print(f"content.message.model_dump():{content.message.model_dump()}")

                messages.append(
                    {
                        "role": "tool",
                        "content": result.content[0].text,
                        "tool_call_id": tool_call.id,
                    }
                )
            response = self.client.chat.completions.create(
                model=self.model, messages=messages
            )
            print(f"response3:{response}", end="\n\n")
            return response.choices[0].message.content
        return content.message.content

    # 需要保证运行client的同时运行server脚本
    async def connect_to_server(self, server_script_path: str):
        """连接到 MCP 服务器并列出可用工具"""
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("服务器脚本必须是 .py 或 .js 文件")

        command = "python" if is_python else "node"
        # 创建一个包含启动命令、脚本路径和环境变量的参数对象
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )
        # 启动 MCP 服务器并建立通信
        stdio_transport = await self.exit_stack.enter_async_context(  # 以异步上下文管理器的方式启动客户端，确保资源在程序结束时被正确释放
            stdio_client(server_params)  # 基于参数启动标准输入输出客户端
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(
                self.stdio, self.write
            )  # 基于已建立的通信通道创建一个 MCP 客户端会话
        )

        await self.session.initialize()

        # 列出 MCP 服务器上的工具
        response = await self.session.list_tools()
        tools = response.tools
        print("\n已连接到服务器，支持以下工具：", [tool.name for tool in tools])
        # List available prompts
        prompts = await self.session.list_prompts()
        print("\n已连接到服务器，支持以下提示：", prompts)
        # Get a prompt
        # prompt = await self.session.get_prompt(
        #     "example-prompt", arguments={"arg1": "value"}
        # )
        # print("\n已连接到服务器，支持以下提示：", prompts)
        # resources = await self.session.list_resources()
        # resources = resources.resources
        # print("\n已连接到服务器，支持以下资源：", resources)
        

    async def chat_loop(self):
        """运行交互式聊天循环"""
        print("\nMCP 客户端已启动！输入 'quit' 退出")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break
                response = await self.llm(query)
                print(f"\nResponse: {response}")
            except Exception as e:
                print(f"\n 发生错误: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
