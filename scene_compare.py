import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def detect_objects(img) -> set:
    results = model(img, conf=0.5, verbose=False)
    objects = set()
    for r in results:
        for box in r.boxes:
            label = model.names[int(box.cls[0])]
            objects.add(label)
    return objects


def compare_scenes(ref_img, cmp_img) -> dict:
    ref_objects = detect_objects(ref_img)
    cmp_objects = detect_objects(cmp_img)

    missing = list(ref_objects - cmp_objects)
    added   = list(cmp_objects - ref_objects)

    return {
        "missing_objects":    missing,
        "added_objects":      added,
        "reference_objects":  list(ref_objects),
        "current_objects":    list(cmp_objects)
    }
