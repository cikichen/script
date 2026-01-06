"""语音合成模块 - 使用 Amazon Polly"""

import boto3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AWS_REGION, POLLY_VOICE_ID

polly = boto3.client("polly", region_name=AWS_REGION)

# 可用的中文语音
CHINESE_VOICES = {
    "Zhiyu": "中文女声（标准）",
    "Hiujin": "粤语女声",
}


def text_to_speech(text: str, output_path: str, voice_id: str = None) -> str:
    """将文本转为语音
    
    Args:
        text: 要转换的文本
        output_path: 输出音频文件路径
        voice_id: 语音 ID（默认使用配置中的语音）
        
    Returns:
        输出文件路径
    """
    if voice_id is None:
        voice_id = POLLY_VOICE_ID
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId=voice_id,
        Engine="neural",  # 使用神经网络引擎，效果更自然
        LanguageCode="cmn-CN"  # 中文普通话
    )
    
    with open(output_path, "wb") as f:
        f.write(response["AudioStream"].read())
    
    return output_path


def get_audio_duration(audio_path: str) -> float:
    """获取音频时长（秒）
    
    需要安装 mutagen: pip install mutagen
    """
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        return audio.info.length
    except ImportError:
        # 如果没有 mutagen，使用 ffprobe
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())


def synthesize_with_ssml(text: str, output_path: str, speed: str = "medium") -> str:
    """使用 SSML 合成语音（支持语速控制）
    
    Args:
        text: 文本内容
        output_path: 输出路径
        speed: 语速 (x-slow, slow, medium, fast, x-fast)
        
    Returns:
        输出文件路径
    """
    ssml_text = f"""<speak>
    <prosody rate="{speed}">
        {text}
    </prosody>
</speak>"""
    
    response = polly.synthesize_speech(
        Text=ssml_text,
        TextType="ssml",
        OutputFormat="mp3",
        VoiceId=POLLY_VOICE_ID,
        Engine="neural",
        LanguageCode="cmn-CN"
    )
    
    with open(output_path, "wb") as f:
        f.write(response["AudioStream"].read())
    
    return output_path
