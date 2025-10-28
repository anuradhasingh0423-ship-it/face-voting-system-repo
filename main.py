import csv
import webbrowser 
import secrets
import hashlib
import threading
import sys
import os
import tempfile
import pygame
import subprocess
import pandas as pd
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, session, request, redirect, url_for, flash, send_file, jsonify



# Optional voice libs (if installed)
try:
    import gtts
    HAVE_GTTS = True
except Exception:
    HAVE_GTTS = False

# Optional cv2 for fallback webcam capture in admin registration (if installed)
try:
    import cv2
    HAVE_CV2 = True
except Exception:
    HAVE_CV2 = False

# captcha
from captcha.image import ImageCaptcha

# Initialize pygame mixer (optional)
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Pygame mixer init failed (continuing without audio): {e}")

# ------------------- CONFIG / PATHS -------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "CHANGE_THIS_TO_A_SECRET_RANDOM_STRING"
app.config["SESSION_TYPE"] = "filesystem"

# Files and directories
ADMIN_USER_FILE = "admin_users.csv"
VOTES_FILE = "Votes.csv"
VOTES_DIRECTORY = "votes"
VOTING_STATE_FILE = "voting_state.json"

DATA_DIR = "data/admin_faces"      # for admin photos (simple)
ADMIN_CSV = "admin.csv"            # simple admin registration CSV

