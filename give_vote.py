import os
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from deepface import DeepFace
from gtts import gTTS
import tempfile
import pygame
import threading
from flask import Flask, render_template, request, redirect, url_for, session
import webbrowser

# -------------------- FILE PATHS --------------------
VOTERS_FILE = "voters.csv"
CANDIDATES_FILE = "candidates.csv"
VOTES_FILE = "Votes.csv"
LOGOS_FOLDER = "logos"

# -------------------- LANGUAGE --------------------
language_mode = 'english'  # 'hindi' or 'english'

LANG_LABELS = {
    "english": {
        "welcome": "Welcome, please verify your face",
        "face_not_recognized": "Face not recognized. Try again.",
        "already_voted": "You have already voted in this election.",
        "vote_success": "Vote cast successfully!",
        "select_election": "Select Election",
        "choose_candidate": "Choose your candidate",
    },
    "hindi": {
        "welcome": "स्वागत है, कृपया अपना चेहरा पहचानें",
        "face_not_recognized": "चेहरा मान्यता प्राप्त नहीं। पुनः प्रयास करें।",
        "already_voted": "आप पहले ही इस चुनाव में मतदान कर चुके हैं।",
        "vote_success": "आपका वोट सफलतापूर्वक दर्ज हो गया!",
        "select_election": "चुनाव चुनें",
        "choose_candidate": "अपना उम्मीदवार चुनें",
    }
}

# -------------------- INITIALIZE PYGAME --------------------
pygame.mixer.init()
def speak(text):
    def run():
        try:
            tts = gTTS(text=text, lang='hi' if language_mode=='hindi' else 'en')
            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as fp:
                temp_path = fp.name
                tts.save(temp_path)

                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
        except Exception as e:
            print("Voice error:", e)
    threading.Thread(target=run, daemon=True).start()

# -------------------- LOAD VOTERS & CANDIDATES --------------------
if not os.path.exists(VOTERS_FILE):
    raise FileNotFoundError(f"{VOTERS_FILE} not found.")
voters_df = pd.read_csv(VOTERS_FILE)

if not os.path.exists(CANDIDATES_FILE):
    raise FileNotFoundError(f"{CANDIDATES_FILE} not found.")
candidates_df = pd.read_csv(CANDIDATES_FILE)

if not os.path.exists(VOTES_FILE):
    pd.DataFrame(columns=["MOBILE","NAME","ELECTION","PARTY","DATE","TIME"]).to_csv(VOTES_FILE, index=False)

