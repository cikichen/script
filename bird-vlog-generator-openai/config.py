"""配置文件 - OpenAI GPT-4o 版本"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # 可选：自定义 API 地址

# AWS 配置（用于 Polly 语音合成）
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
POLLY_VOICE_ID = os.getenv("POLLY_VOICE_ID", "Zhiyu")  # 中文女声

# 帧采样配置
FRAME_SAMPLE_INTERVAL = int(os.getenv("FRAME_SAMPLE_INTERVAL", "30"))  # 采样间隔（秒）
MAX_FRAMES_PER_VIDEO = int(os.getenv("MAX_FRAMES_PER_VIDEO", "3"))  # 每视频最大帧数

# 输出配置
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
