"""
图片生成功能插件
通过硅基流动 FLUX.1 API 生成图片，并在客户端屏幕上显示

使用方法：
1. 在硅基流动平台注册并获取 API Key: https://cloud.siliconflow.cn/
2. 在 config.yaml 的 plugins 节点下添加配置：
   generate_image:
     api_key: "你的API密钥"
     model: "black-forest-labs/FLUX.1-schnell"
     default_size: "512x512"
3. 在 Intent.function_call.functions 列表中添加 "generate_image"
"""

import json
import aiohttp
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

# 功能描述 - LLM 会根据此描述判断何时调用
GENERATE_IMAGE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "根据用户描述生成图片并显示在屏幕上。"
            "**重要**: 当用户请求画图时，立即调用此函数，不要询问风格偏好。"
            "如果用户未指定风格，默认使用cartoon(卡通)风格。"
            "例如：'帮我画一只小猫' -> 直接调用，使用cartoon风格"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "图片描述，详细描述要生成的图片内容、风格、颜色等。例如：一只可爱的橘猫在草地上玩耍，阳光明媚。注意：由于屏幕是圆形的，主要内容应该放在图片中心区域"
                },
                "style": {
                    "type": "string",
                    "enum": ["realistic", "cartoon", "anime", "oil_painting", "watercolor", "digital_art", "none"],
                    "description": "图片风格：realistic(写实)、cartoon(卡通)、anime(动漫)、oil_painting(油画)、watercolor(水彩)、digital_art(数字艺术)、none(不指定)"
                },
                "size": {
                    "type": "string",
                    "enum": ["512x512", "768x768", "1024x1024"],
                    "description": "图片尺寸。推荐使用512x512(生成速度快)或1024x1024(细节更丰富)"
                },
            },
            "required": ["prompt"],
        },
    },
}

# 风格提示词映射
STYLE_PROMPTS = {
    "realistic": "photorealistic, high detail, 8k resolution, professional photography",
    "cartoon": "cartoon style, vibrant colors, playful, cute character design",
    "anime": "anime style, manga art, detailed linework, vibrant colors",
    "oil_painting": "oil painting, artistic, classical style, rich textures",
    "watercolor": "watercolor painting, soft colors, delicate, artistic",
    "digital_art": "digital art, concept art, high quality, detailed",
    "none": ""
}


async def generate_image_with_siliconflow(
    api_key: str,
    prompt: str,
    model: str = "black-forest-labs/FLUX.1-schnell",
    image_size: str = "512x512",
    style: str = None
) -> dict:
    """
    调用硅基流动 Stable Diffusion API 生成图片
    
    Args:
        api_key: 硅基流动 API 密钥
        prompt: 图片描述
        model: 模型名称
        image_size: 图片尺寸
        style: 图片风格
    
    Returns:
        dict: {"success": bool, "url": str, "error": str}
    """
    # 根据风格优化 prompt
    enhanced_prompt = prompt
    if style and style in STYLE_PROMPTS and style != "none":
        style_suffix = STYLE_PROMPTS[style]
        if style_suffix:
            enhanced_prompt = f"{prompt}, {style_suffix}"
    
    # 为圆形屏幕添加提示：主要内容放在中心，避免边缘被裁剪
    circular_hint = "centered composition, main subject in center of frame, avoid important details at edges"
    enhanced_prompt = f"{enhanced_prompt}, {circular_hint}"
    
    url = "https://api.siliconflow.cn/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "prompt": enhanced_prompt,
        "image_size": image_size,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
        "num_images": 1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("images") and len(data["images"]) > 0:
                        return {
                            "success": True,
                            "url": data["images"][0].get("url")
                        }
                    else:
                        return {
                            "success": False,
                            "error": "API 返回数据格式异常"
                        }
                else:
                    error_text = await response.text()
                    logger.bind(tag=TAG).error(f"硅基流动 API 调用失败: {response.status} - {error_text}")
                    return {
                        "success": False,
                        "error": f"API 调用失败: {response.status}"
                    }
    except aiohttp.ClientError as e:
        logger.bind(tag=TAG).error(f"网络请求错误: {e}")
        return {"success": False, "error": f"网络请求错误: {str(e)}"}
    except Exception as e:
        logger.bind(tag=TAG).error(f"图片生成异常: {e}")
        return {"success": False, "error": f"生成异常: {str(e)}"}


