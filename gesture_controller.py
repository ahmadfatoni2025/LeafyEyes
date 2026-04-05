import pyautogui
import time
from utils import CooldownManager, SwipeTracker

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0

GESTURE_IDLE = "idle"
GESTURE_MOVE = "move"
GESTURE_SCROLL = "scroll"
GESTURE_LEFT_CLICK = "left_click"
GESTURE_RIGHT_CLICK = "right_click"
GESTURE_DRAG = "drag"
GESTURE_THREE_FINGER = "three_finger"
GESTURE_FOUR_FINGER = "four_finger"
GESTURE_VOLUME = "volume"
GESTURE_SCREENSHOT = "screenshot"
GESTURE_UNKNOWN = "unknown"

GESTURE_LABELS = {
    GESTURE_IDLE: "IDLE — Tangan Terbuka",
    GESTURE_MOVE: "GERAK KURSOR",
    GESTURE_SCROLL: "MODE SCROLL",
    GESTURE_LEFT_CLICK: "KLIK KIRI!",
    GESTURE_RIGHT_CLICK: "KLIK KANAN!",
    GESTURE_DRAG: "MODE DRAG",
    GESTURE_THREE_FINGER: "3-JARI NAV",
    GESTURE_FOUR_FINGER: "4-JARI NAV",
    GESTURE_VOLUME: "VOLUME",
    GESTURE_SCREENSHOT: "SCREENSHOT",
    GESTURE_UNKNOWN: "Menunggu...",
}

GESTURE_ICONS = {
    GESTURE_IDLE: "🖐️",
    GESTURE_MOVE: "☝️",
    GESTURE_SCROLL: "✌️",
    GESTURE_LEFT_CLICK: "👆",
    GESTURE_RIGHT_CLICK: "👍",
    GESTURE_DRAG: "✊",
    GESTURE_THREE_FINGER: "3️⃣",
    GESTURE_FOUR_FINGER: "4️⃣",
    GESTURE_VOLUME: "🔊",
    GESTURE_SCREENSHOT: "📷",
    GESTURE_UNKNOWN: "❓",
}

GESTURE_COLORS = {
    GESTURE_IDLE: (180, 180, 180),
    GESTURE_MOVE: (255, 200, 0),
    GESTURE_SCROLL: (0, 255, 255),
    GESTURE_LEFT_CLICK: (0, 255, 0),
    GESTURE_RIGHT_CLICK: (0, 165, 255),
    GESTURE_DRAG: (0, 0, 255),
    GESTURE_THREE_FINGER: (255, 255, 0),
    GESTURE_FOUR_FINGER: (255, 100, 50),
    GESTURE_VOLUME: (50, 255, 50),
    GESTURE_SCREENSHOT: (100, 50, 255),
    GESTURE_UNKNOWN: (100, 100, 100),
}

