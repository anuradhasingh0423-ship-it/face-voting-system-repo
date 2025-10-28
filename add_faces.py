import tkinter as tk
import subprocess, sys
import tkinter.filedialog as fd
from PIL import Image
import pytesseract
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
import re
import shutil
import webbrowser



# ---------------- Tesseract Config ---------------- #
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---------------- Configuration ---------------- #
LANGUAGE = 'hi'
DATA_DIR = "data/registered_faces"
VOTER_ID_DIR = "data/voter_ids"
CSV_FILE = "voters.csv"
EMBED_KEY = "PHOTO"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VOTER_ID_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')



# on successful registration (server-side process or when add_faces.py posts to server)

import secrets, json, os

TOKEN_MAP_FILE = "token_map.json"   # { token: {mobile, name, face_file, used: False} }

def create_vote_token(mobile, name, face_file):
    token = secrets.token_urlsafe(24)
    data = {}
    if os.path.exists(TOKEN_MAP_FILE):
        with open(TOKEN_MAP_FILE,"r",encoding="utf-8") as f:
            data = json.load(f)
    data[token] = {"mobile": str(mobile), "name": name, "face_file": face_file, "used": False}
    with open(TOKEN_MAP_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    return token


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
def get_cached_embedding(npy_path):
    if os.path.exists(npy_path):
        emb = np.load(npy_path).reshape(1, -1)
        emb = emb / np.linalg.norm(emb)
        return emb
    return None

def is_duplicate_face(new_embedding, threshold=0.75):
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
    show_status("कृपया कैमरे की तरफ़ देखिए" if LANGUAGE=='hi' else "Please look at the camera")
    
    cap = None
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            break
    else:
        show_status("कैमरा नहीं खुल पाया" if LANGUAGE=='hi' else "Failed to open camera")
        return None

    cv2.namedWindow("Press Space to Capture / स्पेस दबाकर कैप्चर करें")
    face_detected_frame = None
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100,100))

        for (x,y,w,h) in faces:
            cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
            cv2.putText(frame, person_name,(x,y-10), cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2,cv2.LINE_AA)
            face_detected_frame = frame.copy()

        cv2.imshow("Press Space to Capture / स्पेस दबाकर कैप्चर करें", frame)
        key = cv2.waitKey(1)

        if key == 32:  # SPACE
            if face_detected_frame is not None:
                break
            else:
                show_status("चेहरा नहीं मिला" if LANGUAGE=='hi' else "No face detected")
        elif key == 27:  # ESC
            face_detected_frame = None
            break

        if time.time() - start_time > 10 and face_detected_frame is None:
            show_status("कोई चेहरा नहीं मिला, दोबारा प्रयास करें।" if LANGUAGE=='hi' else "No face found, please try again.")
            start_time = time.time()

    cap.release()
    cv2.destroyAllWindows()
    return face_detected_frame

# --- Global variable for original voter ID image path ---
original_voterid_path = None

def upload_voterid():
    global original_voterid_path
    file_path = fd.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
    if file_path:
        original_voterid_path = file_path  # Save original path for later use
        try:
            text = pytesseract.image_to_string(Image.open(file_path), lang='hin+eng')

            # Extract Name
            name_match = re.search(r"(?:Name|नाम)[^\w\d]*([\w\s\u0900-\u097F]+)", text)
            if name_match:
                extracted_name = name_match.group(1).strip()
                name_entry.delete(0, tk.END)
                name_entry.insert(0, extracted_name)

            # Extract Voter ID
            voterid_match = re.search(r"\b[A-Z]{3}\d{7}\b", text)
            if voterid_match:
                voter_id_number = voterid_match.group(0).strip()
                voterid_entry.config(state='normal')
                voterid_entry.delete(0, tk.END)
                voterid_entry.insert(0, voter_id_number)
                voterid_entry.config(state='readonly')

            # Save voter ID image immediately in voter IDs folder
            voterid_filename = os.path.basename(file_path)
            voterid_save_path = os.path.join(VOTER_ID_DIR, voterid_filename)
            shutil.copy(file_path, voterid_save_path)

            show_status("Voter ID uploaded. Name & Voter ID extracted.")
        except Exception as e:
            show_status("OCR failed. कृपया Name और Voter ID manually भरें / enter manually.")
            print("OCR error:", e)




