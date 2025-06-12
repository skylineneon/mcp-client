import json
import httpx
from typing import Any

# OpenWeather API 配置
OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5/weather"
API_KEY = "a362f7bd06439a64837bb0831d5fe81d"  # 请替换为你自己的 OpenWeather API Key
USER_AGENT = "weather-app/1.0"  # 给当前Agent设置一个名字


async def fetch_weather(city: str) -> dict[str, Any] | None:
    """
    从 OpenWeather API 获取天气信息。
    :param city: 城市名称（需使用英文，如 Beijing）
    :return: 天气数据字典；若出错返回包含 error 信息的字典
    """
    params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "zh_cn"}
    headers = {"User-Agent": USER_AGENT}
    # 异步请求
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                OPENWEATHER_API_BASE, params=params, headers=headers, timeout=30.0
            )
            response.raise_for_status()  # 如果响应状态码不是200，将抛出异常
            return response.json()  # 返回字典类型的响应内容
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}


def format_weather(data: dict[str, Any] | str) -> str:
    """
    将天气数据格式化为易读文本。
    :param data: 天气数据（可以是字典或 JSON 字符串）
    :return: 格式化后的天气信息字符串
    """
    # 如果传入的是字符串，则先转换为字典
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return f"无法解析天气数据: {e}"
    # 如果数据中包含错误信息，直接返回错误提示
    if "error" in data:
        return f"⚠️ {data['error']}"

    # 提取数据时做容错处理
    city = data.get("name", "未知")
    country = data.get("sys", {}).get("country", "未知")
    temp = data.get("main", {}).get("temp", "N/A")
    humidity = data.get("main", {}).get("humidity", "N/A")
    wind_speed = data.get("wind", {}).get("speed", "N/A")
    # weather 可能为空列表，因此用 [0] 前先提供默认字典
    weather_list = data.get("weather", [{}])
    description = weather_list[0].get("description", "未知")
    return (
        f"🌎 {city}, {country}\n"
        f"🌡️ 温度: {temp}°C\n"
        f"💧 湿度: {humidity}%\n"
        f"🍃 风速: {wind_speed} m/s\n"
        f"☀️ 天气: {description}\n"
    )


async def query_weather(city: str) -> str:
    """
    当你想查询指定城市的天气时非常有用。输入指定城市的英文名称，返回今日天气查询结果。
    :param city: 城市名称（需使用英文）
    """
    data = await fetch_weather(city)
    return format_weather(data)
