import os
import numpy as np
import pandas as pd
from deepface import DeepFace

DATA_DIR = "data/registered_faces"
VOTERS_FILE = "voters.csv"

if not os.path.exists(VOTERS_FILE):
    print("voters.csv not found!")
    exit()

voters_df = pd.read_csv(VOTERS_FILE)

for idx, row in voters_df.iterrows():
    photo_file = row.get("PHOTO")
    if not photo_file:
        continue

    img_path = os.path.join(DATA_DIR, photo_file)
    emb_path = img_path.replace(".jpg", ".npy")

    if not os.path.exists(img_path):
        print(f"Image missing: {img_path}")
        continue

    if os.path.exists(emb_path):
        print(f"Embedding already exists: {emb_path}")
        continue

    try:
        print(f"Generating embedding for {photo_file}...")
        emb_obj = DeepFace.represent(
            img_path=img_path,
            model_name="VGG-Face",
            enforce_detection=False
        )
        embedding = np.array(emb_obj[0]["embedding"]).reshape(1, -1)
        embedding = embedding / np.linalg.norm(embedding)
        np.save(emb_path, embedding)
        print(f"Saved embedding: {emb_path}")
    except Exception as e:
        print(f"Failed for {photo_file}: {e}")
