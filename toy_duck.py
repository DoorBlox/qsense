from ultralytics import YOLO
import cv2

print("Loading toy duck detector...")

# Open-vocabulary YOLO model
model = YOLO("yolov8s-world.pt")

# Tell the model what we want to detect
model.set_classes([
    "toy duck",
    "rubber duck",
    "yellow toy duck"
])

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Could not open webcam.")
    exit()

while True:

    ret, frame = cap.read()

    if not ret:
        print("ERROR: Could not read frame.")
        break

    results = model.predict(
        frame,
        conf=0.20,
        verbose=False
    )[0]

    duck_count = 0

    for box in results.boxes:

        confidence = float(box.conf[0])
        class_id = int(box.cls[0])

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        label_name = model.names[class_id]

        duck_count += 1

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"{label_name} {confidence:.2f}",
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    cv2.putText(
        frame,
        f"Toy ducks: {duck_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )

    cv2.imshow("Toy Duck Detector", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()