#!/usr/bin/env python3
"""
presence_detector_simple.py

Simple, stable presence detector using MediaPipe Tasks (FaceLandmarker) + OpenCV.
Works on Python 3.12+ with MediaPipe 0.10+.

Required:
 - Download a FaceLandmarker .task model and set MODEL_PATH below.

Outputs JSON POSTs to SERVER_URL with status updates and logs CSV.

"""

import time
import math
from datetime import datetime
from collections import deque

import numpy as np
import cv2
import requests
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks import python
from tabulate import tabulate
import csv
import os
from app.utils.log_file import log_file

# -----------------------
# USER CONFIG
# -----------------------
MODEL_PATH = r"C:\Users\lahar\Downloads\desktop_pet_project - Copy\app\data\face_landmarker.task"  # <-- SET: full path to the face_landmarker .task model file
SERVER_URL = "http://127.0.0.1:5050/presence"  # endpoint to receive status
CAMERA_ID = 0
LOG_PATH = log_file("presence_log.csv")

# thresholds (tweak if needed)
AWAY_TIMEOUT = 5.0
SLEEP_EYES_CLOSED = 2.0
DISTRACTED_TIMEOUT = 3.0
EAR_THRESHOLD = 0.25
YAW_THRESHOLD = 40.0
PITCH_THRESHOLD = 200.0
WINDOW_SECONDS = 1.5
FPS_SMOOTHING = 0.9

# landmark groups (commonly compatible with MediaPipe FaceLandmarker models)
LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [263, 387, 385, 362, 373, 380]
LEFT_IRIS_IDXs = [474, 475, 476, 477]
RIGHT_IRIS_IDXs = [469, 470, 471, 472]

HEAD_POSE_IDX = {
    "nose_tip": 1,
    "chin": 152,
    "left_eye_outer": 33,
    "right_eye_outer": 263,
    "mouth_left": 61,
    "mouth_right": 291
}

MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),        # nose tip
    (0.0, -63.6, -12.5),    # chin
    (-43.3, 32.7, -26.0),   # left eye outer
    (43.3, 32.7, -26.0),    # right eye outer
    (-28.9, -28.9, -24.1),  # mouth left
    (28.9, -28.9, -24.1)    # mouth right
], dtype=np.float64)

# -----------------------
# Utilities - CSV + debug table
# -----------------------
def init_csv_if_needed():
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "fps", "status", "confidence",
                "face_present", "avg_ear", "eyes_closed_time",
                "gaze_direction", "gaze_away_time",
                "yaw", "pitch", "roll"
            ])

def append_csv_row(data_dict):
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            data_dict.get("timestamp"),
            data_dict.get("fps"),
            data_dict.get("status"),
            data_dict.get("confidence"),
            data_dict.get("face_present"),
            data_dict.get("avg_ear"),
            data_dict.get("eyes_closed_time"),
            data_dict.get("gaze_direction"),
            data_dict.get("gaze_away_time"),
            data_dict.get("yaw"),
            data_dict.get("pitch"),
            data_dict.get("roll")
        ])

# -----------------------
# Utilities - geometry / mediapipe helpers
# -----------------------
def to_image_coords(lm, w, h):
    return int(lm.x * w), int(lm.y * h)

def compute_EAR(landmarks, indices, w, h):
    """Eye Aspect Ratio from 6 landmarks: [outer, top, top_in, inner, bottom_in, bottom]"""
    pts = [np.array(to_image_coords(landmarks[i], w, h)) for i in indices]
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3]) + 1e-6
    ear = (A + B) / (2.0 * C)
    return ear

def iris_center(landmarks, iris_indices, w, h):
    pts = np.array([to_image_coords(landmarks[i], w, h) for i in iris_indices], dtype=np.float32)
    return np.mean(pts, axis=0)

def iris_ratio(landmarks, eye_indices, iris_indices, w, h):
    outer = np.array(to_image_coords(landmarks[eye_indices[0]], w, h), dtype=np.float32)
    inner = np.array(to_image_coords(landmarks[eye_indices[3]], w, h), dtype=np.float32)
    ic = iris_center(landmarks, iris_indices, w, h)
    eye_vec = inner - outer
    if np.allclose(eye_vec, 0.0):
        return 0.5
    t = np.dot(ic - outer, eye_vec) / (np.dot(eye_vec, eye_vec) + 1e-6)
    return float(np.clip(t, 0.0, 1.0))

