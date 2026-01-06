# 观鸟 Vlog 一键生成器

基于 Amazon Bedrock (Claude 3.5 Sonnet) + AWS Polly + FFmpeg 实现观鸟视频自动剪辑。

## 快速开始（Docker 部署）

### 1. 配置 AWS 凭证

```bash
cp .env.example .env
# 编辑 .env 填入你的 AWS 凭证
```

### 2. 构建镜像

```bash
docker compose build
```

### 3. 运行

```bash
# 将视频放入 input 目录
mkdir -p input output
cp 你的视频.mp4 input/

# 运行生成
docker compose run --rm bird-vlog /app/input/你的视频.mp4
```

### 4. 查看输出

生成的 Vlog 在 `output/` 目录下。

---

## 直接部署（无 Docker）

### 1. 安装依赖

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg

# CentOS/RHEL
sudo yum install -y python3 python3-pip ffmpeg
```

### 2. 安装 Python 依赖

```bash
pip3 install -r requirements.txt
```

### 3. 配置 AWS

```bash
pip3 install awscli
aws configure
```

### 4. 运行

```bash
python3 main.py 视频.mp4
```

---

## 配置说明

编辑 `config.py` 自定义参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `AWS_REGION` | AWS 区域 | `us-east-1` |
| `BEDROCK_MODEL_ID` | Bedrock 模型 | Claude 3.5 Sonnet |
| `POLLY_VOICE_ID` | 语音角色 | `Zhiyu` (中文女声) |
| `FRAME_SAMPLE_INTERVAL` | 关键帧间隔(秒) | `30` |
| `MAX_FRAMES_PER_VIDEO` | 最大提取帧数 | `20` |

---

## 命令参数

```bash
python main.py <视频路径> [选项]

选项:
  -o, --output   输出目录 (默认: output)
  -s, --style    脚本风格: 温馨/专业/幽默 (默认: 温馨)
  -m, --mode     输出模式: video/slideshow (默认: video)
```
