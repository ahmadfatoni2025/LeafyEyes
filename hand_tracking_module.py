import cv2
import mediapipe as mp
import math
import os
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

class HandDetector:
    TIP_IDS = [4, 8, 12, 16, 20]

    def __init__(self, mode=False, max_hands=1, detection_con=0.7, track_con=0.7):
        self.max_hands = max_hands
        self.detection_con = detection_con
        self.track_con = track_con
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file tidak ditemukan: {model_path}\n"
                "Download dari: https://storage.googleapis.com/mediapipe-models/"
                "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
            )
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=self.max_hands,
            min_hand_detection_confidence=self.detection_con,
            min_hand_presence_confidence=self.detection_con,
            min_tracking_confidence=self.track_con,
            running_mode=vision.RunningMode.IMAGE,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        self.hand_connections = vision.HandLandmarksConnections.HAND_CONNECTIONS
        self.landmarks_list = []
        self.results = None

    def find_hands(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        self.results = self.landmarker.detect(mp_image)
        if draw and self.results.hand_landmarks:
            for hand_lm in self.results.hand_landmarks:
                self._draw_landmarks(img, hand_lm)
        return img

    def _draw_landmarks(self, img, hand_landmarks):
        h, w, _ = img.shape
        for connection in self.hand_connections:
            start_idx = connection.start
            end_idx = connection.end
            start_lm = hand_landmarks[start_idx]
            end_lm = hand_landmarks[end_idx]
            start_point = (int(start_lm.x * w), int(start_lm.y * h))
            end_point = (int(end_lm.x * w), int(end_lm.y * h))
            cv2.line(img, start_point, end_point, (0, 255, 0), 2)
        for idx, lm in enumerate(hand_landmarks):
            cx, cy = int(lm.x * w), int(lm.y * h)
            if idx in self.TIP_IDS:
                cv2.circle(img, (cx, cy), 8, (255, 0, 255), cv2.FILLED)
            else:
                cv2.circle(img, (cx, cy), 5, (0, 0, 255), cv2.FILLED)

    def find_position(self, img, hand_no=0):
        self.landmarks_list = []
        if self.results and self.results.hand_landmarks:
            if hand_no < len(self.results.hand_landmarks):
                hand = self.results.hand_landmarks[hand_no]
                h, w, _ = img.shape
                for idx, lm in enumerate(hand):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    self.landmarks_list.append([idx, cx, cy])
        return self.landmarks_list

    def fingers_up(self):
        fingers = []
        if len(self.landmarks_list) == 0:
            return [0, 0, 0, 0, 0]
        if self.landmarks_list[self.TIP_IDS[0]][1] > self.landmarks_list[self.TIP_IDS[4]][1]:
            if self.landmarks_list[self.TIP_IDS[0]][1] > self.landmarks_list[self.TIP_IDS[0] - 1][1]:
                fingers.append(1)
            else:
                fingers.append(0)
        else:
            if self.landmarks_list[self.TIP_IDS[0]][1] < self.landmarks_list[self.TIP_IDS[0] - 1][1]:
                fingers.append(1)
            else:
                fingers.append(0)
        for i in range(1, 5):
            if self.landmarks_list[self.TIP_IDS[i]][2] < self.landmarks_list[self.TIP_IDS[i] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)
        return fingers

    def find_distance(self, p1, p2, img=None, draw=True):
        x1, y1 = self.landmarks_list[p1][1], self.landmarks_list[p1][2]
        x2, y2 = self.landmarks_list[p2][1], self.landmarks_list[p2][2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        distance = math.hypot(x2 - x1, y2 - y1)
        if img is not None and draw:
            cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
            cv2.circle(img, (cx, cy), 8, (0, 255, 0), cv2.FILLED)
        return distance, img, [x1, y1, x2, y2, cx, cy]

    def get_hand_center(self):
        if len(self.landmarks_list) == 0:
            return None
        cx = self.landmarks_list[9][1]
        cy = self.landmarks_list[9][2]
        return cx, cy

    def close(self):
        if self.landmarker:
            self.landmarker.close()