# ---------------- Register Face ---------------- #
def register_face(name, mobile, voter_id_number, location):
    name, mobile, voter_id_number, location = name.strip(), mobile.strip(), voter_id_number.strip(), location.strip()
    try:
        if not name or not mobile or not voter_id_number or not location:
            show_status("कृपया सभी फ़ील्ड भरें" if LANGUAGE=='hi' else "Please fill all fields")
            return

        df = pd.read_csv(CSV_FILE, dtype={'VOTER_ID':str,'MOBILE':str}) if os.path.exists(CSV_FILE) else pd.DataFrame(columns=["MOBILE","NAME","VOTER_ID","LOCATION",EMBED_KEY,"VOTER_ID_IMAGE"])
        if EMBED_KEY not in df.columns: df[EMBED_KEY]=""
        if "VOTER_ID_IMAGE" not in df.columns: df["VOTER_ID_IMAGE"]=""

        # Duplicate checks
        if len(df[df["MOBILE"]==mobile])>=1:
            show_status("यह मोबाइल पहले ही पंजीकृत है" if LANGUAGE=='hi' else "This mobile is already registered")
            return
        if voter_id_number in df["VOTER_ID"].astype(str).values:
            show_status("यह Voter ID पहले से उपयोग किया गया है" if LANGUAGE=='hi' else "This Voter ID is already used")
            return

        # Capture face
        frame = show_camera_and_capture(name)
        if frame is None:
            show_status("चेहरा कैप्चर नहीं हो पाया" if LANGUAGE=='hi' else "Failed to capture face")
            return

        temp_img_path = "temp_face.jpg"
        cv2.imwrite(temp_img_path, frame)

        # Face embedding
        try:
            new_embedding_obj = DeepFace.represent(img_path=temp_img_path, model_name="VGG-Face", enforce_detection=False)
            new_embedding = np.array(new_embedding_obj[0]["embedding"]).reshape(1,-1)
            new_embedding = new_embedding / np.linalg.norm(new_embedding)
        except Exception as e:
            os.remove(temp_img_path)
            show_status("चेहरे की पहचान नहीं हो पाई" if LANGUAGE=='hi' else "Failed to process face")
            print("Embedding error:", e)
            return
        os.remove(temp_img_path)

        if is_duplicate_face(new_embedding):
            show_status("यह चेहरा पहले से पंजीकृत है" if LANGUAGE=='hi' else "This face is already registered")
            return

        # Save face
        img_filename = f"{mobile}_{name}.jpg"
        img_path = os.path.join(DATA_DIR,img_filename)
        embedding_path = img_path.replace('.jpg','.npy')
        cv2.imwrite(img_path, frame)
        np.save(embedding_path,new_embedding)

        # Save record
        voterid_image_filename = voter_id_number + ".jpg"
        voterid_image_path = os.path.join(VOTER_ID_DIR, voter_id_number + ".jpg")

        if original_voterid_path and os.path.exists(original_voterid_path):
            shutil.copy(original_voterid_path, voterid_image_path)
        else:
            show_status("Voter ID image not found. कृपया इसे manually upload करें")
            return

        new_row = pd.DataFrame([{
            "MOBILE":mobile,
            "NAME":name,
            "VOTER_ID":voter_id_number,
            "LOCATION":location,
            EMBED_KEY:img_filename,
            "VOTER_ID_IMAGE":voterid_image_filename
        }])
        df = pd.concat([df,new_row],ignore_index=True)
        df.to_csv(CSV_FILE,index=False)

        show_status("पंजीकरण सफल रहा" if LANGUAGE=='hi' else "Registration successful")
        
         # --- CRITICAL CHANGE: Call the new window instead of clearing fields ---
        root.after(100, root.withdraw) # Hide the main window immediately
        post_registration_window() # Open the status check window

        # # Clear fields
        # name_entry.delete(0,tk.END)
        # mobile_entry.delete(0,tk.END)
        # voterid_entry.config(state='normal')
        # voterid_entry.delete(0,tk.END)
        # voterid_entry.config(state='readonly')
        # voterid_path_var.set("")
        # location_entry.delete(0,tk.END)

    except Exception as e:
        show_status(f"अप्रत्याशित त्रुटि: {e}" if LANGUAGE=='hi' else f"Unexpected error: {e}")
        print("Registration error:",repr(e))


# add_faces.py (Add this new function)

def check_status_and_vote():
    """Launches the web browser to check voting status on the main Flask app."""
    main_app_url = "http://127.0.0.1:5000/start_voting_station_route"
    try:
        # Open the main voting URL in the default web browser
        webbrowser.open_new_tab(main_app_url)
        print(f"Opening voting status link: {main_app_url}")
    except Exception as e:
        print(f"Error opening browser for voting status: {e}")

def post_registration_window():
    """Creates a new small window asking the user to check voting status."""
    global post_reg_root 
    
    post_reg_root = tk.Toplevel(root) # Use Toplevel to create a secondary window
    post_reg_root.title("Registration Complete")
    post_reg_root.geometry("400x200")
    post_reg_root.configure(bg="#f4f4f4")

    tk.Label(post_reg_root, 
             text="✅ Registration Successful!", 
             font=("Arial", 18, "bold"), 
             bg="#f4f4f4", fg="#138808").pack(pady=15)

    # Button that checks the status and starts the voting process
    tk.Button(post_reg_root, 
             text="🗳️ Check Voting Status & Start Vote", 
             font=("Arial", 14), 
             bg="#0b3d91", fg="white", padx=15, pady=8,
             command=check_status_and_vote).pack(pady=10)
    
    # Close button
    tk.Button(post_reg_root, 
             text="Close", 
             font=("Arial", 14), 
             bg="#d52d2d", fg="white", padx=15, pady=5,
             command=post_reg_root.destroy).pack(pady=5)
    
    # Hide the main registration window until the user closes the status window
    root.withdraw() 
    post_reg_root.protocol("WM_DELETE_WINDOW", lambda: [root.destroy(), post_reg_root.destroy()]) # Ensure both close

