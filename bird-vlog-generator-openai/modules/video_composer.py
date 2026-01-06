"""视频合成模块 - 简化稳定版"""

import os
import subprocess
import tempfile
import shutil


def compose_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    subtitle_text: str = None,
    subtitle_file: str = None
) -> str:
    """合成最终 Vlog：原视频 + 旁白音频 + 字幕"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    if subtitle_file and os.path.exists(subtitle_file):
        safe_srt_path = subtitle_file.replace("\\", "/").replace(":", "\\:")
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-vf', f"subtitles='{safe_srt_path}':force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Alignment=2'",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
    elif subtitle_text:
        display_text = subtitle_text[:50] + "..." if len(subtitle_text) > 50 else subtitle_text
        display_text = display_text.replace("'", "\\'").replace(":", "\\:").replace('"', '\\"')
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-vf', f"drawtext=text='{display_text}':x=(w-text_w)/2:y=h-80:fontsize=28:fontcolor=white:borderw=2:bordercolor=black",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def compose_from_highlights(
    highlights: list[dict],
    audio_path: str,
    output_path: str,
    clip_duration: float | list[float] = None,  # None = 自动计算, 也可以是时长列表
    subtitle_file: str = None,
    subtitle_text: str = None,
    max_workers: int = 4
) -> str:
    """从精彩片段提取视频并合成 Vlog
    
    关键优化：
    1. 支持并行片段提取（大幅提升速度）
    2. 支持针对每个片段指定不同时长（配合逐段旁白）
    3. 添加 tqdm 进度条显示
    """
    if not highlights:
        raise ValueError("没有精彩片段")
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 1. 获取音频时长
        audio_duration = get_media_duration(audio_path)
        print(f"  音频总时长: {audio_duration:.1f}秒")
        
        # 2. 计算每个片段的时长
        num_clips = len(highlights)
        if clip_duration is None:
            avg_duration = audio_duration / num_clips
            durations = [avg_duration] * num_clips
        elif isinstance(clip_duration, list):
            durations = clip_duration
        else:
            durations = [clip_duration] * num_clips
        
        # 3. 提取视频片段（并行处理）
        print(f"  并行提取 {num_clips} 个视频片段 (线程数: {max_workers})...")
        clips = [None] * num_clips
        
        def extract_worker(index, highlight, duration):
            timestamp = highlight.get("timestamp", 0)
            video_path = highlight.get("video_path")
            
            if not video_path or not os.path.exists(video_path):
                return index, None
            
            start_time = max(0, timestamp - duration / 2)
            clip_path = os.path.join(temp_dir, f"clip_{index:04d}.mp4")
            
            is_first = (index == 0)
            is_last = (index == num_clips - 1)
            
            try:
                extract_clip_simple(
                    video_path, start_time, duration, clip_path,
                    fade_in=is_first, fade_out=is_last
                )
                return index, clip_path
            except Exception as e:
                print(f"    片段 {index} 提取失败: {e}")
                return index, None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(num_clips):
                futures.append(executor.submit(extract_worker, i, highlights[i], durations[i]))
            
            for future in tqdm(as_completed(futures), total=num_clips, desc="  提取进度", unit="clip"):
                idx, path = future.result()
                if path:
                    clips[idx] = path
        
        # 过滤提取失败的片段
        valid_clips = [c for c in clips if c is not None]
        
        if not valid_clips:
            raise ValueError("没有成功提取任何视频片段")
        
        if len(valid_clips) < num_clips:
            print(f"  警告: 有 {num_clips - len(valid_clips)} 个片段提取失败")
        
        # 4. 拼接视频
        print("  正在拼接视频片段...")
        merged_video = os.path.join(temp_dir, "merged.mp4")
        concat_videos(valid_clips, merged_video)
        
        # 5. 添加音频和字幕
        print("  正在压制字幕和音频...")
        add_audio_and_subtitle(merged_video, audio_path, output_path, subtitle_file, subtitle_text)
        
        return output_path
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def extract_clip_simple(
    video_path: str,
    start_sec: float,
    duration: float,
    output_path: str,
    fade_in: bool = False,
    fade_out: bool = False,
    fade_duration: float = 0.5
) -> str:
    """提取视频片段，可选首尾淡入淡出"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    scale = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1"
    
    # 构建滤镜链
    filters = [scale]
    if fade_in:
        filters.append(f"fade=t=in:st=0:d={fade_duration}")
    if fade_out:
        filters.append(f"fade=t=out:st={duration - fade_duration}:d={fade_duration}")
    
    vf = ",".join(filters)
    
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(max(0, start_sec)),
        '-i', video_path,
        '-t', str(duration),
        '-vf', vf,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-r', '30',
        '-c:a', 'aac',
        '-ar', '44100',
        '-ac', '2',
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def extract_clip_with_fade(
    video_path: str,
    start_sec: float,
    duration: float,
    output_path: str,
    fade_duration: float = 0.3
) -> str:
    """提取视频片段并添加淡入淡出效果（所有片段）"""
    return extract_clip_simple(
        video_path, start_sec, duration, output_path,
        fade_in=True, fade_out=True, fade_duration=fade_duration
    )