def estimate_head_pose(landmarks, w, h, camera_matrix, dist_coeffs=np.zeros((4,1))):
    pts2d = []
    for name in ["nose_tip", "chin", "left_eye_outer", "right_eye_outer", "mouth_left", "mouth_right"]:
        lm = landmarks[HEAD_POSE_IDX[name]]
        pts2d.append((lm.x * w, lm.y * h))
    image_points = np.array(pts2d, dtype=np.float64)
    success, rvec, tvec = cv2.solvePnP(MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
    if not success:
        return False, None, None, (0.0, 0.0, 0.0)
    R, _ = cv2.Rodrigues(rvec)
    sy = math.sqrt(R[0,0]**2 + R[1,0]**2)
    singular = sy < 1e-6
    if not singular:
        x = math.atan2(R[2,1], R[2,2])
        y = math.atan2(-R[2,0], sy)
        z = math.atan2(R[1,0], R[0,0])
    else:
        x = math.atan2(-R[1,2], R[1,1])
        y = math.atan2(-R[2,0], sy)
        z = 0
    pitch = math.degrees(x)
    yaw = math.degrees(y)
    roll = math.degrees(z)
    return True, rvec, tvec, (yaw, pitch, roll)

def post_status(obj):
    try:
        requests.post(SERVER_URL, json=obj, timeout=0.8)
    except Exception:
        pass

# -----------------------
# Main
# -----------------------
def main():
    if not MODEL_PATH or MODEL_PATH.strip() == "":
        print("ERROR: set MODEL_PATH to a FaceLandmarker .task model file path at top of script.")
        return

    # Create FaceLandmarker (VIDEO mode)
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = vision.FaceLandmarker
    FaceLandmarkerOptions = vision.FaceLandmarkerOptions
    RunningMode = vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print("ERROR: cannot open camera")
        return

    ret, frame = cap.read()
    if not ret:
        print("ERROR: cannot read camera")
        return

    h, w = frame.shape[:2]
    focal_length = w
    center = (w / 2.0, h / 2.0)
    camera_matrix = np.array([[focal_length, 0, center[0]],
                              [0, focal_length, center[1]],
                              [0, 0, 1]], dtype=np.float64)

    # trackers
    last_face_time = time.time()
    face_present = False
    eyes_closed_since = None
    gaze_away_since = None
    ear_history = deque()
    gaze_history = deque()
    pose_history = deque()
    fps = 0.0
    last_time = time.time()
    init_csv_if_needed()

    print("Starting presence_detector_simple — press ESC to exit.")

    with FaceLandmarker.create_from_options(options) as landmarker:
        while True:
            now = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp_ms = int(now * 1000)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            # FPS smoothing
            dt = now - last_time
            last_time = now
            fps = FPS_SMOOTHING * fps + (1.0 - FPS_SMOOTHING) * (1.0 / max(dt, 1e-6))

            status = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "fps": round(fps, 1),
                "status": "unknown",
                "confidence": 0.0
            }

            if result and result.face_landmarks and len(result.face_landmarks) > 0:
                face_present = True
                last_face_time = now
                lm_list = result.face_landmarks[0]

                # EAR
                left_ear = compute_EAR(lm_list, LEFT_EYE_IDX, w, h)
                right_ear = compute_EAR(lm_list, RIGHT_EYE_IDX, w, h)
                ear = (left_ear + right_ear) / 2.0
                ear_history.append((now, ear))
                while ear_history and now - ear_history[0][0] > WINDOW_SECONDS:
                    ear_history.popleft()
                recent_ears = [e for ts,e in ear_history]
                avg_ear = float(np.mean(recent_ears)) if recent_ears else ear

                eyes_closed = avg_ear < EAR_THRESHOLD
                if eyes_closed:
                    if eyes_closed_since is None:
                        eyes_closed_since = now
                else:
                    eyes_closed_since = None
                eyes_closed_time = (now - eyes_closed_since) if eyes_closed_since else 0.0

                # gaze (simple horizontal iris ratio)
                left_ratio = iris_ratio(lm_list, LEFT_EYE_IDX, LEFT_IRIS_IDXs, w, h)
                right_ratio = iris_ratio(lm_list, RIGHT_EYE_IDX, RIGHT_IRIS_IDXs, w, h)
                gaze_history.append((now, (left_ratio, right_ratio)))
                while gaze_history and now - gaze_history[0][0] > WINDOW_SECONDS:
                    gaze_history.popleft()
                g = [g for ts,g in gaze_history]
                if g:
                    left_mean = np.mean([x[0] for x in g])
                    right_mean = np.mean([x[1] for x in g])
                    mean_ratio = (left_mean + right_mean) / 2.0
                else:
                    mean_ratio = 0.5

                # head pose
                ok, rvec, tvec, (yaw, pitch, roll) = estimate_head_pose(lm_list, w, h, camera_matrix)
                yaw_val, pitch_val, roll_val = (yaw, pitch, roll)
                pose_history.append((now, (yaw_val, pitch_val, roll_val)))
                while pose_history and now - pose_history[0][0] > WINDOW_SECONDS:
                    pose_history.popleft()

                # Improved gaze classification: prefer head yaw when clear, else use iris ratio
                gaze_direction = "center"
                # Use yaw primarily if head turned more than threshold
                if abs(yaw_val) > YAW_THRESHOLD:
                    gaze_direction = "right" if yaw_val < 0 else "left"
                # compute gaze_away_time
                if gaze_direction != "center":
                    if gaze_away_since is None:
                        gaze_away_since = now
                else:
                    gaze_away_since = None
                gaze_away_time = (now - gaze_away_since) if gaze_away_since else 0.0

                head_facing = (abs(yaw_val) < YAW_THRESHOLD) and (abs(pitch_val) < PITCH_THRESHOLD)

                # status decision
                status_kind = "working"
                confidence = 0.8
                if eyes_closed_time >= SLEEP_EYES_CLOSED:
                    status_kind = "sleeping"
                    confidence = 0.95
                elif gaze_away_time >= DISTRACTED_TIMEOUT or not head_facing:
                    status_kind = "distracted"
                    confidence = 0.6
                else:
                    status_kind = "working"
                    confidence = 0.9

                status.update({
                    "status": status_kind,
                    "confidence": confidence,
                    "face_present": True,
                    "avg_ear": float(round(avg_ear, 3)),
                    "eyes_closed_time": float(round(eyes_closed_time, 2)),
                    "gaze_direction": gaze_direction,
                    "gaze_away_time": float(round(gaze_away_time, 2)),
                    "yaw": float(round(yaw_val, 2)),
                    "pitch": float(round(pitch_val, 2)),
                    "roll": float(round(roll_val, 2))
                })
                append_csv_row(status)

                # -----------------------
                # Debug Table Overlay (on-frame) + Console print
                # -----------------------
                debug_lines = [
                    f"Status: {status_kind}    Conf: {confidence:.2f}",
                    f"FPS: {fps:.1f}",
                    f"EAR(avg): {avg_ear:.3f}    EyesClosed: {eyes_closed_time:.2f}s",
                    f"Gaze: {gaze_direction}    GazeAway: {gaze_away_time:.2f}s",
                    f"Yaw: {yaw_val:.1f}   Pitch: {pitch_val:.1f}   Roll: {roll_val:.1f}",
                    f"Iris L/R: {left_ratio:.2f} / {right_ratio:.2f}"
                ]

                # draw semi-transparent table background
                x0, y0 = 10, 10
                line_height = 22
                padding = 8
                table_width = 520
                table_height = padding*2 + line_height * len(debug_lines)
                overlay = frame.copy()
                cv2.rectangle(
                    overlay,
                    (x0, y0),
                    (x0 + table_width, y0 + table_height),
                    (20, 20, 20),
                    -1
                )
                alpha = 0.55
                frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

                # draw text lines
                for i, text in enumerate(debug_lines):
                    y = y0 + padding + (i+1) * line_height
                    cv2.putText(
                        frame,
                        text,
                        (x0 + 10, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA
                    )

                # print console debug table (smaller set)
                debug_info = {
                    "FPS": status["fps"],
                    "Status": status["status"],
                    "Confidence": status["confidence"],
                    "Face Present": status["face_present"],
                    "EAR": status["avg_ear"],
                    "Eyes Closed Time": status["eyes_closed_time"],
                    "Gaze Direction": status["gaze_direction"],
                    "Gaze Away Time": status["gaze_away_time"],
                    "Yaw": status["yaw"],
                    "Pitch": status["pitch"],
                    "Roll": status["roll"]
                }
                append_csv_row(status)

                # send
                post_status(status)

            else:
                # no face
                if face_present:
                    if time.time() - last_face_time > AWAY_TIMEOUT:
                        face_present = False
                if not face_present and (time.time() - last_face_time) > AWAY_TIMEOUT:
                    status.update({
                        "status": "away",
                        "confidence": 0.98,
                        "face_present": False
                    })
                    post_status(status)
                    cv2.putText(frame, "Status: AWAY", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,200,255), 2)

            # show
            cv2.imshow("Presence Detector", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break

    cap.release()
    cv2.destroyAllWindows()
    print("Exited.")

def start_presence_detector():
    main()

if __name__ == "__main__":
    start_presence_detector()
