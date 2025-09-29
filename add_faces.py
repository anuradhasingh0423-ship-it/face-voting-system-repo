import tkinter as tk
import cv2
import os
import numpy as np
import pandas as pd
from deepface import DeepFace
from sklearn.metrics.pairwise import cosine_similarity
from gtts import gTTS
import pygame
import threading
import time
import tempfile

# ---------------- Configuration ---------------- #
LANGUAGE = 'hi'
DATA_DIR = "data/registered_faces"
CSV_FILE = "voters.csv"
EMBED_KEY = "PHOTO"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Load OpenCV face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# ---------------- Voice Function ---------------- #
def play_voice(text, lang=LANGUAGE):
    def _play():
        try:
            fd, filename = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            tts = gTTS(text=text, lang=lang)
            tts.save(filename)
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            os.remove(filename)
        except Exception as e:
            print(f"Voice playback error: {e}")
    threading.Thread(target=_play, daemon=True).start()

def show_status(msg):
    status_label.config(text=msg)
    play_voice(msg, lang=LANGUAGE)

# ---------------- Embeddings ---------------- #
def get_embedding(img_path):
    try:
        embedding_obj = DeepFace.represent(
            img_path=img_path,
            model_name="VGG-Face",
            enforce_detection=True
        )
        emb = np.array(embedding_obj[0]["embedding"]).reshape(1, -1)
        emb = emb / np.linalg.norm(emb)
        return emb
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def get_cached_embedding(npy_path):
    if os.path.exists(npy_path):
        emb = np.load(npy_path).reshape(1, -1)
        emb = emb / np.linalg.norm(emb)
        return emb
    return None

def is_duplicate_face(new_embedding, threshold=0.75):
    """
    Check if the new face embedding matches any existing embeddings.
    Slightly higher threshold (0.75) allows small variations in the same face.
    """
    for file in os.listdir(DATA_DIR):
        if file.endswith(".npy"):
            existing_embedding = get_cached_embedding(os.path.join(DATA_DIR, file))
            if existing_embedding is not None:
                sim = cosine_similarity(new_embedding, existing_embedding)[0][0]
                if sim >= threshold:
                    return True
    return False


# ---------------- Camera ---------------- #
def show_camera_and_capture(person_name):
    show_status("कृपया कैमरे की तरफ़ देखिए" if LANGUAGE == 'hi' else "Please look at the camera")
    
    # Auto-detect working camera
    cap = None
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            break
    else:
        show_status("कैमरा नहीं खुल पाया" if LANGUAGE == 'hi' else "Failed to open camera")
        return None

    cv2.namedWindow("Press Space to Capture / स्पेस दबाकर कैप्चर करें")
    face_detected_frame = None
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, person_name, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            face_detected_frame = frame.copy()

        cv2.imshow("Press Space to Capture / स्पेस दबाकर कैप्चर करें", frame)
        key = cv2.waitKey(1)

        if key == 32:  # Space
            if face_detected_frame is not None:
                break
            else:
                show_status("चेहरा नहीं मिला" if LANGUAGE == 'hi' else "No face detected")
        elif key == 27:  # ESC
            face_detected_frame = None
            break

        if time.time() - start_time > 10 and face_detected_frame is None:
            show_status("कोई चेहरा नहीं मिला, दोबारा प्रयास करें।" if LANGUAGE == 'hi' else "No face found, please try again.")
            start_time = time.time()

    cap.release()
    cv2.destroyAllWindows()
    return face_detected_frame

