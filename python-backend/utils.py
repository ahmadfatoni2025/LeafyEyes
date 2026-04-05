import time
import numpy as np

def map_coordinates(x, y, cam_w, cam_h, screen_w, screen_h, frame_reduction=100):
    screen_x = np.interp(x, (frame_reduction, cam_w - frame_reduction), (0, screen_w))
    screen_y = np.interp(y, (frame_reduction, cam_h - frame_reduction), (0, screen_h))
    screen_x = max(0, min(screen_w - 1, screen_x))
    screen_y = max(0, min(screen_h - 1, screen_y))
    return int(screen_x), int(screen_y)

def smooth(current_x, current_y, prev_x, prev_y, smoothing=5):
    smoothed_x = prev_x + (current_x - prev_x) / smoothing
    smoothed_y = prev_y + (current_y - prev_y) / smoothing
    return int(smoothed_x), int(smoothed_y)

def detect_swipe_direction(prev_pos, curr_pos, threshold=60):
    if prev_pos is None or curr_pos is None:
        return None
    dx = curr_pos[0] - prev_pos[0]
    dy = curr_pos[1] - prev_pos[1]
    if abs(dx) < threshold and abs(dy) < threshold:
        return None
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    else:
        return "down" if dy > 0 else "up"

class CooldownManager:
    def __init__(self):
        self._last_trigger = {}

    def can_trigger(self, gesture_name, cooldown_ms=600):
        now = time.time() * 1000
        last = self._last_trigger.get(gesture_name, 0)
        if now - last >= cooldown_ms:
            self._last_trigger[gesture_name] = now
            return True
        return False

    def reset(self, gesture_name=None):
        if gesture_name:
            self._last_trigger.pop(gesture_name, None)
        else:
            self._last_trigger.clear()

class SwipeTracker:
    def __init__(self, history_size=10, swipe_threshold=80):
        self.history = []
        self.history_size = history_size
        self.swipe_threshold = swipe_threshold
        self._swipe_detected = False

    def update(self, position):
        if position is None:
            self.history.clear()
            return None
        self.history.append(position)
        if len(self.history) > self.history_size:
            self.history.pop(0)
        if len(self.history) < 5:
            return None
        start = self.history[0]
        end = self.history[-1]
        direction = detect_swipe_direction(start, end, self.swipe_threshold)
        if direction and not self._swipe_detected:
            self._swipe_detected = True
            self.history.clear()
            return direction
        if direction is None:
            self._swipe_detected = False
        return None

    def reset(self):
        self.history.clear()
        self._swipe_detected = False
