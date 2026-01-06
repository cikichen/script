"""鸟类检测模块 - 使用 YOLOv8"""

import os
from ultralytics import YOLO

# 全局模型实例（懒加载）
_model = None


def get_model():
    """获取或初始化 YOLO 模型"""
    global _model
    if _model is None:
        # 使用 YOLOv8n（最小最快的版本）
        # 首次运行会自动下载模型
        _model = YOLO('yolov8n.pt')
    return _model


def detect_bird(image_path: str, confidence: float = 0.3) -> dict:
    """检测图片中是否有鸟类
    
    Args:
        image_path: 图片路径
        confidence: 置信度阈值
        
    Returns:
        {
            "has_bird": bool,
            "bird_count": int,
            "confidence": float,  # 最高置信度
            "boxes": list  # 边界框列表
        }
    """
    model = get_model()
    
    # YOLO 检测
    results = model(image_path, verbose=False)
    
    # COCO 数据集中 bird 的类别 ID 是 14
    BIRD_CLASS_ID = 14
    
    bird_detections = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            if cls_id == BIRD_CLASS_ID and conf >= confidence:
                bird_detections.append({
                    "confidence": conf,
                    "box": box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                })
    
    return {
        "has_bird": len(bird_detections) > 0,
        "bird_count": len(bird_detections),
        "confidence": max([d["confidence"] for d in bird_detections]) if bird_detections else 0,
        "boxes": bird_detections
    }


def detect_bird_in_frame(frame, confidence: float = 0.3) -> dict:
    """检测 OpenCV 帧中是否有鸟类（不保存到磁盘）
    
    Args:
        frame: OpenCV 图像帧 (numpy array)
        confidence: 置信度阈值
        
    Returns:
        检测结果字典
    """
    model = get_model()
    
    # YOLO 可以直接接受 numpy array
    results = model(frame, verbose=False)
    
    BIRD_CLASS_ID = 14
    
    bird_detections = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            if cls_id == BIRD_CLASS_ID and conf >= confidence:
                bird_detections.append({
                    "confidence": conf,
                    "box": box.xyxy[0].tolist()
                })
    
    return {
        "has_bird": len(bird_detections) > 0,
        "bird_count": len(bird_detections),
        "confidence": max([d["confidence"] for d in bird_detections]) if bird_detections else 0,
        "boxes": bird_detections
    }


def batch_detect(image_paths: list[str], confidence: float = 0.3, progress_callback=None) -> list[dict]:
    """批量检测图片中的鸟类
    
    Args:
        image_paths: 图片路径列表
        confidence: 置信度阈值
        progress_callback: 进度回调函数 (current, total)
        
    Returns:
        检测结果列表
    """
    results = []
    total = len(image_paths)
    
    for i, path in enumerate(image_paths):
        if progress_callback:
            progress_callback(i + 1, total)
        
        try:
            result = detect_bird(path, confidence)
            result["path"] = path
            results.append(result)
        except Exception as e:
            results.append({
                "path": path,
                "has_bird": False,
                "bird_count": 0,
                "confidence": 0,
                "error": str(e)
            })
    
    return results


def filter_bird_frames(detection_results: list[dict]) -> list[dict]:
    """筛选出有鸟的帧"""
    return [r for r in detection_results if r.get("has_bird", False)]
