import cv2
import numpy as np
import time
import pyautogui
from hand_tracking_module import HandDetector
from gesture_controller import (
    GestureController,
    GESTURE_LABELS,
    GESTURE_COLORS,
    GESTURE_MOVE,
    GESTURE_DRAG,
    GESTURE_SCROLL,
    GESTURE_IDLE,
    GESTURE_UNKNOWN,
    GESTURE_LEFT_CLICK,
    GESTURE_RIGHT_CLICK,
)
from utils import map_coordinates, smooth

CAM_WIDTH = 640
CAM_HEIGHT = 480
FRAME_REDUCTION = 100
SMOOTHING_FACTOR = 5
SCREEN_W, SCREEN_H = pyautogui.size()

def draw_rounded_rect(img, pt1, pt2, color, thickness, radius=15, fill=False):
    x1, y1 = pt1
    x2, y2 = pt2
    if fill:
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, cv2.FILLED)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, cv2.FILLED)
        cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, cv2.FILLED)
        cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, cv2.FILLED)
        cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, cv2.FILLED)
        cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, cv2.FILLED)
    else:
        cv2.line(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
        cv2.line(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
        cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness)
        cv2.line(img, (x2, y1 + radius), (x2, y2 - radius), color, thickness)
        cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)
        cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)

