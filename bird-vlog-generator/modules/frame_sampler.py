"""关键帧提取模块 - 带 YOLO 鸟类检测"""

import cv2
import os
import sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FRAME_SAMPLE_INTERVAL, MAX_FRAMES_PER_VIDEO


def extract_keyframes(
    video_path: str,
    output_dir: str,
    method: str = "bird_detect",
    max_frames: int = 3  # 每个视频最多 3 帧（参考 Reli 方案）
) -> list[dict]:
    """从视频中提取关键帧
    
    Args:
        video_path: 输入视频路径
        output_dir: 输出目录
        method: 提取方法 
            - "simple": 等间隔抽帧
            - "smart": 场景变化+运动检测
            - "bird_detect": YOLO 鸟类检测（推荐）
        max_frames: 最大帧数
        
    Returns:
        关键帧信息列表 [{"path": str, "timestamp": float, "video_path": str, ...}, ...]
    """
    if max_frames is None:
        max_frames = MAX_FRAMES_PER_VIDEO
    
    if method == "simple":
        return extract_keyframes_simple(video_path, output_dir, max_frames)
    elif method == "smart":
        return extract_keyframes_smart(video_path, output_dir, max_frames)
    else:
        return extract_keyframes_with_bird_detection(video_path, output_dir, max_frames)


def extract_keyframes_simple(video_path: str, output_dir: str, max_frames: int = 20) -> list[dict]:
    """简单等间隔抽帧"""
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"  视频信息: {duration:.1f}秒, {fps:.1f}fps, {total_frames}帧")
    
    frame_interval = int(fps * FRAME_SAMPLE_INTERVAL)
    if frame_interval <= 0:
        frame_interval = 30
    
    frame_infos = []
    frame_count = 0
    saved_count = 0
    
    while cap.isOpened() and saved_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            path = os.path.join(output_dir, f"frame_{saved_count:04d}_t{int(timestamp)}.jpg")
            cv2.imwrite(path, frame)
            frame_infos.append({
                "path": path,
                "timestamp": timestamp,
                "video_path": video_path,
                "frame_index": saved_count
            })
            saved_count += 1
        
        frame_count += 1
    
    cap.release()
    return frame_infos


def extract_keyframes_with_bird_detection(
    video_path: str,
    output_dir: str,
    max_frames: int = 20,
    sample_interval: float = 5.0,  # 每 5 秒检测一次
    confidence: float = 0.25
) -> list[dict]:
    """使用 YOLO 检测鸟类，只保留有鸟的帧
    
    流程：
    1. 每 sample_interval 秒取一帧
    2. 用 YOLO 检测是否有鸟
    3. 只保留有鸟的帧
    4. 如果有鸟的帧超过 max_frames，按置信度排序取 top
    """
    from modules.bird_detector import detect_bird_in_frame
    
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"  视频信息: {duration:.1f}秒, {fps:.1f}fps, {total_frames}帧")
    
    frame_interval = int(fps * sample_interval)
    if frame_interval <= 0:
        frame_interval = int(fps * 5)
    
    # 收集所有候选帧
    candidates = []  # [(frame_idx, timestamp, frame, confidence, bird_count)]
    frame_count = 0
    checked_count = 0
    
    print(f"  🔍 YOLO 鸟类检测中...")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            checked_count += 1
            timestamp = frame_count / fps
            
            # YOLO 检测
            result = detect_bird_in_frame(frame, confidence=confidence)
            
            if result["has_bird"]:
                candidates.append({
                    "frame_idx": frame_count,
                    "timestamp": timestamp,
                    "frame": frame.copy(),
                    "confidence": result["confidence"],
                    "bird_count": result["bird_count"]
                })
                print(f"    ✓ 发现鸟类 @ {timestamp:.1f}s (置信度: {result['confidence']:.2f})", end="\r")
        
        frame_count += 1
    
    cap.release()
    print()
    
    print(f"  检查了 {checked_count} 帧，发现 {len(candidates)} 帧有鸟")
    
    # 如果没有检测到鸟，回退到等间隔抽帧
    if not candidates:
        print(f"  未检测到鸟类，使用等间隔抽帧...")
        return extract_keyframes_simple(video_path, output_dir, max_frames)
    
    # 按置信度排序，取 top max_frames
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    selected = candidates[:max_frames]
    
    # 按时间顺序排序
    selected.sort(key=lambda x: x["timestamp"])
    
    # 保存帧
    frame_infos = []
    for i, cand in enumerate(selected):
        path = os.path.join(output_dir, f"frame_{i:04d}_t{int(cand['timestamp'])}.jpg")
        cv2.imwrite(path, cand["frame"])
        frame_infos.append({
            "path": path,
            "timestamp": cand["timestamp"],
            "video_path": video_path,
            "frame_index": i,
            "bird_confidence": cand["confidence"],
            "bird_count": cand["bird_count"]
        })
    
    print(f"  ✓ 最终选择 {len(frame_infos)} 帧（有鸟）")
    
    return frame_infos


