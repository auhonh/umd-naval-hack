import cv2
from ultralytics import YOLO

# 1. Load the YOLO26 Nano model (auto-downloads 'yolo26n.pt' on first run)
model = YOLO('yolo26n.pt')

# 2. Initialize the camera (0 is usually the default USB webcam)
cap = cv2.VideoCapture(1)

# Lower the resolution to save Pi CPU cycles
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Starting YOLO26 boat detection... Press source venv/bin/activate'q' to quit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("Failed to grab frame. Exiting...")
        break

    # 3. Run inference
    # classes=[8] filters the detections to ONLY show the COCO "boat" class
    # imgsz=320 reduces the image matrix size, drastically speeding up the Pi
    # conf=0.5 ensures we only show confident detections
    results = model(frame, classes=[8], imgsz=320, conf=0.05)

    # 4. Draw the bounding boxes on the frame
    # YOLO26's plot() handles drawing the NMS-free boxes cleanly
    annotated_frame = results[0].plot()

    # 5. Display the output
    cv2.imshow("YOLO26 Nano Boat Detection (Pi 4)", annotated_frame)

    # Quit if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()