# The main Tkinter loop must be started in a separate thread if you run it from Flask, 
# but since you are running this from subprocess, the existing root.mainloop() is fine.

# ---------------- Language Toggle ---------------- #
def toggle_language():
    global LANGUAGE
    LANGUAGE = 'en' if LANGUAGE=='hi' else 'hi'
    lang_btn.config(text="🔁 भाषा बदलें / Switch Language" if LANGUAGE=='hi' else "🔁 Change Language / भाषा बदलें")
    reg_btn.config(text="📝 पंजीकरण करें / Register" if LANGUAGE=='hi' else "📝 Register / पंजीकरण करें")
    exit_btn.config(text="❌ बंद करें / Exit" if LANGUAGE=='hi' else "❌ Exit / बंद करें")
    title.config(text="🔐 चेहरे से पंजीकरण / Face Registration" if LANGUAGE=='hi' else "🔐 Face Registration / चेहरे से पंजीकरण")
    play_voice("भाषा बदली गई" if LANGUAGE=='hi' else "Language changed", lang=LANGUAGE)

# ---------------- GUI ---------------- #
root = tk.Tk()
root.title("Face Registration")
root.attributes('-fullscreen', True)
root.configure(bg="#f4f4f4")

title = tk.Label(root, text="🔐 चेहरे से पंजीकरण / Face Registration", font=("Arial",28,"bold"), bg="#f4f4f4", fg="#333")
title.pack(pady=30)

frame = tk.Frame(root, bg="#f4f4f4")
frame.pack(pady=20)

tk.Label(frame,text="नाम / Name:", font=("Arial",18), bg="#f4f4f4").grid(row=0,column=0,padx=20,pady=15,sticky="e")
name_entry = tk.Entry(frame,font=("Arial",18), width=25)
name_entry.grid(row=0,column=1,padx=20,pady=15)

tk.Label(frame,text="मोबाइल नंबर / Mobile:", font=("Arial",18), bg="#f4f4f4").grid(row=1,column=0,padx=20,pady=15,sticky="e")
mobile_entry = tk.Entry(frame,font=("Arial",18), width=25)
mobile_entry.grid(row=1,column=1,padx=20,pady=15)

tk.Label(frame,text="मतदाता पहचान पत्र / Voter ID:", font=("Arial",18), bg="#f4f4f4").grid(row=2,column=0,padx=20,pady=15,sticky="e")
voterid_path_var = tk.StringVar()
voterid_entry = tk.Entry(frame,font=("Arial",16), width=25, textvariable=voterid_path_var, state='readonly')
voterid_entry.grid(row=2,column=1,padx=20,pady=15)
upload_btn = tk.Button(frame,text="Upload Voter ID", font=("Arial",12), bg="#3467d1", fg="white", command=upload_voterid)
upload_btn.grid(row=2,column=2,padx=10,pady=15)

tk.Label(frame,text="स्थान / Location:", font=("Arial",18), bg="#f4f4f4").grid(row=3,column=0,padx=20,pady=15,sticky="e")
location_entry = tk.Entry(frame,font=("Arial",18), width=25)
location_entry.grid(row=3,column=1,padx=20,pady=15)

reg_btn = tk.Button(root,text="📝 पंजीकरण करें / Register", font=("Arial",16), bg="#4CC452", fg="white",
                    activebackground="#4a724e", padx=25, pady=10,
                    command=lambda: register_face(
                        name_entry.get(), mobile_entry.get(), voterid_entry.get(), location_entry.get()))
reg_btn.pack(pady=15)

lang_btn = tk.Button(root,text="🔁 भाषा बदलें / Switch Language", font=("Arial",15), bg="#3467d1", fg="white",
                     padx=18, pady=8, command=toggle_language)
lang_btn.pack(pady=8)

exit_btn = tk.Button(root,text="❌ बंद करें / Exit", font=("Arial",15), bg="#d52d2d", fg="white",
                     padx=18, pady=8, command=root.destroy)
exit_btn.pack(pady=8)

status_label = tk.Label(root,text="", font=("Arial",16), bg="#f4f4f4", fg="crimson")
status_label.pack(pady=10)



tk.Label(root, text="--- OR ---", font=("Arial", 12), bg="#f4f4f4").pack(pady=5)

check_btn = tk.Button(root,
                      text="✅ Already Registered? Check Status",
                      font=("Arial", 14),
                      bg="#0b3d91", fg="white",
                      padx=20, pady=8,
                      command=check_status_and_vote)
check_btn.pack(pady=10)


root.mainloop()

