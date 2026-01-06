"""故事脚本生成模块 - 使用 OpenAI GPT（带片段对应）"""

import json
import os
import sys
import re
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL

client = OpenAI(
    api_key=OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"),
    base_url=OPENAI_BASE_URL
)


def generate_script(analysis_results: list[dict], style: str = "温馨") -> str:
    """根据分析结果生成 Vlog 旁白脚本（通用版本）"""
    valid_results = [r for r in analysis_results if r.get("has_bird") or r.get("highlight_score", 0) > 3]
    
    if not valid_results:
        return "这是一段宁静的自然观察记录，让我们一起感受大自然的美好。"
    
    summary = json.dumps(valid_results, ensure_ascii=False, indent=2)
    
    style_guide = {
        "温馨": "语气温馨、富有故事性，像在给朋友分享一个有趣的发现",
        "专业": "语气专业、客观，像自然纪录片旁白",
        "幽默": "语气轻松幽默，带有趣味性的解说"
    }
    
    prompt = f"""你是一个专业的自然纪录片旁白撰稿人。
根据以下视频分析结果，撰写一段 Vlog 旁白脚本。

分析结果：
{summary}

要求：
1. 脚本长度 150-250 字
2. 风格: {style_guide.get(style, style_guide["温馨"])}
3. 突出精彩镜头（highlight_score 高的场景）
4. 使用中文
5. 包含开场白和结尾

只返回脚本文本，不要其他内容。"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048
    )
    
    return response.choices[0].message.content.strip()


def generate_script_with_segments(
    analysis_results: list[dict],
    style: str = "温馨",
    expected_bird: str = None,
    target_duration: float = None
) -> tuple[str, list[dict]]:
    """生成带片段对应的故事脚本
    
    Returns:
        (完整脚本文本, 片段字幕列表)
        片段字幕列表: [{"segment_index": 0, "text": "..."}, ...]
    """
    valid_results = [r for r in analysis_results if r.get("has_bird") or r.get("highlight_score", 0) > 3]
    
    if not valid_results:
        # 使用所有结果
        valid_results = analysis_results[:10]
    
    if not valid_results:
        default_text = "这是一段宁静的自然观察记录，让我们一起感受大自然的美好。"
        return default_text, [{"segment_index": 0, "text": default_text}]
    
    # 构建片段描述
    segment_descriptions = []
    for i, result in enumerate(valid_results):
        desc = result.get("description", "")
        bird_type = result.get("bird_type", "")
        activity = result.get("activity", "")
        
        segment_desc = f"片段{i+1}: "
        if bird_type:
            segment_desc += f"{bird_type}"
        if activity:
            segment_desc += f"正在{activity}"
        if desc:
            segment_desc += f"，{desc[:50]}"
        
        segment_descriptions.append(segment_desc)
    
    style_guide = {
        "温馨": "语气温馨、富有故事性，像在给朋友分享一个有趣的发现",
        "专业": "语气专业、客观，像自然纪录片旁白",
        "幽默": "语气轻松幽默，带有趣味性的解说"
    }
    
    prompt = f"""你是一个专业的自然纪录片旁白撰稿人。
根据以下视频片段描述，撰写一段有故事性的 Vlog 旁白脚本。

片段描述：
{chr(10).join(segment_descriptions)}

要求：
1. 为每个片段生成对应的旁白句子
2. 脚本要有整体故事性，有起承转合
3. 风格: {style_guide.get(style, style_guide["温馨"])}
4. 使用中文
{f'5. 重点突出主角: {expected_bird}' if expected_bird else ''}
{f'6. 脚本总时长大约需要匹配: {target_duration}秒（语速约为每秒 4-5 个字）' if target_duration else ''}

请按以下 JSON 格式返回：
{{
    "full_script": "完整的旁白脚本（连贯的故事）",
    "segments": [
        {{"segment_index": 0, "text": "对应片段1的旁白句子"}},
        {{"segment_index": 1, "text": "对应片段2的旁白句子"}},
        ...
    ]
}}

只返回 JSON，不要其他内容。"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048
    )
    
    content = response.choices[0].message.content.strip()
    
    # 尝试解析 JSON
    try:
        # 提取 JSON 部分
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            full_script = result.get("full_script", "")
            segments = result.get("segments", [])
            
            # 确保每个片段都有字幕
            if len(segments) < len(valid_results):
                # 补充缺少的片段
                for i in range(len(segments), len(valid_results)):
                    segments.append({
                        "segment_index": i,
                        "text": segment_descriptions[i] if i < len(segment_descriptions) else ""
                    })
            
            # 按 segment_index 排序，确保顺序正确
            segments.sort(key=lambda x: x.get("segment_index", 0))
            
            return full_script, segments
    except json.JSONDecodeError:
        pass
    
    # 解析失败，回退到简单模式
    simple_script = generate_script(analysis_results, style)
    # 均匀分配字幕
    sentences = re.split(r'[。！？]', simple_script)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    segments = []
    for i in range(len(valid_results)):
        if i < len(sentences):
            segments.append({"segment_index": i, "text": sentences[i]})
        else:
            segments.append({"segment_index": i, "text": ""})
    
    return simple_script, segments


def generate_subtitles(script: str, duration: float) -> list[dict]:
    """根据脚本生成字幕时间轴（通用版本）"""
    sentences = re.split(r'[。！？]', script)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [{"start": 0.0, "end": duration, "text": script}]
    
    time_per_sentence = duration / len(sentences)
    subtitles = []
    current_time = 0.0
    
    for sentence in sentences:
        subtitles.append({"start": current_time, "end": current_time + time_per_sentence, "text": sentence})
        current_time += time_per_sentence
    
    return subtitles


def generate_subtitles_for_segments(
    segments: list[dict],
    clip_durations: list[float]
) -> list[dict]:
    """根据片段字幕和时长生成 SRT 格式的字幕列表
    
    注意：segments 和 clip_durations 必须按相同顺序排列
    
    Args:
        segments: [{"segment_index": 0, "text": "..."}, ...] 或 [{"text": "..."}, ...]
        clip_durations: 每个片段的时长列表
        
    Returns:
        [{"start": 0.0, "end": 5.0, "text": "..."}, ...]
    """
    subtitles = []
    current_time = 0.0
    
    # 直接按顺序匹配，不依赖 segment_index
    for i, duration in enumerate(clip_durations):
        text = ""
        if i < len(segments):
            text = segments[i].get("text", "")
        
        if text:
            subtitles.append({
                "start": current_time,
                "end": current_time + duration,
                "text": text
            })
        
        current_time += duration
    
    return subtitles


def format_srt_time(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def save_srt(subtitles: list[dict], output_path: str) -> str:
    """将字幕列表保存为 SRT 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(subtitles, 1):
            start_time = format_srt_time(sub["start"])
            end_time = format_srt_time(sub["end"])
            text = sub["text"]
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")
    
    return output_path