# -------------------- FACE VERIFICATION --------------------
def verify_face(threshold=0.60):
    # Use DirectShow backend to avoid MSMF errors on Windows. Try index 1 or 0.
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print("Error: Cannot open camera. Please check your webcam.")
        speak("Error: Cannot open camera. Please check your webcam.")
        return None, None

    speak(LANG_LABELS[language_mode]["welcome"])
    voters_df_local = pd.read_csv(VOTERS_FILE)
    embeddings = []
    for _, voter in voters_df_local.iterrows():
        photo_file = voter.get("PHOTO")
        if photo_file:
            emb_path = os.path.join("data/registered_faces", photo_file.replace(".jpg",".npy"))
            if os.path.exists(emb_path):
                emb = np.load(emb_path).reshape(1,-1)
                emb = emb / np.linalg.norm(emb)
                embeddings.append((str(voter["MOBILE"]), voter["NAME"], emb))

    while True:
        ret, frame = cap.read()
        if not ret:
            cv2.waitKey(50)
            continue

        cv2.imshow("Face Verification - Press Q to quit", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        # --- REMOVED --- The lines that save the image to a temporary file are gone.
        # temp_path = "temp_vote.jpg"
        # cv2.imwrite(temp_path, frame)

        try:
            # Pass the frame directly from the camera for huge performance gain
            temp_emb_obj = DeepFace.represent(
                img_path=frame, 
                model_name="VGG-Face", 
                enforce_detection=True,
                detector_backend='opencv' # Using a faster detector
            )
            temp_emb = np.array(temp_emb_obj[0]["embedding"]).reshape(1,-1)
            temp_emb = temp_emb / np.linalg.norm(temp_emb)
            
            from sklearn.metrics.pairwise import cosine_similarity
            for mobile, name, reg_emb in embeddings:
                sim = cosine_similarity(temp_emb, reg_emb)[0][0]
                if sim >= threshold:
                    cap.release()
                    cv2.destroyAllWindows()
                    # --- REMOVED --- No need to remove a file that was never created.
                    # os.remove(temp_path)
                    return mobile, name
                    
        except Exception as e:
            # This exception now just means a face was not found in the frame. We can safely ignore it.
            continue
            
        # --- REMOVED --- No temporary file to remove here either.
        # os.remove(temp_path)

    cap.release()
    cv2.destroyAllWindows()
    return None, None


# -------------------- FLASK APP --------------------
app = Flask(__name__)
app.secret_key = "secret123"

# -------------------- ELECTION CHOICE --------------------
@app.route("/", methods=["GET","POST"])
def choose_election():
    mobile = request.args.get("mobile")
    name = request.args.get("name")

    if mobile and name:
        session["voter_mobile"] = mobile
        session["voter_name"] = name

    if request.method=="POST":
        election_type = request.form.get("chunav")
        return redirect(f"/{election_type}_vote")

    return render_template("election_choice.html")

# -------------------- GENERIC VOTE HANDLER --------------------
def handle_vote(election_type, template_name):
    mobile = session.get("voter_mobile")
    name = session.get("voter_name")

    if not mobile or not name:
        speak(LANG_LABELS[language_mode]["face_not_recognized"])
        return render_template("face_not_recognized.html")

    if request.method == "POST":
        candidate = request.form.get("candidate")

        if not candidate:
            speak("Please select a valid candidate.")
            return render_template(template_name, error="Please select a candidate.")

        df = pd.read_csv(VOTES_FILE)
        df = df.dropna(subset=["MOBILE", "NAME"])
        df["MOBILE"] = df["MOBILE"].astype(str).str.strip()
        df["ELECTION"] = df["ELECTION"].astype(str).str.lower().str.strip()
        mobile_str = str(mobile).strip()
        election_type_lower = election_type.lower().strip()

        already_voted = df[
            (df["MOBILE"] == mobile_str) &
            (df["ELECTION"] == election_type_lower)
        ]

        if not already_voted.empty:
            speak(LANG_LABELS[language_mode]["already_voted"])
            return render_template("already_voted.html", voter_name=name, election=election_type)

        now = datetime.now()
        new_vote = pd.DataFrame([{
            "MOBILE": mobile_str,
            "NAME": name,
            "ELECTION": election_type_lower,
            "PARTY": candidate,
            "DATE": now.strftime("%Y-%m-%d"),
            "TIME": now.strftime("%H:%M:%S")
        }])
        
        df = pd.concat([df, new_vote], ignore_index=True)
        df.to_csv(VOTES_FILE, index=False)

        speak(f" आपने {candidate} को वोट दिया।")
        session.pop("voter_mobile", None)
        session.pop("voter_name", None)
        return render_template("thank_you.html", voter_name=name, candidate=candidate, election=election_type)

    # For a GET request, load candidates and render the voting page
    election_candidates = candidates_df[candidates_df['ELECTION'].str.lower() == election_type.lower()]
    return render_template(template_name, candidates=election_candidates.to_dict('records'))

# -------------------- ROUTES --------------------
@app.route("/vidhansabha_vote", methods=["GET","POST"])
def vidhan_vote():
    return handle_vote("vidhansabha","vidhan_vote.html")

@app.route("/loksabha_vote", methods=["GET","POST"])
def lok_vote():
    return handle_vote("loksabha","loksabha_vote.html")

@app.route("/rajyasabha_vote", methods=["GET","POST"])
def rajya_vote():
    return handle_vote("rajyasabha","rajyasabha_vote.html")

@app.route("/panchayat_vote", methods=["GET","POST"])
def panchayat_vote():
    return handle_vote("panchayat","panchayat_vote.html")

# -------------------- RUN FLASK --------------------
def run_flask_app():
    app.run(debug=False, use_reloader=False)

# -------------------- MAIN FLOW --------------------
def main():
    mobile, name = verify_face()
    if mobile is None:
        speak(LANG_LABELS[language_mode]["face_not_recognized"])
        print(LANG_LABELS[language_mode]["face_not_recognized"])
        return

    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()

    webbrowser.open(f"http://127.0.0.1:5000/?mobile={mobile}&name={name}")
    print(f"Browser opened for {name}. The server is running in the background.")
    print("Press CTRL+C in this terminal to stop the entire script for the next voter.")
    
    # --- CORRECTED --- The join() call is now removed. The script will exit, but the server thread will keep running.
    # flask_thread.join()

if __name__=="__main__":
    main()
