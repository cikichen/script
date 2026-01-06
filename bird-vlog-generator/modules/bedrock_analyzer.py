"""AI 视觉分析模块 - 使用 OpenAI GPT-4 Vision"""

import base64
import json
import os
import sys
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL

client = OpenAI(
    api_key=OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"),
    base_url=OPENAI_BASE_URL
)

ANALYSIS_PROMPT = """分析这张图片，返回 JSON 格式：
{
    "has_bird": true/false,
    "bird_species": "鸟类名称或 null",
    "activity": "行为描述（如筑巢/觅食/休息/喂食幼鸟/飞行）",
    "scene_description": "场景一句话描述",
    "highlight_score": 1-10,
    "timestamp_suggestion": "建议的旁白文字"
}

评分标准:
- 10分: 极其罕见的精彩瞬间
- 7-9分: 精彩互动
- 4-6分: 普通活动
- 1-3分: 无主体或画面模糊

只返回 JSON，不要其他内容。"""


def analyze_image(image_path: str, prompt: str = ANALYSIS_PROMPT) -> str:
    """使用 GPT-4 Vision 分析图像"""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    ext = image_path.lower().split(".")[-1]
    media_type = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(ext, "jpeg")
    
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/{media_type};base64,{image_data}"}}
                ]
            }
        ],
        max_tokens=1024
    )
    
    return response.choices[0].message.content


from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_analyze(image_data_list: list, max_workers: int = 5, progress_callback=None) -> list[dict]:
    """批量分析图像（支持并行处理）
    
    Args:
        image_data_list: 图片路径列表 [str, ...] 或关键帧信息列表 [{"path": str, ...}, ...]
        max_workers: 最大并行线程数
        progress_callback: 进度回调函数
    """
    results = [None] * len(image_data_list)
    total = len(image_data_list)
    
    def worker(index, image_data):
        # 兼容字符串路径和字典对象
        path = image_data.get("path") if isinstance(image_data, dict) else image_data
        
        try:
            text = analyze_image(path)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            
            data = json.loads(text)
            
            # 合并原始信息
            if isinstance(image_data, dict):
                data.update(image_data)
            
            data["frame_path"] = path
            data["frame_index"] = index
            return index, data
            
        except Exception as e:
            print(f"  分析失败 [{index}]: {path}, 错误: {e}")
            fallback = {
                "frame_path": path, 
                "frame_index": index, 
                "has_bird": False, 
                "highlight_score": 0, 
                "error": str(e)
            }
            if isinstance(image_data, dict):
                # 保留原始的时间戳等信息
                fallback.update(image_data)
            return index, fallback

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(worker, i, data): i for i, data in enumerate(image_data_list)}
        
        count = 0
        for future in as_completed(future_to_index):
            idx, result = future.result()
            results[idx] = result
            count += 1
            if progress_callback:
                progress_callback(count, total)
    
    return results


def filter_highlights(results: list[dict], min_score: int = 7) -> list[dict]:
    """筛选精彩片段"""
    return [r for r in results if r.get("highlight_score", 0) >= min_score]
