"""AI 视觉分析模块 - 使用 OpenAI GPT-4 Vision"""

import base64
import json
import os
import sys
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, HIGHLIGHT_MIN_SCORE

client = OpenAI(
    api_key=OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"),
    base_url=OPENAI_BASE_URL
)

ANALYSIS_PROMPT = """你是一个顶级的自然摄影评审，专门负责从大量的野外素材中挑选出最精彩的片段。
请分析这张图片，识别鸟类名称、行为，并根据以下**严苛**的标准给出 1-10 的“高光分 (highlight_score)”：

### 重点关注的高价值行为：
- **顶级 (9-10分)**：捕食瞬间（抓鱼、捕蝉）、空中格斗、极速俯冲、破水而出、育雏喂食、求偶舞步、交配。
- **高价值 (7-8分)**：展翅高飞、悬停（如蜂鸟或翠鸟）、俯冲预备、带食材回巢、筑巢加固、激烈争吵、洗澡溅水、刚起飞或落枝的瞬间。
- **中等 (5-6分)**：稳定鸣叫、梳理羽毛、缓慢行走觅食、好奇观察镜头、警戒姿态。
- **低价值 (1-4分)**：静止睡觉、背对镜头、主体模糊、遮挡严重或纯背景。

### 评分标准：
- **10分 (顶级珍宝)**：极罕见瞬间 + 完美构图 + 主体清晰巨大。
- **8-9分 (非常精彩)**：动作感极强，画面锐利，主体突出。
- **6-7分 (优秀素材)**：典型行为展示，主体清晰，背景干净。
- **4-5分 (平庸记录)**：主体偏小或行为单一，画面一般。
- **1-3分 (废片)**：无主体、模糊或严重遮挡。

请以 JSON 格式返回：
{
    "has_bird": true/false,
    "bird_species": "具体鸟名，不确定则写种类名，无则 null",
    "activity": "简炼的动态描述（如：悬停寻猎、带树枝筑巢、破水而出）",
    "behavior_category": "行为分类（取值：捕食/飞行/空中互动/育雏/求偶/洗澡/理羽/休息/寻觅/其他）",
    "scene_description": "画面意境描述（如：晨雾中展开的双翼）",
    "highlight_score": 1-10 (整数),
    "composition_quality": "从摄影角度评价构图",
    "timestamp_suggestion": "建议的短旁白核心（5-10字，绝对严禁含标签编号）"
}

只返回纯 JSON，不要任何 Markdown 块或额外解释。"""


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