os.makedirs(VOTES_DIRECTORY, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ------------------- ELECTION TYPES -------------------
ELECTION_TYPES = {
    "vidhansabha": "Vidhan",
    "loksabha": "Loksabha",
    "rajyasabha": "Rajya",
    "panchayat": "Panchayat"
}

# ------------------- UTILS: voting state -------------------
def set_voting_state(active: bool):
    import json
    state = {"active": bool(active), "started_at": str(datetime.now()) if active else None}
    with open(VOTING_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

def get_voting_state():
    import json
    if not os.path.exists(VOTING_STATE_FILE):
        return {"active": False, "started_at": None}
    with open(VOTING_STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def is_voting_active():
    state = get_voting_state()
    return bool(state.get("active", False))

# ------------------- VOTE FUNCTIONS -------------------
def save_vote(votes_file, mobile, name, election, party):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    file_exists = os.path.isfile(votes_file)
    with open(votes_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["MOBILE","NAME","ELECTION","PARTY","DATE","TIME"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "MOBILE": mobile,
            "NAME": name,
            "ELECTION": election,
            "PARTY": party,
            "DATE": date_str,
            "TIME": time_str
        })

def has_voted(votes_file, voter_mobile, vote_type=None):
    if not voter_mobile or not os.path.exists(votes_file):
        return False
    try:
        df = pd.read_csv(votes_file, dtype=str)
        df['MOBILE'] = df['MOBILE'].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        df['ELECTION'] = df['ELECTION'].astype(str).str.strip()
    except Exception as e:
        print(f"Error reading {votes_file}: {e}")
        return False
    voter_mobile = str(voter_mobile).strip()
    if vote_type:
        election_name = ELECTION_TYPES.get(vote_type.lower())
        if not election_name:
            return False
        df = df[df['ELECTION'].str.lower() == election_name.lower()]
    return voter_mobile in df['MOBILE'].values

# ------------------- VOICE FEEDBACK (optional) -------------------
language_mode = 'hindi'
def play_voice(text):
    if not HAVE_GTTS:
        return
    def _play():
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            tts = gtts.gTTS(text=text, lang='hi' if language_mode=='hindi' else 'en')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
                tts.save(temp_path)
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            os.remove(temp_path)
        except Exception as e:
            print("Voice error:", e)
    threading.Thread(target=_play, daemon=True).start()

# ------------------- ADMIN AUTH (users stored in CSV) -------------------
def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def find_admin(username):
    if not os.path.exists(ADMIN_USER_FILE):
        return None
    with open(ADMIN_USER_FILE, 'r', newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if row and row[0] == username:
                return row
    return None

def add_user(username, password, sec_q, sec_a):
    if not os.path.exists(ADMIN_USER_FILE):
        with open(ADMIN_USER_FILE, 'w', newline='', encoding='utf-8'):
            pass
    if find_admin(username):
        return False
    with open(ADMIN_USER_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([username, hash_pw(password), sec_q, hash_pw(sec_a.lower())])
    return True

def check_credentials(username, password):
    admin = find_admin(username)
    return admin and hash_pw(password) == admin[1]

def check_security_answer(username, answer):
    admin = find_admin(username)
    return admin and hash_pw(answer.lower()) == admin[3]

def update_password(username, new_password):
    admins = []
    found = False
    if not os.path.exists(ADMIN_USER_FILE):
        return False
    with open(ADMIN_USER_FILE, 'r', newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if row and row[0] == username:
                row[1] = hash_pw(new_password)
                found = True
            admins.append(row)
    if found:
        with open(ADMIN_USER_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(admins)
        return True
    return False

# Decorator: check consistent session key
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Access denied. Admin login required.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------- HELPERS: simple admin registration (no DeepFace) -------------------
def generate_admin_id(length=6):
    import random, string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def save_base64_image(data_url, save_path):
    header, encoded = data_url.split(",", 1)
    import base64
    data = base64.b64decode(encoded)
    with open(save_path, "wb") as f:
        f.write(data)

# ------------------- ROUTES -------------------
@app.route('/')
@app.route('/welcome')
def welcome():
    # show whether voting active to visitors
    voting = is_voting_active()
    return render_template("welcome.html", role="admin" if session.get('admin_logged_in') else "voter", voting_active=voting)

@app.route('/choose_registration')
def choose_registration():
    choice = request.args.get("role")  # 'voter' or 'admin'
    if choice == "voter":
        # Launch add_faces.py (voter registration script) as external process if exists
        script_path = os.path.join(os.path.dirname(__file__), "add_faces.py")
        if os.path.exists(script_path):
            try:
                subprocess.Popen([sys.executable, script_path], shell=False)
                flash("Voter registration launched!", "success")
            except Exception as e:
                flash(f"Failed to launch voter registration: {e}", "danger")
        else:
            flash("Voter registration script not found.", "danger")
        return redirect(url_for("welcome"))
    elif choice == "admin":
        return redirect(url_for("admin_registration"))
    else:
        flash("Invalid choice")
        return redirect(url_for("welcome"))


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        # logic to reset password
        pass
    return render_template("forgot.html")


# ------------------- AUTH (signup/login) -------------------
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=="POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        conf_pw = request.form.get("confirm_password","")
        security_q = request.form.get("security_q")
        security_a = request.form.get("security_a")
        captcha_input = request.form.get("captcha","")
        captcha_correct = session.get("captcha_text","")
        if not username or not password or not conf_pw or not security_q or not security_a:
            flash("Fill all fields.", "danger")
        elif password != conf_pw:
            flash("Passwords do not match.", "danger")
        elif not captcha_correct or captcha_input.lower() != captcha_correct.lower():
            flash("Invalid captcha.", "danger")
        elif add_user(username, password, security_q, security_a):
            flash("Admin registered successfully. Please login.", "success")
            return redirect(url_for("login"))
        else:
            flash("That username already exists.", "danger")
    return render_template("signup.html")

# ------------------- AUTH (signup/login) -------------------
# In your main.py file:

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=="POST":
        # CRITICAL FIX: Strip all user inputs of whitespace
        username = request.form.get("username","").strip()
        password = request.form.get("password","") # Don't strip password if it allows spaces
        captcha_input = request.form.get("captcha","").strip() # Strip captcha input
        
        # Get session value, ensure it's also stripped and lowercased for safe comparison
        captcha_correct = session.get("captcha_text", "").strip().lower()

        if not username or not password:
            flash("Fill all fields.", "danger")
        
        # Ensure comparison is done on stripped, lowercased values for the captcha
        elif captcha_input.lower() != captcha_correct:
            # Note: We don't remove the flash message here, as the template handles it
            flash("Invalid captcha.", "danger")
        
        # Check actual credentials
        elif check_credentials(username, password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("registration_page"))
        
        else:
            flash("Incorrect username or password.", "danger")
        
        # If POST fails, render the login template so the user can try again
        # We render the template directly to show the error messages (via flash)
        return render_template("login.html") # <--- RENDER ON POST FAILURE (FIXED)

    # On GET request (initial page load), render the login template
    return render_template("login.html")
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("registration_page"))


# ------------------- REGISTRATION -------------------
@app.route('/registration', methods=['GET','POST'])
def registration_page():
    # This page is the "Select Registration Type" page (registration.html)
    if request.method == 'POST':
        # If the user posts to this page, they might be attempting voter registration 
        # from an old link. Better to redirect to the proper form.
        flash("Please use the 'Voter Registration' link.", "warning")
        return redirect(url_for('registration_page'))
    
    # Renders the selection page (registration.html)
    return render_template("registration.html")


@app.route('/voter_registration')
def voter_registration():
    """
    Launches the external add_faces.py script via subprocess.
    The GET/POST logic for web forms is removed.
    """
    script_path = os.path.join(os.path.dirname(__file__), "add_faces.py")
    try:
        if os.path.exists(script_path):
            # Use subprocess.Popen to execute the tkinter script (add_faces.py)
            subprocess.Popen([sys.executable, script_path], shell=False)
            flash("Voter Registration window opened successfully! Please look at the new window.", "success")
        else:
            flash("Error: add_faces.py script not found!", "danger")
    except Exception as e:
        flash(f"Error launching Voter Registration: {e}", "danger")
    
    # Redirect back to the registration selection page
    return redirect(url_for('registration_page'))





# Launch voter registration script (if you use external add_faces script)
@app.route('/launch_add_faces')
@admin_login_required
def launch_add_faces():
    script_path = os.path.join(os.path.dirname(__file__), "add_faces.py")
    try:
        if os.path.exists(script_path):
            subprocess.Popen([sys.executable, script_path], shell=False)
            flash("Voter registration launched! Follow instructions in the new window.", "success")
        else:
            flash("add_faces.py not found.", "danger")
    except Exception as e:
        flash(f"Failed to launch registration: {e}", "danger")
    return redirect(url_for('registration_page'))

# ------------------- CAPTCHA -------------------
@app.route('/captcha')
def captcha():
    generated_captcha = secrets.token_hex(3)
    session['captcha_text'] = generated_captcha
    image = ImageCaptcha(width=180, height=60)
    data = image.generate(generated_captcha)
    return send_file(data, mimetype='image/png')


# Election overview: summary of votes per election
@app.route('/election_overview')
@admin_login_required
def election_overview():
    votes_file = VOTES_FILE
    summary = {}
    if os.path.exists(votes_file):
        df = pd.read_csv(votes_file, dtype=str)
        for election_type in df['ELECTION'].unique():
            summary[election_type] = df[df['ELECTION']==election_type]['PARTY'].value_counts().to_dict()
    return render_template('election_overview.html', summary=summary)


# ------------------- DASHBOARD -------------------
@app.route('/dashboard')
@admin_login_required
def dashboard():
    # Show results only when voting stopped (so admin can declare)
    voting_active = is_voting_active()
    vote_summary = {}
    if os.path.exists(VOTES_FILE):
        try:
            df = pd.read_csv(VOTES_FILE, dtype=str)
            df['ELECTION'] = df['ELECTION'].str.strip()
            for election_type in df['ELECTION'].unique():
                # admin can see counts live but full declared results only after voting stops
                vote_summary[election_type] = df[df['ELECTION']==election_type]['PARTY'].value_counts().to_dict()
        except Exception as e:
            flash(f"Error reading votes: {e}", "danger")
    return render_template("dashboard.html", voting_active=voting_active, vote_summary=vote_summary)

# ------------------- ADMIN START/STOP VOTING -------------------
@app.route("/admin/start_voting", methods=["POST"])
@admin_login_required
def admin_start_voting():
    try:
        set_voting_state(True)
        state = get_voting_state()
        flash(f"Voting started at {state.get('started_at')}", "success")
    except Exception as e:
        flash(f"Failed to start voting: {e}", "danger")
    return redirect(url_for('dashboard'))

@app.route("/admin/stop_voting", methods=["POST"])
@admin_login_required
def admin_stop_voting():
    try:
        set_voting_state(False)
        flash("Voting stopped.", "info")
    except Exception as e:
        flash(f"Failed to stop voting: {e}", "danger")
    return redirect(url_for('dashboard'))

# ------------------- START VOTING STATION (voter uses this to verify face & begin) -------------------
# Note: verify_face should return [mobile, name] or None — this function is expected in give_vote.py
try:
    from give_vote import verify_face
except Exception:
    # fallback stub (so app runs even without give_vote)
    def verify_face():
        return None

@app.route('/start_voting_station_route')
def start_voting_station_route():
    # Voter-accessible route to begin face verification and voting. Voting must be active.
    if not is_voting_active():
        flash("Voting has not started yet. कृपया बाद में प्रयास करें।", "warning")
        return redirect(url_for('welcome'))

    try:
        result = verify_face()
    except Exception as e:
        flash(f"Face verification error: {e}", "danger")
        return redirect(url_for('welcome'))

    if not result or result[0] is None:
        
        flash("Face not recognized. कृपया पुनः प्रयास करें।", "warning")
        play_voice("Face not recognized.")
        return redirect(url_for('welcome'))

    voter_mobile = str(result[0]).strip()
    voter_name = str(result[1]).strip() if len(result) > 1 and result[1] else "Voter"

    already_voted_in = []
    for key, name in ELECTION_TYPES.items():
        if has_voted(VOTES_FILE, voter_mobile, key):
            already_voted_in.append(name)

    if len(already_voted_in) == len(ELECTION_TYPES):
        message = f"You have already voted in all available elections: {', '.join(already_voted_in)}"
        flash(message, "info")
        play_voice(message)
        session['last_voter_name'] = voter_name
        session['already_voted_elections'] = already_voted_in
        return redirect(url_for('already_voted'))

    session['voter_mobile'] = voter_mobile
    session['voter_name'] = voter_name
    flash(f"Face recognized: Welcome {voter_name}", "success")
    play_voice(f"Welcome {voter_name}")
    return redirect(url_for('choose_election'))

# ------------------- CHOOSE ELECTION / VOTE PAGES / SUBMIT (unchanged logic) -------------------
@app.route('/choose_election', methods=['GET','POST'])
def choose_election():
    voter_mobile = session.get("voter_mobile")
    if not voter_mobile:
        flash("Your session has expired. Please verify your face again.", "warning")
        return redirect(url_for('welcome'))

    remaining_elections = []
    for key, name in ELECTION_TYPES.items():
        if not has_voted(VOTES_FILE, voter_mobile, key):
            remaining_elections.append((key, name))

    if not remaining_elections:
        flash("आप पहले ही सभी चुनावों में वोट दे चुके हैं।")
        return redirect(url_for('already_voted'))

    if request.method == 'POST':
        chunav_type = request.form.get("chunav")
        
        # --- FIX ---
        
        # Step 1: Check if the user selected anything at all. (You added this correctly)
        if not chunav_type:
            flash("Please select an election.", "warning")
            return redirect(url_for('choose_election'))

        # Step 2: Check if the selected election is one they are actually allowed to vote in.
        allowed = [key for key, _ in remaining_elections]
        if chunav_type not in allowed:
            flash("You are not eligible to vote in that election or have already voted.", "danger")
            return redirect(url_for('choose_election'))

        # --- END FIX ---

        # If both checks pass, proceed.
        session['chunav_type'] = chunav_type
        return redirect(url_for(f"{chunav_type}_vote_page"))

    return render_template('election_choice.html', remaining_elections=remaining_elections)

@app.route('/thank_you')
def thank_you():
    voter_name = session.pop("last_voter_name", "Voter")
    return render_template("thank_you.html", voter_name=voter_name)


@app.route('/already_voted')
def already_voted():
    voter_name = session.pop("last_voter_name", "Voter")
    voted_elections = session.pop("already_voted_elections", [])
    return render_template("already_voted.html", voter_name=voter_name, voted_elections=voted_elections)


# load candidates
def load_candidates(csv_file):
    candidates = []
    if os.path.exists(csv_file):
        with open(csv_file,"r",encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['ELECTION'] = row.get('ELECTION','').strip()
                candidates.append(row)
    return candidates

@app.route('/vidhansabha_vote')
def vidhansabha_vote_page():
    candidates = load_candidates("candidates.csv")
    return render_template("vidhan_vote.html", candidates=candidates)

@app.route('/loksabha_vote')
def loksabha_vote_page():
    candidates = load_candidates("candidates.csv")
    return render_template("loksabha_vote.html", candidates=candidates)

@app.route('/rajyasabha_vote')
def rajyasabha_vote_page():
    candidates = load_candidates("candidates.csv")
    return render_template("rajya_vote.html", candidates=candidates)

@app.route('/panchayat_vote')
def panchayat_vote_page():
    candidates = load_candidates("candidates.csv")
    return render_template("panchayat_vote.html", candidates=candidates)

def submit_vote_generic(vote_type, election_name):
    voter_name = session.get("voter_name", "Voter")
    voter_mobile = session.get("voter_mobile", "")
    candidate_id = request.form.get("candidate")
    votes_file = VOTES_FILE

    if not voter_mobile:
        flash("Voter identity lost. Please restart voting process.")
        return redirect(url_for('welcome'))

    if not candidate_id:
        flash("Please select a candidate.")
        return redirect(url_for(f"{vote_type}_vote_page"))

    if has_voted(votes_file, voter_mobile, vote_type):
        flash(f"आप पहले ही {ELECTION_TYPES[vote_type]} चुनाव में वोट दे चुके हैं।")
        session['last_voter_name'] = voter_name
        session.pop("voter_name", None)
        session.pop("voter_mobile", None)
        return redirect(url_for('already_voted'))

    save_vote(votes_file, voter_mobile, voter_name, election_name, candidate_id)

    # voice
    play_voice(f"आपने {candidate_id} को वोट दिया।")

    session['last_voter_name'] = voter_name
    session.pop("voter_name", None)
    session.pop("voter_mobile", None)

    return redirect(url_for("thank_you"))


@app.route('/launch_desktop_dashboard')
@admin_login_required
def launch_desktop_dashboard():
    """
    This function safely launches the external vote_dashboard.py script.
    """
    script_path = os.path.join(os.path.dirname(__file__), "vote_dashboard.py")
    
    try:
        if os.path.exists(script_path):
            # Use subprocess.Popen to run the script in a new window
            subprocess.Popen([sys.executable, script_path], shell=False)
            flash("Live Desktop Dashboard window has been opened!", "success")
        else:
            flash("Error: vote_dashboard.py script not found.", "danger")
    except Exception as e:
        flash(f"Failed to launch the desktop dashboard: {e}", "danger")
        
    # Always redirect back to the main web dashboard
    return redirect(url_for('dashboard'))


@app.route('/submit_vidhansabha_vote', methods=['POST'])
def submit_vidhansabha_vote():
    return submit_vote_generic("vidhansabha","Vidhan")

@app.route('/submit_loksabha_vote', methods=['POST'])
def submit_loksabha_vote():
    return submit_vote_generic("loksabha","Loksabha")

@app.route('/submit_rajyasabha_vote', methods=['POST'])
def submit_rajyasabha_vote():
    return submit_vote_generic("rajyasabha","Rajya")

@app.route('/submit_panchayat_vote', methods=['POST'])
def submit_panchayat_vote():
    return submit_vote_generic("panchayat","Panchayat")


# ------------------- RESULTS / TALLY -------------------
def tally_votes(election_csv, candidate_csv):
    candidates = {}
    if os.path.exists(candidate_csv):
        with open(candidate_csv,"r",encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidates[row["CANDIDATE"]] = row["CANDIDATE"]
    vote_counts = {cid:0 for cid in candidates}
    if os.path.exists(election_csv):
        with open(election_csv,"r",encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("PARTY")
                if cid in vote_counts:
                    vote_counts[cid] += 1
    return vote_counts

@app.route('/results_vidhansabha')
@admin_login_required
def results_vidhansabha():
    # Only allow seeing final declared result if voting stopped
    if is_voting_active():
        flash("Results will be available after voting ends.", "warning")
        return redirect(url_for('dashboard'))
    votes = tally_votes(VOTES_FILE, "candidates.csv")
    return render_template("results.html", results=votes.items(), election="Vidhan Sabha")

@app.route('/results_loksabha')
@admin_login_required
def results_loksabha():
    if is_voting_active():
        flash("Results will be available after voting ends.", "warning")
        return redirect(url_for('dashboard'))
    votes = tally_votes(VOTES_FILE, "candidates.csv")
    return render_template("results.html", results=votes.items(), election="Lok Sabha")

@app.route('/results_rajyasabha')
@admin_login_required
def results_rajyasabha():
    if is_voting_active():
        flash("Results will be available after voting ends.", "warning")
        return redirect(url_for('dashboard'))
    votes = tally_votes(VOTES_FILE, "candidates.csv")
    return render_template("results.html", results=votes.items(), election="Rajya Sabha")

@app.route('/results_panchayat')
@admin_login_required
def results_panchayat():
    if is_voting_active():
        flash("Results will be available after voting ends.", "warning")
        return redirect(url_for('dashboard'))
    votes = tally_votes(VOTES_FILE, "candidates.csv")
    return render_template("results.html", results=votes.items(), election="Panchayat")

# ------------------- OTHER UTILITIES -------------------
@app.route('/clear_data', methods=['POST'])
@admin_login_required
def clear_data():
    votes_file = VOTES_FILE
    try:
        if os.path.exists(votes_file):
            with open(votes_file, 'r', newline='') as f:
                reader = csv.reader(f)
                headers = next(reader)
            with open(votes_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            flash("All votes have been reset. Voters can vote again.", "success")
        else:
            flash("Votes file not found. No data cleared.", "danger")
    except Exception as e:
        flash(f"Error clearing votes: {e}", "danger")
    return redirect(url_for('dashboard'))

@app.route('/dashboard_live')
@admin_login_required
def dashboard_live_route():
    votes_file = VOTES_FILE
    vote_summary = {}
    if os.path.exists(votes_file):
        df = pd.read_csv(votes_file)
        for election_type in df['ELECTION'].unique():
            vote_summary[election_type] = df[df['ELECTION']==election_type]['PARTY'].value_counts().to_dict()
    return render_template('dashboard_live.html', vote_summary=vote_summary)





@app.route('/set_language')
def set_language():
    global language_mode
    lang = request.args.get('lang', 'hindi')
    language_mode = 'hindi' if lang=='hindi' else 'english'
    return ('', 204)


# Import the Blueprint here, right before registration.
from admin_registration import admin_bp

# Register the Blueprint with a prefix for clarity.
app.register_blueprint(admin_bp, url_prefix='/admin_portal')

# --- NOW, DEFINE THE LAUNCHER ROUTE ---
@app.route('/admin_register')
def admin_register():
    """Directs the user to the Admin Portal routes defined by the Blueprint."""
    # This URL is resolved by Flask to: http://127.0.0.1:5000/admin_portal/admin_registration
    return redirect(url_for('admin_bp.admin_registration'))


# ------------------- RUN -------------------
if __name__=="__main__":
    # set debug True if you want (development)
    app.run(debug=False, host="0.0.0.0", port=5000)


