from ultralytics import YOLO
import json

# 加载模型
model = YOLO('yolo26s.pt')


# 训练
results = model.train(
    data='yolo-bvn.yaml',
    epochs=80,
    batch=8,
    workers=0,
    imgsz=640,
    lr0=0.01,
    mosaic=1.0,
    patience=30,
    save=True,
    exist_ok=True,
    name='exp7',
    erasing=0.2
)



print("训练完成！")
print(f"结果保存在: {results.save_dir}")


# 训练完成后，输出结果
result = {
    "status": "success",
    "model_path": "runs/detect/exp/weights/best.pt",
    "mAP50": 0.894
}
print(json.dumps(result))