async def show_image_on_client(conn: "ConnectionHandler", image_url: str) -> bool:
    """
    通过 MCP 协议在客户端显示图片
    
    Args:
        conn: 连接处理器
        image_url: 图片 URL
    
    Returns:
        bool: 是否成功
    """
    try:
        # 检查客户端是否支持 MCP
        if not hasattr(conn, "mcp_client") or not conn.mcp_client:
            logger.bind(tag=TAG).warning("客户端不支持 MCP，无法显示图片")
            return False
        
        # 检查 MCP 客户端是否就绪
        if not await conn.mcp_client.is_ready():
            logger.bind(tag=TAG).warning("MCP 客户端未就绪")
            return False
        
        # 导入 MCP 工具调用函数
        from core.providers.tools.device_mcp.mcp_handler import call_mcp_tool
        from core.utils.util import sanitize_tool_name
        
        # 调用客户端的图片预览工具（使用 sanitized 名称，点号变下划线）
        tool_name = sanitize_tool_name("self.screen.preview_image")
        result = await call_mcp_tool(
            conn,
            conn.mcp_client,
            tool_name,
            json.dumps({"url": image_url}),
            timeout=30
        )
        
        logger.bind(tag=TAG).info(f"图片显示结果: {result}")
        return True
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"MCP 调用失败: {e}")
        return False


@register_function("generate_image", GENERATE_IMAGE_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def generate_image(conn: "ConnectionHandler", prompt: str, style: str = "none", size: str = None):
    """
    图片生成工具函数
    
    Args:
        conn: 连接处理器，包含配置和 MCP 客户端
        prompt: 图片描述
        style: 图片风格
        size: 图片尺寸 (512x512, 768x768, 1024x1024)
    
    Returns:
        ActionResponse: 指示后续动作
    """
    logger.bind(tag=TAG).info(f"开始生成图片，提示词: {prompt}, 风格: {style}, 尺寸: {size}")
    
    # 获取插件配置
    image_config = conn.config.get("plugins", {}).get("generate_image", {})
    api_key = image_config.get("api_key")
    
    if not api_key:
        return ActionResponse(
            Action.RESPONSE,
            None,
            "图片生成功能未配置，请在配置文件中设置 API 密钥"
        )
    
    model = image_config.get("model", "black-forest-labs/FLUX.1-schnell")
    # 默认使用 512x512，更适合圆形屏幕
    default_size = image_config.get("default_size", "512x512")
    image_size = size if size else default_size
    
    # 调用硅基流动 API 生成图片
    result = await generate_image_with_siliconflow(
        api_key=api_key,
        prompt=prompt,
        model=model,
        image_size=default_size,
        style=style
    )
    
    if not result["success"]:
        error_msg = result.get("error", "未知错误")
        logger.bind(tag=TAG).error(f"图片生成失败: {error_msg}")
        return ActionResponse(
            Action.REQLLM,
            f"图片生成失败：{error_msg}。请告知用户并建议稍后重试。",
            None
        )
    
    image_url = result["url"]
    logger.bind(tag=TAG).info(f"图片生成成功，URL: {image_url}")
    
    # 在客户端显示图片
    display_success = await show_image_on_client(conn, image_url)
    
    if display_success:
        # 生成成功消息给 LLM
        style_desc = f"，风格为{style}" if style and style != "none" else ""
        return ActionResponse(
            Action.REQLLM,
            f"已成功生成图片{style_desc}，图片正在设备屏幕上显示。"
            f"图片描述：{prompt}。"
            f"请用简洁友好的语言告诉用户图片已生成并显示在屏幕上。",
            None
        )
    else:
        # 图片生成成功但显示失败
        return ActionResponse(
            Action.REQLLM,
            f"图片已生成成功，但无法在设备屏幕上显示。图片 URL: {image_url}。"
            f"请告知用户图片已生成，但显示功能可能需要设备支持 MCP 协议。",
            None
        )
