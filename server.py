from mcp.server.fastmcp import FastMCP
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from get_weather import query_weather
from computer_config import get_host_info

# 初始化 MCP 服务器,并命名
mcp = FastMCP("WeatherServer",port=8990) # 若为sse模式，则需要指定port
app = Server("example-server")

mcp.add_tool(query_weather)
mcp.add_tool(get_host_info)

@mcp.prompt()
def review_code(code: str) -> str:
    """
    当你想审查代码时，可以使用这个函数审查以下代码：
    :param code: 要审查的代码
    :return: 审查结果
    """
    return f"请审查以下代码：\n\n{code}"



if __name__ == "__main__":
    # 采用标准IO 作为传输方式
    """
    当指定transport="stdio"运行MCP服务器时，客户端必须在启动时同时启动当前
    这个脚本，否则无法进行通信。因为stdio模式是一种本地进程间的通信方式。
    它需要服务器作为子进程运行
    因此，编辑完服务器后，并不能直接调用这个服务器，而是需要创建一个对应的能够进行
    stdio的客户端，才能够进行通信
    """
    
    mcp.run(transport="stdio")
    # mcp.run(transport="sse")
    