# ---------------- Register Face ---------------- #
def register_face(name, mobile, aadhaar, location):
    name, mobile, aadhaar, location = name.strip(), mobile.strip(), aadhaar.strip(), location.strip()
    try:
        if not name or not mobile or not aadhaar or not location:
            show_status("कृपया सभी फ़ील्ड भरें" if LANGUAGE == 'hi' else "Please fill all fields")
            return
        if not mobile.isdigit() or len(mobile) != 10:
            show_status("कृपया 10 अंकों का मोबाइल नंबर दर्ज करें" if LANGUAGE == 'hi' else "Enter valid 10-digit mobile number")
            return
        if not aadhaar.isdigit() or len(aadhaar) != 12:
            show_status("कृपया 12 अंकों का आधार नंबर दर्ज करें" if LANGUAGE == 'hi' else "Enter 12-digit Aadhaar number")
            return

        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE, dtype={'AADHAAR': str, 'MOBILE': str})
        else:
            df = pd.DataFrame(columns=["MOBILE", "NAME", "AADHAAR", "LOCATION", EMBED_KEY])

        if EMBED_KEY not in df.columns:
            df[EMBED_KEY] = ""

        if len(df[df["MOBILE"] == mobile]) >= 3:
            show_status("इस मोबाइल से 3 पंजीकरण पहले ही हो चुके हैं" if LANGUAGE == 'hi' else "This mobile already has 3 voters")
            return

        if aadhaar in df["AADHAAR"].astype(str).values:
            show_status("यह आधार पहले से उपयोग किया गया है" if LANGUAGE == 'hi' else "This Aadhaar already used")
            return

        frame = show_camera_and_capture(name)
        if frame is None:
            show_status("चेहरा कैप्चर नहीं हो पाया" if LANGUAGE == 'hi' else "Failed to capture face")
            return

        temp_img_path = "temp_face.jpg"
        cv2.imwrite(temp_img_path, frame)

        try:
            new_embedding_obj = DeepFace.represent(
                img_path=temp_img_path,
                model_name="VGG-Face",
                enforce_detection=False
            )
            new_embedding = np.array(new_embedding_obj[0]["embedding"]).reshape(1, -1)
            new_embedding = new_embedding / np.linalg.norm(new_embedding)  # normalize
        except Exception as e:
            os.remove(temp_img_path)
            show_status("चेहरे की पहचान नहीं हो पाई" if LANGUAGE == 'hi' else "Failed to process face")
            print("Embedding error:", e)
            return

        os.remove(temp_img_path)


        if is_duplicate_face(new_embedding):
            show_status("यह चेहरा पहले से पंजीकृत है" if LANGUAGE == 'hi' else "This face is already registered")
            return

        img_filename = f"{mobile}_{name}.jpg"
        img_path = os.path.join(DATA_DIR, img_filename)
        embedding_path = img_path.replace('.jpg', '.npy')

        cv2.imwrite(img_path, frame)
        np.save(embedding_path, new_embedding)

        new_row = pd.DataFrame([{"MOBILE": mobile, "NAME": name, "AADHAAR": aadhaar, "LOCATION": location, EMBED_KEY: img_filename}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)
        show_status("पंजीकरण सफल रहा" if LANGUAGE == 'hi' else "Registration successful")

        name_entry.delete(0, tk.END)
        mobile_entry.delete(0, tk.END)
        aadhaar_entry.delete(0, tk.END)
        location_entry.delete(0, tk.END)

    except Exception as e:
        show_status(f"अप्रत्याशित त्रुटि: {e}" if LANGUAGE == 'hi' else f"Unexpected error: {e}")
        print("Registration error:", repr(e))

# ---------------- Language Toggle ---------------- #
def toggle_language():
    global LANGUAGE
    LANGUAGE = 'en' if LANGUAGE == 'hi' else 'hi'
    lang_btn.config(text="🔁 भाषा बदलें / Switch Language" if LANGUAGE == 'hi' else "🔁 Change Language / भाषा बदलें")
    reg_btn.config(text="📝 पंजीकरण करें / Register" if LANGUAGE == 'hi' else "📝 Register / पंजीकरण करें")
    exit_btn.config(text="❌ बंद करें / Exit" if LANGUAGE == 'hi' else "❌ Exit / बंद करें")
    title.config(text="🔐 चेहरे से पंजीकरण / Face Registration" if LANGUAGE == 'hi' else "🔐 Face Registration / चेहरे से पंजीकरण")
    play_voice("भाषा बदली गई" if LANGUAGE == 'hi' else "Language changed", lang=LANGUAGE)

# ---------------- GUI ---------------- #
root = tk.Tk()
root.title("Face Registration")
root.attributes('-fullscreen', True)
root.configure(bg="#f4f4f4")

title = tk.Label(root, text="🔐 चेहरे से पंजीकरण / Face Registration", font=("Arial", 28, "bold"), bg="#f4f4f4", fg="#333")
title.pack(pady=30)

frame = tk.Frame(root, bg="#f4f4f4")
frame.pack(pady=20)

tk.Label(frame, text="नाम / Name:", font=("Arial", 18), bg="#f4f4f4").grid(row=0, column=0, padx=20, pady=15, sticky="e")
name_entry = tk.Entry(frame, font=("Arial", 18), width=25)
name_entry.grid(row=0, column=1, padx=20, pady=15)

tk.Label(frame, text="मोबाइल नंबर / Mobile:", font=("Arial", 18), bg="#f4f4f4").grid(row=1, column=0, padx=20, pady=15, sticky="e")
mobile_entry = tk.Entry(frame, font=("Arial", 18), width=25)
mobile_entry.grid(row=1, column=1, padx=20, pady=15)

tk.Label(frame, text="आधार नंबर / Aadhaar:", font=("Arial", 18), bg="#f4f4f4").grid(row=2, column=0, padx=20, pady=15, sticky="e")
aadhaar_entry = tk.Entry(frame, font=("Arial", 18), width=25)
aadhaar_entry.grid(row=2, column=1, padx=20, pady=15)

tk.Label(frame, text="स्थान / Location:", font=("Arial", 18), bg="#f4f4f4").grid(row=3, column=0, padx=20, pady=15, sticky="e")
location_entry = tk.Entry(frame, font=("Arial", 18), width=25)
location_entry.grid(row=3, column=1, padx=20, pady=15)

reg_btn = tk.Button(root, text="📝 पंजीकरण करें / Register", font=("Arial", 16), bg="#4CC452", fg="white",
                    activebackground="#4a724e", padx=25, pady=10,
                    command=lambda: register_face(
                        name_entry.get(), mobile_entry.get(), aadhaar_entry.get(), location_entry.get()))
reg_btn.pack(pady=15)

lang_btn = tk.Button(root, text="🔁 भाषा बदलें / Switch Language", font=("Arial", 15), bg="#3467d1", fg="white",
                     padx=18, pady=8, command=toggle_language)
lang_btn.pack(pady=8)

exit_btn = tk.Button(root, text="❌ बंद करें / Exit", font=("Arial", 15), bg="#d52d2d", fg="white",
                     padx=18, pady=8, command=root.destroy)
exit_btn.pack(pady=8)

status_label = tk.Label(root, text="", font=("Arial", 16), bg="#f4f4f4", fg="crimson")
status_label.pack(pady=10)

root.mainloop()









