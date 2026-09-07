import os
import shutil
import sqlite3
import tempfile
import urllib.request
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Path definitions
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "CSProject.db")
VIDEO_DIR = os.path.join(BASE_DIR, "user_videos")
OUTPUT_CSV = os.path.join(BASE_DIR, "dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "face_landmarker.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"


def ensure_model_exists():
    if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 1000000:
        print("Downloading face_landmarker.task...")
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("Download complete.")
        except Exception as e:
            print(f"Download failed: {e}")


def euclidean_distance(pt1, pt2):
    return np.linalg.norm(np.array(pt1) - np.array(pt2))


def process_video(video_path, landmarker):
    if not os.path.exists(video_path):
        print(f"  [Error] 文件不存在: {video_path}")
        return None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  [Error] OpenCV 无法打开视频文件: {video_path}")
        return None

    mouth_ratios = []
    eye_ratios = []
    eyebrow_distances = []

    total_frames = 0
    detected_frames = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1

        # Resize standard size if resolution is too large to boost detection rate
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        detection_result = landmarker.detect(mp_image)

        if detection_result.face_landmarks:
            detected_frames += 1
            landmarks = detection_result.face_landmarks[0]
            h, w, _ = frame.shape

            pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

            mouth_width = euclidean_distance(pts[61], pts[291])
            mouth_height = euclidean_distance(pts[13], pts[14])
            mouth_ratio = mouth_height / (mouth_width + 1e-6)

            left_ear = euclidean_distance(pts[159], pts[145])
            right_ear = euclidean_distance(pts[386], pts[374])
            avg_ear = (left_ear + right_ear) / 2.0

            brow_dist = euclidean_distance(pts[55], pts[285])

            mouth_ratios.append(mouth_ratio)
            eye_ratios.append(avg_ear)
            eyebrow_distances.append(brow_dist)

    cap.release()

    print(f"  [Info] {os.path.basename(video_path)}: 读取 {total_frames} 帧, 成功检测人脸 {detected_frames} 帧")

    if len(mouth_ratios) == 0:
        return None

    metrics = {
        "mouth_ratio_mean": float(np.mean(mouth_ratios)),
        "mouth_ratio_std": float(np.std(mouth_ratios)),
        "eye_ratio_mean": float(np.mean(eye_ratios)),
        "eye_ratio_std": float(np.std(eye_ratios)),
        "brow_dist_mean": float(np.mean(eyebrow_distances)),
        "brow_dist_std": float(np.std(eyebrow_distances)),
    }

    return metrics


def main():
    ensure_model_exists()

    if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 1000000:
        print("Invalid model file.")
        return

    temp_dir = tempfile.gettempdir()
    temp_model_path = os.path.join(temp_dir, "face_landmarker_temp.task")
    shutil.copyfile(MODEL_PATH, temp_model_path)

    try:
        base_options = python.BaseOptions(model_asset_path=temp_model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
        )
        landmarker = vision.FaceLandmarker.create_from_options(options)

        conn = sqlite3.connect(DB_PATH)
        # 排除 phq9_score 为空的情况，只处理有成绩且有文件夹的用户
        query = "SELECT id, phq9_score FROM participant WHERE phq9_score IS NOT NULL"
        df_participants = pd.read_sql_query(query, conn)
        conn.close()

        print(f"有效问卷参与者总数: {len(df_participants)}")

        dataset_rows = []

        for _, row in df_participants.iterrows():
            pid = int(row["id"])
            phq9_score = row["phq9_score"]
            user_folder = os.path.join(VIDEO_DIR, str(pid))

            if not os.path.exists(user_folder):
                continue

            print(f"\n---> 开始处理用户 ID: {pid}")
            participant_data = {"participant_id": pid, "phq9_score": phq9_score}

            valid_entry = True
            for emotion in ["comedy", "neutral", "sad"]:
                video_file = os.path.join(user_folder, f"{emotion}.mp4")
                feat = process_video(video_file, landmarker)

                if feat is None:
                    print(f"【跳过用户 {pid}】视频 {emotion}.mp4 特征提取失败！")
                    valid_entry = False
                    break

                for key, val in feat.items():
                    participant_data[f"{emotion}_{key}"] = val

            if valid_entry:
                dataset_rows.append(participant_data)
                print(f"【成功】用户 {pid} 特征提取完毕！")

        landmarker.close()

        df_dataset = pd.DataFrame(dataset_rows)
        df_dataset.to_csv(OUTPUT_CSV, index=False)
        print(f"\nDataset successfully saved to {OUTPUT_CSV} with {len(df_dataset)} samples.")

    finally:
        if os.path.exists(temp_model_path):
            os.remove(temp_model_path)


if __name__ == "__main__":
    main()