def concat_videos(clips: list[str], output_path: str) -> str:
    """简单拼接视频（使用 concat demuxer）"""
    temp_dir = os.path.dirname(output_path)
    list_file = os.path.join(temp_dir, "list.txt")
    
    with open(list_file, 'w') as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")
    
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        '-c', 'copy',
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def add_audio_and_subtitle(
    video_path: str,
    audio_path: str,
    output_path: str,
    subtitle_file: str = None,
    subtitle_text: str = None
) -> str:
    """添加音频和字幕"""
    if subtitle_file and os.path.exists(subtitle_file):
        safe_srt_path = subtitle_file.replace("\\", "/").replace(":", "\\:")
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-vf', f"subtitles='{safe_srt_path}':force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Alignment=2'",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]
    elif subtitle_text:
        display_text = subtitle_text[:60].replace("'", "\\'").replace(":", "\\:").replace('"', '\\"')
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-vf', f"drawtext=text='{display_text}':x=(w-text_w)/2:y=h-80:fontsize=24:fontcolor=white:borderw=2:bordercolor=black",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def get_media_duration(media_path: str) -> float:
    """获取媒体文件时长"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', media_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except:
        return 60.0


def create_slideshow(
    image_paths: list,
    audio_path: str,
    output_path: str,
    duration_per_image: float = None,
    subtitle_text: str = None
) -> str:
    """将图片序列创建为幻灯片视频"""
    if image_paths and isinstance(image_paths[0], dict):
        paths = [img.get("path", img) for img in image_paths]
    else:
        paths = image_paths
    
    if not paths:
        raise ValueError("图片列表为空")
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # 获取音频时长
    audio_duration = get_media_duration(audio_path)
    if duration_per_image is None:
        duration_per_image = audio_duration / len(paths)
    
    temp_dir = tempfile.mkdtemp()
    temp_videos = []
    fade_duration = 0.3
    
    try:
        for i, img_path in enumerate(paths):
            temp_video = os.path.join(temp_dir, f"clip_{i:04d}.mp4")
            
            fade_in = f"fade=t=in:st=0:d={fade_duration}"
            fade_out = f"fade=t=out:st={duration_per_image - fade_duration}:d={fade_duration}"
            scale = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"
            
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-i', img_path,
                '-c:v', 'libx264',
                '-t', str(duration_per_image),
                '-pix_fmt', 'yuv420p',
                '-vf', f"{scale},{fade_in},{fade_out}",
                '-r', '30',
                temp_video
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            temp_videos.append(temp_video)
        
        merged_video = os.path.join(temp_dir, "merged.mp4")
        concat_videos(temp_videos, merged_video)
        
        add_audio_and_subtitle(merged_video, audio_path, output_path, subtitle_text=subtitle_text)
        
        return output_path
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
