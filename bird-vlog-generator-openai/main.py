#!/usr/bin/env python3
"""观鸟 Vlog 一键生成器 - 主程序（支持多视频 + 动态片段）"""

import os
import sys
import json
import argparse
import glob
from datetime import datetime

from tqdm import tqdm
from config import OUTPUT_DIR, HIGHLIGHT_MIN_SCORE
from modules.frame_sampler import extract_keyframes, get_video_duration
from modules.bedrock_analyzer import batch_analyze, filter_highlights
from modules.script_generator import generate_script, generate_script_with_segments, generate_subtitles, generate_subtitles_for_segments, save_srt
from modules.polly_tts import text_to_speech
from modules.video_composer import compose_video, create_slideshow, compose_from_highlights


def get_video_files(input_path: str) -> list[str]:
    """获取输入路径中的所有视频文件"""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')
    
    if os.path.isfile(input_path):
        return [input_path]
    elif os.path.isdir(input_path):
        videos = []
        for ext in video_extensions:
            videos.extend(glob.glob(os.path.join(input_path, f'*{ext}')))
            videos.extend(glob.glob(os.path.join(input_path, f'*{ext.upper()}')))
        return sorted(videos)
    else:
        raise ValueError(f"路径不存在: {input_path}")




def generate_vlog(
    input_path: str,
    output_dir: str = None,
    style: str = "温馨",
    mode: str = "video",
    merge: bool = False,
    birds: str = None,
    duration: float = None,
    workers: int = 5
) -> str:
    """一键生成观鸟 Vlog"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    
    video_files = get_video_files(input_path)
    if not video_files:
        raise ValueError(f"未找到视频文件: {input_path}")
    
    print("=" * 50)
    print("🐦 观鸟 Vlog 一键生成器")
    print("=" * 50)
    print(f"输入: {input_path}")
    print(f"发现 {len(video_files)} 个视频文件")
    if birds:
        print(f"主角: {birds}")
    if duration:
        print(f"目标时长: {duration}秒")
    print()
    
    if merge and len(video_files) > 1:
        return generate_merged_vlog(video_files, output_dir, style, mode, birds, duration, workers)
    else:
        results = []
        for i, video in enumerate(video_files):
            print(f"\n{'='*50}")
            print(f"处理视频 [{i+1}/{len(video_files)}]: {os.path.basename(video)}")
            print(f"{'='*50}\n")
            result = process_single_video(video, output_dir, style, mode, birds, duration, workers)
            results.append(result)
        
        if len(results) == 1:
            return results[0]
        else:
            print(f"\n✅ 全部完成！共生成 {len(results)} 个 Vlog")
            return output_dir


def process_single_video(
    input_video: str,
    output_dir: str,
    style: str,
    mode: str,
    birds: str = None,
    duration: float = None,
    workers: int = 5
) -> str:
    """处理单个视频"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_name = os.path.splitext(os.path.basename(input_video))[0]
    work_dir = os.path.join(output_dir, f"vlog_{video_name}_{timestamp}")
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"输出目录: {work_dir}")
    print()
    
    # 1. 提取关键帧
    print("📷 步骤 1/5: 提取关键帧...")
    frames_dir = os.path.join(work_dir, "frames")
    frame_infos = extract_keyframes(input_video, frames_dir)
    print(f"  ✓ 提取了 {len(frame_infos)} 帧")
    print()
    
    pbar = tqdm(total=len(frame_infos), desc="🤖 AI 视觉分析", unit="frame")
    def progress(current, total):
        pbar.update(1)
    
    analysis_results = batch_analyze(frame_infos, max_workers=workers, progress_callback=progress)
    pbar.close()
    print()
    
    # 保存分析结果
    analysis_file = os.path.join(work_dir, "analysis.json")
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    
    highlights = filter_highlights(analysis_results, min_score=HIGHLIGHT_MIN_SCORE)
    print(f"  ✓ 分析完成，发现 {len(highlights)} 个精彩片段")
    print()
    
    # 3. 生成脚本
    print("📝 步骤 3/5: 生成故事脚本...")
    script, segment_subtitles = generate_script_with_segments(
        analysis_results, style=style, expected_bird=birds, target_duration=duration
    )
    
    script_file = os.path.join(work_dir, "script.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    
    print(f"  ✓ 脚本生成完成 ({len(script)} 字)")
    print()
    
    # 4. 语音合成
    print("🎙️ 步骤 4/5: 语音合成...")
    audio_path = os.path.join(work_dir, "narration.mp3")
    text_to_speech(script, audio_path)
    print(f"  ✓ 语音合成完成")
    print()
    
    # 获取音频时长
    import subprocess
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            capture_output=True, text=True
        )
        audio_duration = float(result.stdout.strip())
    except:
        audio_duration = 10.0
    
    # 生成字幕
    num_clips = len(analysis_results)
    clip_duration = audio_duration / num_clips if num_clips > 0 else 5.0
    subtitles = generate_subtitles_for_segments(segment_subtitles, [clip_duration] * num_clips)
    srt_path = os.path.join(work_dir, "subtitles.srt")
    save_srt(subtitles, srt_path)
    

    # 5. 视频合成
    print("🎬 步骤 5/5: 视频合成...")
    output_path = os.path.join(work_dir, "vlog.mp4")
    
    if mode == "slideshow":
        create_slideshow(frame_infos, audio_path, output_path, subtitle_text=script[:100])
    else:
        # 修正参数：去掉 analysis_results，保持与函数定义一致
        compose_video(input_video, audio_path, output_path, 
                      subtitle_file=srt_path)
    
    print(f"  ✓ 视频合成完成")
    print()
    
    return output_path