class GestureController:
    CLICK_DISTANCE_THRESHOLD = 45
    STABILIZE_FRAMES = 3
    STABILIZE_FRAMES_ACTION = 4

    def __init__(self):
        self.cooldown = CooldownManager()
        self.swipe_tracker = SwipeTracker(history_size=12, swipe_threshold=70)
        self.drag_active = False
        self.prev_scroll_y = None
        self.current_gesture = GESTURE_UNKNOWN
        self.confirmed_gesture = GESTURE_UNKNOWN
        self._gesture_buffer = []
        self._buffer_size = 6
        self.scroll_accumulator = 0.0
        self.click_feedback_time = 0
        self.click_feedback_type = ""

    def _stabilize_gesture(self, raw_gesture):
        self._gesture_buffer.append(raw_gesture)
        if len(self._gesture_buffer) > self._buffer_size:
            self._gesture_buffer.pop(0)
        if len(self._gesture_buffer) < self.STABILIZE_FRAMES:
            return self.confirmed_gesture
        action_gestures = {GESTURE_LEFT_CLICK, GESTURE_RIGHT_CLICK, GESTURE_SCREENSHOT}
        required = self.STABILIZE_FRAMES_ACTION if raw_gesture in action_gestures else self.STABILIZE_FRAMES
        recent = self._gesture_buffer[-required:]
        if all(g == raw_gesture for g in recent):
            self.confirmed_gesture = raw_gesture
        return self.confirmed_gesture

    def detect_gesture(self, fingers, landmarks_list, detector):
        if len(landmarks_list) == 0:
            raw = GESTURE_UNKNOWN
            self.current_gesture = self._stabilize_gesture(raw)
            return self.current_gesture
        thumb, index, middle, ring, pinky = fingers
        total_up = sum(fingers)
        raw = GESTURE_UNKNOWN
        if total_up == 5:
            raw = GESTURE_IDLE
        elif total_up == 0:
            raw = GESTURE_DRAG
        elif fingers == [0, 0, 0, 0, 1]:
            raw = GESTURE_SCREENSHOT
        elif fingers == [1, 0, 0, 0, 1]:
            raw = GESTURE_VOLUME
        elif fingers == [0, 1, 1, 1, 1]:
            raw = GESTURE_FOUR_FINGER
        elif fingers == [0, 1, 1, 1, 0]:
            raw = GESTURE_THREE_FINGER
        elif fingers == [1, 1, 0, 0, 0]:
            raw = GESTURE_LEFT_CLICK
        elif fingers == [0, 1, 1, 0, 0]:
            distance, _, _ = detector.find_distance(8, 12)
            raw = GESTURE_SCROLL
        elif fingers == [0, 1, 0, 0, 0]:
            dist, _, _ = detector.find_distance(8, 5)
            if dist < 65:
                raw = GESTURE_LEFT_CLICK
            else:
                raw = GESTURE_MOVE
        self.current_gesture = self._stabilize_gesture(raw)
        return self.current_gesture

    def execute_gesture(self, gesture, detector, screen_x=0, screen_y=0, hand_center=None):
        result = {"gesture": gesture, "action": None, "detail": ""}
        if gesture == GESTURE_IDLE:
            self._end_drag()
            self.prev_scroll_y = None
            self.swipe_tracker.reset()
            result["action"] = "pause"
            result["detail"] = "Tangan terbuka — jeda"
            return result
        if gesture == GESTURE_MOVE:
            self._end_drag()
            pyautogui.moveTo(screen_x, screen_y)
            result["action"] = "move"
            result["detail"] = f"({screen_x}, {screen_y})"
            return result
        if gesture == GESTURE_LEFT_CLICK:
            if self.cooldown.can_trigger("left_click", cooldown_ms=300):
                pyautogui.click()
                self.click_feedback_time = time.time()
                self.click_feedback_type = "LEFT"
                result["action"] = "click"
                result["detail"] = "Klik kiri!"
            return result
        if gesture == GESTURE_RIGHT_CLICK:
            if self.cooldown.can_trigger("right_click", cooldown_ms=600):
                pyautogui.rightClick()
                self.click_feedback_time = time.time()
                self.click_feedback_type = "RIGHT"
                result["action"] = "right_click"
                result["detail"] = "Klik kanan!"
            return result
        if gesture == GESTURE_SCROLL:
            self._end_drag()
            if len(detector.landmarks_list) > 0:
                y_index = detector.landmarks_list[8][2]
                y_middle = detector.landmarks_list[12][2]
                current_y = (y_index + y_middle) / 2
                if self.prev_scroll_y is not None:
                    diff = self.prev_scroll_y - current_y
                    self.scroll_accumulator += diff * 0.12
                    if abs(self.scroll_accumulator) >= 1:
                        scroll_amount = int(self.scroll_accumulator)
                        pyautogui.scroll(scroll_amount)
                        self.scroll_accumulator -= scroll_amount
                        direction = "↑ Atas" if scroll_amount > 0 else "↓ Bawah"
                        result["action"] = "scroll"
                        result["detail"] = f"Scroll {direction}"
                self.prev_scroll_y = current_y
            return result
        if gesture == GESTURE_DRAG:
            if not self.drag_active:
                self.drag_active = True
                pyautogui.mouseDown()
                result["action"] = "drag_start"
                result["detail"] = "Drag dimulai — buka tangan untuk lepas"
            else:
                pyautogui.moveTo(screen_x, screen_y)
                result["action"] = "dragging"
                result["detail"] = f"Dragging..."
            return result
        if gesture == GESTURE_THREE_FINGER:
            self._end_drag()
            swipe_dir = self.swipe_tracker.update(hand_center)
            if swipe_dir:
                if swipe_dir == "up":
                    if self.cooldown.can_trigger("task_view", cooldown_ms=1200):
                        pyautogui.hotkey("win", "tab")
                        result["action"] = "task_view"
                        result["detail"] = "Task View (Win+Tab)"
                elif swipe_dir == "down":
                    if self.cooldown.can_trigger("show_desktop", cooldown_ms=1200):
                        pyautogui.hotkey("win", "d")
                        result["action"] = "show_desktop"
                        result["detail"] = "Show Desktop (Win+D)"
                elif swipe_dir in ("left", "right"):
                    if self.cooldown.can_trigger("alt_tab", cooldown_ms=1000):
                        pyautogui.hotkey("alt", "tab")
                        result["action"] = "switch_app"
                        result["detail"] = f"Switch App ({'→' if swipe_dir == 'right' else '←'})"
            else:
                result["detail"] = "Swipe untuk navigasi..."
            return result
        if gesture == GESTURE_FOUR_FINGER:
            self._end_drag()
            swipe_dir = self.swipe_tracker.update(hand_center)
            if swipe_dir:
                if swipe_dir == "left":
                    if self.cooldown.can_trigger("vdesktop", cooldown_ms=1200):
                        pyautogui.hotkey("win", "ctrl", "left")
                        result["action"] = "virtual_desktop"
                        result["detail"] = "Desktop ← Kiri"
                elif swipe_dir == "right":
                    if self.cooldown.can_trigger("vdesktop", cooldown_ms=1200):
                        pyautogui.hotkey("win", "ctrl", "right")
                        result["action"] = "virtual_desktop"
                        result["detail"] = "Desktop → Kanan"
                elif swipe_dir == "up":
                    if self.cooldown.can_trigger("maximize", cooldown_ms=1200):
                        pyautogui.hotkey("win", "up")
                        result["action"] = "maximize"
                        result["detail"] = "Maximize (Win+Up)"
                elif swipe_dir == "down":
                    if self.cooldown.can_trigger("minimize", cooldown_ms=1200):
                        pyautogui.hotkey("win", "down")
                        result["action"] = "minimize"
                        result["detail"] = "Minimize (Win+Down)"
            else:
                result["detail"] = "Swipe untuk pindah desktop..."
            return result
        if gesture == GESTURE_VOLUME:
            self._end_drag()
            try:
                if len(detector.landmarks_list) > 0:
                    current_y = detector.landmarks_list[4][2]
                    if self.prev_scroll_y is not None:
                        diff = self.prev_scroll_y - current_y
                        if abs(diff) > 8:
                            if self.cooldown.can_trigger("volume", cooldown_ms=120):
                                if diff > 0:
                                    pyautogui.hotkey("volumeup")
                                    result["detail"] = "Volume ↑"
                                else:
                                    pyautogui.hotkey("volumedown")
                                    result["detail"] = "Volume ↓"
                                result["action"] = "volume"
                    else:
                        result["detail"] = "Gerak atas/bawah untuk volume"
                    self.prev_scroll_y = current_y
            except Exception:
                result["detail"] = "Volume tidak tersedia"
            return result
        if gesture == GESTURE_SCREENSHOT:
            self._end_drag()
            if self.cooldown.can_trigger("screenshot", cooldown_ms=2500):
                pyautogui.hotkey("win", "shift", "s")
                result["action"] = "screenshot"
                result["detail"] = "Screenshot! (Win+Shift+S)"
            else:
                result["detail"] = "Screenshot — tunggu cooldown..."
            return result
        return result

    def _end_drag(self):
        if self.drag_active:
            pyautogui.mouseUp()
            self.drag_active = False

    def reset_scroll(self):
        self.prev_scroll_y = None
        self.scroll_accumulator = 0.0

    def has_click_feedback(self):
        if time.time() - self.click_feedback_time < 0.3:
            return self.click_feedback_type
        return None