def extract_keyframes_smart(video_path: str, output_dir: str, max_frames: int = 20) -> list[dict]:
    """智能关键帧提取：场景变化+运动检测"""
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"  视频信息: {duration:.1f}秒, {fps:.1f}fps, {total_frames}帧")
    
    min_frame_gap = int(fps * 3)
    scene_threshold = 0.15
    motion_threshold = 5
    blur_threshold = 50
    
    candidates = []
    prev_frame = None
    prev_hist = None
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        scene_score = 0
        if prev_hist is not None:
            scene_score = 1 - cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
        
        motion_score = 0
        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            motion_score = np.mean(diff)
        
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        timestamp = frame_count / fps
        
        if blur_score > blur_threshold:
            total_score = scene_score * 0.4 + (motion_score / 100) * 0.4 + (blur_score / 1000) * 0.2
            
            if scene_score > scene_threshold or motion_score > motion_threshold:
                candidates.append((frame_count, total_score, frame.copy(), timestamp))
        
        prev_frame = gray.copy()
        prev_hist = hist
        frame_count += 1
    
    cap.release()
    
    print(f"  检测到 {len(candidates)} 个候选关键帧")
    
    selected_frames = select_distributed_frames(candidates, total_frames, min_frame_gap, max_frames)
    
    frame_infos = []
    for i, (frame_idx, score, frame, timestamp) in enumerate(selected_frames):
        path = os.path.join(output_dir, f"frame_{i:04d}_t{int(timestamp)}.jpg")
        cv2.imwrite(path, frame)
        frame_infos.append({
            "path": path,
            "timestamp": timestamp,
            "video_path": video_path,
            "frame_index": i,
            "score": score
        })
    
    print(f"  ✓ 最终选择 {len(frame_infos)} 帧")
    
    if len(frame_infos) < 3:
        print(f"  智能检测帧数不足，补充等间隔帧...")
        return extract_keyframes_simple(video_path, output_dir, max_frames)
    
    return frame_infos


def select_distributed_frames(candidates, total_frames, min_gap, max_count):
    """从候选帧中选择分布均匀的关键帧"""
    if not candidates:
        return []
    
    sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
    
    selected = []
    used_ranges = []
    
    for frame_idx, score, frame, timestamp in sorted_candidates:
        if len(selected) >= max_count:
            break
        
        too_close = False
        for used_idx in used_ranges:
            if abs(frame_idx - used_idx) < min_gap:
                too_close = True
                break
        
        if not too_close:
            selected.append((frame_idx, score, frame, timestamp))
            used_ranges.append(frame_idx)
    
    selected.sort(key=lambda x: x[0])
    return selected


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return total_frames / fps if fps > 0 else 0


def extract_clip(video_path: str, start_sec: float, end_sec: float, output_path: str) -> str:
    """提取视频片段"""
    import subprocess
    
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_sec),
        '-i', video_path,
        '-t', str(end_sec - start_sec),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'fast',
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    
    return output_path