def generate_merged_vlog(
    video_files: list[str],
    output_dir: str,
    style: str,
    mode: str,
    birds: str = None,
    duration: float = None,
    workers: int = 5
) -> str:
    """将多个视频合并为一个精彩 Vlog"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = os.path.join(output_dir, f"vlog_merged_{timestamp}")
    os.makedirs(work_dir, exist_ok=True)
    
    print(f"输出目录: {work_dir}")
    print()
    
    all_frame_infos = []
    
    # 1. 从所有视频提取关键帧
    print("📷 步骤 1/5: 提取所有视频的关键帧...")
    frames_dir = os.path.join(work_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    for i, video in enumerate(video_files):
        print(f"  处理 [{i+1}/{len(video_files)}]: {os.path.basename(video)}")
        video_frames_dir = os.path.join(frames_dir, f"video_{i:03d}")
        frame_infos = extract_keyframes(video, video_frames_dir)
        all_frame_infos.extend(frame_infos)
    
    print(f"  ✓ 共提取 {len(all_frame_infos)} 帧")
    print()
    
    # 2. AI 视觉分析
    print("🤖 步骤 2/5: AI 视觉分析...")
    pbar = tqdm(total=len(all_frame_infos), desc="🤖 AI 视觉分析", unit="frame")
    def progress(current, total):
        pbar.update(1)
    
    all_analysis = batch_analyze(all_frame_infos, max_workers=workers, progress_callback=progress)
    pbar.close()
    print()
    
    # 保存分析结果
    analysis_file = os.path.join(work_dir, "analysis.json")
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(all_analysis, f, ensure_ascii=False, indent=2)
    
    # 筛选可用片段 (动态升降级筛选策略)
    # 1. 优先尝试使用配置的高分阈值 (默认 7)
    usable_clips = [r for r in all_analysis if r.get("highlight_score", 0) >= HIGHLIGHT_MIN_SCORE and r.get("video_path")]
    
    # 2. 如果高分片段太少 (少于 3 个)，尝试降级到 4 分 (普通素材)
    if len(usable_clips) < 3:
        usable_clips = [r for r in all_analysis if r.get("highlight_score", 0) >= 4 and r.get("video_path")]
        
    # 3. 如果依然没有，则保底使用所有有视频路径的片段
    if not usable_clips:
        usable_clips = [r for r in all_analysis if r.get("video_path")]
    
    if not usable_clips:
        usable_clips = all_frame_infos
    
    print(f"  ✓ 分析完成，将使用 {len(usable_clips)} 个片段")
    print()
    
    # 3. 生成脚本（带片段对应）
    print("📝 步骤 3/5: 生成故事脚本...")
    script, segment_subtitles = generate_script_with_segments(
        usable_clips, style=style, expected_bird=birds, target_duration=duration
    )
    
    script_file = os.path.join(work_dir, "script.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    
    print(f"  ✓ 脚本生成完成 ({len(script)} 字)")
    print(f"  ✓ 已为 {len(segment_subtitles)} 个片段生成对应字幕")
    print()
    
    # 4. 逐段语音合成 (解决音画同步的关键)
    print("🎙️ 步骤 4/5: 逐段旁白合成 (确保音画完美匹配)...")
    temp_audio_dir = os.path.join(work_dir, "temp_audio")
    os.makedirs(temp_audio_dir, exist_ok=True)
    
    audio_segments = []
    clip_durations = []
    
    for i, seg in enumerate(tqdm(segment_subtitles, desc="🎙️ 旁白合成", unit="seg")):
        text = seg.get("text", "")
        if not text:
            # 如果某片段没有旁白，给一个默认时长（如 3 秒）
            clip_durations.append(3.0)
            continue
            
        seg_audio_path = os.path.abspath(os.path.join(temp_audio_dir, f"seg_{i:03d}.mp3"))
        text_to_speech(text, seg_audio_path)
        
        # 获取该段语音的时长
        from modules.polly_tts import get_audio_duration
        seg_duration = get_audio_duration(seg_audio_path)
        
        audio_segments.append(seg_audio_path)
        clip_durations.append(seg_duration)
    
    # 合并所有音频
    audio_path = os.path.abspath(os.path.join(work_dir, "narration.mp3"))
    audio_list_file = os.path.abspath(os.path.join(temp_audio_dir, "audio_list.txt"))
    with open(audio_list_file, 'w', encoding='utf-8') as f:
        for seg_audio in audio_segments:
            # 使用绝对路径，并转义单引号以防路径包含特殊字符
            safe_path = seg_audio.replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
            
    try:
        import subprocess
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', audio_list_file, '-c', 'copy', audio_path
        ], capture_output=True, check=True)
    except Exception as e:
        print(f"  音频合并失败: {e}，回退到整体合成模式")
        text_to_speech(script, audio_path)
    
    print(f"  ✓ 语音合成完成")
    print()
    
    # 生成 SRT 字幕文件
    subtitles = generate_subtitles_for_segments(segment_subtitles, clip_durations)
    srt_path = os.path.join(work_dir, "subtitles.srt")
    save_srt(subtitles, srt_path)
    print(f"  ✓ 字幕完成，已根据旁白动态调整时间轴")
    
    # 保存调试信息
    debug_file = os.path.join(work_dir, "debug_segments.json")
    with open(debug_file, "w", encoding="utf-8") as f:
        json.dump({
            "usable_clips_count": len(usable_clips),
            "segment_subtitles_count": len(segment_subtitles),
            "subtitles_count": len(subtitles),
            "clip_durations": clip_durations,
            "segment_subtitles": segment_subtitles
        }, f, ensure_ascii=False, indent=2)
    print()

    # 5. 视频合成
    print("🎬 步骤 5/5: 视频合成 (采用动态时长模式)...")
    output_path = os.path.join(work_dir, "vlog.mp4")
    
    if mode == "slideshow":
        create_slideshow(all_frame_infos, audio_path, output_path, subtitle_text=script[:100])
    else:
        # 这里传递具体的时长列表给视频合成模块
        compose_from_highlights(usable_clips, audio_path, output_path, 
                                 clip_duration=clip_durations, subtitle_file=srt_path)
    
    print(f"  ✓ 视频合成完成")
    print()
    
    print("=" * 50)
    print(f"✅ 合并生成完成!")
    print(f"📁 输出目录: {work_dir}")
    print(f"🎥 成品视频: {output_path}")
    print("=" * 50)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="观鸟 Vlog 一键生成器 - 使用 AI 自动分析并生成观鸟视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py video.mp4                    # 处理单个视频
  python main.py ./videos/ --merge            # 合并为动态 Vlog
  python main.py ./videos/ --merge --birds "翠鸟" --duration 60
  python main.py ./videos/ --merge --workers 10  # 使用 10 线程并行分析
        """
    )
    
    parser.add_argument("input", help="输入视频路径或目录")
    parser.add_argument("-o", "--output", help="输出目录", default=OUTPUT_DIR)
    parser.add_argument("-s", "--style", help="脚本风格", 
                        choices=["温馨", "专业", "幽默"], default="温馨")
    parser.add_argument("-m", "--mode", help="输出模式",
                        choices=["video", "slideshow"], default="video")
    parser.add_argument("--merge", action="store_true",
                        help="将多个视频合并为一个 Vlog")
    parser.add_argument("--birds", "--bird", help="指定预期观察到的鸟类名称")
    parser.add_argument("--duration", type=float, help="设置目标 Vlog 理想时长（秒）")
    parser.add_argument("--workers", type=int, default=5, help="AI 分析并行线程数 (默认: 5)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 路径不存在: {args.input}")
        sys.exit(1)
    
    try:
        generate_vlog(
            input_path=args.input,
            output_dir=args.output,
            style=args.style,
            mode=args.mode,
            merge=args.merge,
            birds=args.birds,
            duration=args.duration,
            workers=args.workers
        )
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