def draw_overlay(img, gesture, action_detail, fps, controller):
    h, w, _ = img.shape
    color = GESTURE_COLORS.get(gesture, (255, 255, 255))
    dash_len = 10
    for i in range(FRAME_REDUCTION, w - FRAME_REDUCTION, dash_len * 2):
        cv2.line(img, (i, FRAME_REDUCTION), (min(i + dash_len, w - FRAME_REDUCTION), FRAME_REDUCTION), (80, 80, 80), 1)
        cv2.line(img, (i, h - FRAME_REDUCTION), (min(i + dash_len, w - FRAME_REDUCTION), h - FRAME_REDUCTION), (80, 80, 80), 1)
    for i in range(FRAME_REDUCTION, h - FRAME_REDUCTION, dash_len * 2):
        cv2.line(img, (FRAME_REDUCTION, i), (FRAME_REDUCTION, min(i + dash_len, h - FRAME_REDUCTION)), (80, 80, 80), 1)
        cv2.line(img, (w - FRAME_REDUCTION, i), (w - FRAME_REDUCTION, min(i + dash_len, h - FRAME_REDUCTION)), (80, 80, 80), 1)
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 40), (20, 20, 20), cv2.FILLED)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)
    cv2.putText(img, "AI Virtual Mouse", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    fps_text = f"FPS {int(fps)}"
    fps_color = (0, 255, 0) if fps > 20 else (0, 255, 255) if fps > 10 else (0, 0, 255)
    cv2.putText(img, fps_text, (w - 90, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, fps_color, 1, cv2.LINE_AA)
    card_h = 70
    overlay2 = img.copy()
    cv2.rectangle(overlay2, (10, h - card_h - 10), (w - 10, h - 10), (30, 30, 30), cv2.FILLED)
    cv2.addWeighted(overlay2, 0.75, img, 0.25, 0, img)
    cv2.rectangle(img, (10, h - card_h - 10), (16, h - 10), color, cv2.FILLED)
    label = GESTURE_LABELS.get(gesture, "...")
    cv2.putText(img, label, (28, h - card_h + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
    if action_detail:
        cv2.putText(img, action_detail, (28, h - card_h + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
    click_type = controller.has_click_feedback()
    if click_type:
        elapsed = time.time() - controller.click_feedback_time
        alpha = max(0, 1.0 - elapsed / 0.3)
        radius = int(30 + elapsed * 100)
        feedback_color = (0, 255, 0) if click_type == "LEFT" else (0, 165, 255)
        thickness = max(1, int(3 * alpha))
        cv2.circle(img, (w // 2, h // 2), radius, feedback_color, thickness)
        click_label = "LEFT CLICK!" if click_type == "LEFT" else "RIGHT CLICK!"
        cv2.putText(img, click_label, (w // 2 - 80, h // 2 - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (feedback_color[0], feedback_color[1], feedback_color[2]), 2, cv2.LINE_AA)
    cv2.putText(img, "Tekan 'q' untuk keluar", (w - 200, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 120, 120), 1, cv2.LINE_AA)
    return img

def draw_finger_status(img, fingers):
    if not fingers or len(fingers) != 5:
        return img
    h, w, _ = img.shape
    start_x = w - 135
    start_y = 50
    overlay = img.copy()
    cv2.rectangle(overlay, (start_x - 8, start_y - 5), (start_x + 118, start_y + 55), (30, 30, 30), cv2.FILLED)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)
    finger_names = ["Jmp", "Tel", "Tgh", "Mns", "Klg"]
    for i, (name, status) in enumerate(zip(finger_names, fingers)):
        x = start_x + i * 23
        color = (0, 255, 100) if status else (60, 60, 60)
        bar_h = 28 if status else 10
        cv2.rectangle(img, (x, start_y + 32 - bar_h), (x + 16, start_y + 32), color, cv2.FILLED)
        label_color = (200, 200, 200) if status else (80, 80, 80)
        cv2.putText(img, name[0], (x + 3, start_y + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.3, label_color, 1, cv2.LINE_AA)
    return img

def draw_gesture_guide(img):
    h, w, _ = img.shape
    guides = [
        ("Telunjuk", "Gerak kursor"),
        ("Telunjuk tekuk", "Klik kiri"),
        ("Pinch", "Klik kiri"),
        ("Dua jari", "Scroll"),
        ("Kepalan", "Drag"),
    ]
    overlay = img.copy()
    cv2.rectangle(overlay, (8, 48), (235, 48 + len(guides) * 22 + 10), (20, 20, 20), cv2.FILLED)
    cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
    cv2.putText(img, "Panduan Gesture:", (14, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1, cv2.LINE_AA)
    for i, (gesture, action) in enumerate(guides):
        y = 86 + i * 22
        cv2.putText(img, f"{gesture}", (14, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(img, f"= {action}", (140, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 150), 1, cv2.LINE_AA)
    return img

def main():
    print("=" * 50)
    print("  AI Virtual Mouse — Starting...")
    print(f"  Screen: {SCREEN_W}x{SCREEN_H}")
    print(f"  Camera: {CAM_WIDTH}x{CAM_HEIGHT}")
    print(f"  Frame Reduction: {FRAME_REDUCTION}px")
    print(f"  Smoothing: {SMOOTHING_FACTOR}")
    print("=" * 50)
    print()
    print("  Gesture Utama:")
    print("    Telunjuk lurus     → Gerak kursor")
    print("    Telunjuk tekuk     → Klik kiri")
    print("    Jempol + Telunjuk  → Klik kiri (Pinch)")
    print("    Dua jari terbuka   → Scroll")
    print("    Kepalan            → Drag")
    print("    Tangan terbuka     → Pause")
    print()
    print("  Shortcut Windows:")
    print("    3 Jari Swipe       → Alt+Tab / Task View / Desktop")
    print("    4 Jari Swipe       → Virtual Desktop / Max / Min")
    print("    Jempol + Kelingking→ Volume")
    print("    Kelingking saja    → Screenshot")
    print()
    print("  Tekan 'q' untuk keluar.")
    print("  Fail-safe: gerak mouse ke pojok layar.")
    print()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    if not cap.isOpened():
        print("[ERROR] Tidak bisa membuka kamera!")
        return
    detector = HandDetector(mode=False, max_hands=1, detection_con=0.7, track_con=0.7)
    controller = GestureController()
    prev_x, prev_y = SCREEN_W // 2, SCREEN_H // 2
    prev_time = time.time()
    fps = 0
    action_detail = ""
    current_fingers = [0, 0, 0, 0, 0]
    prev_gesture = GESTURE_UNKNOWN
    no_hand_frames = 0
    print("[OK] Kamera terbuka. Mulai tracking...\n")
    while True:
        success, img = cap.read()
        if not success:
            continue
        img = cv2.flip(img, 1)
        img = detector.find_hands(img)
        landmarks = detector.find_position(img)
        if len(landmarks) > 0:
            no_hand_frames = 0
            current_fingers = detector.fingers_up()
            gesture = controller.detect_gesture(current_fingers, landmarks, detector)
            if gesture != prev_gesture:
                if prev_gesture == GESTURE_SCROLL:
                    controller.reset_scroll()
                controller.swipe_tracker.reset()
                prev_gesture = gesture
            screen_x, screen_y = prev_x, prev_y
            if gesture in (GESTURE_MOVE, GESTURE_DRAG):
                if gesture == GESTURE_MOVE:
                    finger_x = landmarks[8][1]
                    finger_y = landmarks[8][2]
                else:
                    center = detector.get_hand_center()
                    if center:
                        finger_x, finger_y = center
                    else:
                        finger_x, finger_y = landmarks[8][1], landmarks[8][2]
                raw_x, raw_y = map_coordinates(finger_x, finger_y, CAM_WIDTH, CAM_HEIGHT, SCREEN_W, SCREEN_H, FRAME_REDUCTION)
                screen_x, screen_y = smooth(raw_x, raw_y, prev_x, prev_y, SMOOTHING_FACTOR)
                prev_x, prev_y = screen_x, screen_y
            hand_center = detector.get_hand_center()
            result = controller.execute_gesture(gesture, detector, screen_x=screen_x, screen_y=screen_y, hand_center=hand_center)
            if result.get("detail"):
                action_detail = result["detail"]
        else:
            no_hand_frames += 1
            if no_hand_frames > 10:
                controller._end_drag()
                controller.reset_scroll()
                controller.swipe_tracker.reset()
                current_fingers = [0, 0, 0, 0, 0]
                controller.current_gesture = GESTURE_UNKNOWN
                controller.confirmed_gesture = GESTURE_UNKNOWN
                action_detail = "Arahkan tangan ke kamera..."
        current_time = time.time()
        dt = current_time - prev_time
        fps = 1 / dt if dt > 0 else 0
        prev_time = current_time
        active_gesture = controller.confirmed_gesture
        img = draw_overlay(img, active_gesture, action_detail, fps, controller)
        img = draw_finger_status(img, current_fingers)
        if active_gesture in (GESTURE_IDLE, GESTURE_UNKNOWN):
            img = draw_gesture_guide(img)
        cv2.imshow("AI Virtual Mouse", img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[EXIT] Program dihentikan oleh user.")
            break
    controller._end_drag()
    detector.close()
    cap.release()
    cv2.destroyAllWindows()
    print("[OK] Kamera ditutup. Selesai.")

if __name__ == "__main__":
    main()
