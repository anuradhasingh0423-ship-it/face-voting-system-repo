# import csv
# import secrets
# import hashlib
# import threading
# import sys
# import os
# import gtts
# import tempfile
# import pygame
# import pandas as pd
# from datetime import datetime

# ELECTION_TYPES = {
#     "vidhan": "Vidhan",
#     "loksabha": "Loksabha",
#     "rajya": "Rajya",
#     "panchayat": "Panchayat"
# }


# def save_vote(votes_file, mobile, name, election, party):
#     """Save a vote to Votes.csv with date and time."""
#     now = datetime.now()
#     date_str = now.strftime("%Y-%m-%d")
#     time_str = now.strftime("%H:%M:%S")

#     file_exists = os.path.isfile(votes_file)
#     with open(votes_file, 'a', newline='', encoding='utf-8') as f:
#         writer = csv.DictWriter(f, fieldnames=["MOBILE","NAME","ELECTION","PARTY","DATE","TIME"])
#         if not file_exists:
#             writer.writeheader()
#         writer.writerow({
#             "MOBILE": mobile,
#             "NAME": name,
#             "ELECTION": election,
#             "PARTY": party,
#             "DATE": date_str,
#             "TIME": time_str
#         })




# def has_voted(votes_file, voter_mobile, election=None):
#     """Check if a voter has already voted in a specific election."""
#     if not voter_mobile or not os.path.exists(votes_file):
#         return False

#     df = pd.read_csv(votes_file, dtype=str)
#     df['MOBILE'] = df['MOBILE'].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
#     df['ELECTION'] = df['ELECTION'].astype(str).str.strip().str.lower()

#     voter_mobile = str(voter_mobile).strip()
#     if election:
#         election = election.strip().lower()
#         df = df[df['ELECTION'] == election]

#     return voter_mobile in df['MOBILE'].values





# language_mode = 'hindi'  # or 'english'

# def play_voice(text):
#     def _play():
#         try:
#             tts = gtts.gTTS(text=text, lang='hi' if language_mode=='hindi' else 'en')
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
#                 temp_path = fp.name
#                 tts.save(temp_path)

#             if pygame.mixer.get_init() is None:
#                 pygame.mixer.init()
#             if pygame.mixer.music.get_busy():
#                 pygame.mixer.music.stop()
#             pygame.mixer.music.load(temp_path)
#             pygame.mixer.music.play()
#             while pygame.mixer.music.get_busy():
#                 pygame.time.Clock().tick(10)
#             os.remove(temp_path)
#         except Exception as e:
#             print("Voice error:", e)
#     threading.Thread(target=_play, daemon=True).start()


# from flask import (
#     Flask, render_template, session, request, redirect,
#     url_for, flash, send_file, jsonify
# )
# from flask_session import Session
# from captcha.image import ImageCaptcha
# from give_vote import verify_face

# import subprocess
# import json

# app = Flask(__name__)
# app.config["SECRET_KEY"] = "CHANGE_THIS_TO_A_SECRET_RANDOM_STRING"
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)

# ADMIN_USER_FILE = "admin_users.csv"
# VOTES_DIRECTORY = "votes"

# # Ensure the votes directory exists
# if not os.path.exists(VOTES_DIRECTORY):
#     os.makedirs(VOTES_DIRECTORY)

# def hash_pw(password):
#     return hashlib.sha256(password.encode()).hexdigest()

# def find_admin(username):
#     if not os.path.exists(ADMIN_USER_FILE):
#         return None
#     with open(ADMIN_USER_FILE, 'r', newline='', encoding='utf-8') as f:
#         for row in csv.reader(f):
#             if row and row[0] == username:
#                 return row
#     return None

# def add_user(username, password, sec_q, sec_a):
#     if not os.path.exists(ADMIN_USER_FILE):
#         with open(ADMIN_USER_FILE, 'w', newline='', encoding='utf-8'):
#             pass
#     if find_admin(username):
#         return False
#     with open(ADMIN_USER_FILE, 'a', newline='', encoding='utf-8') as f:
#         writer = csv.writer(f)
#         writer.writerow([username, hash_pw(password), sec_q, hash_pw(sec_a.lower())])
#         return True

# def check_credentials(username, password):
#     admin = find_admin(username)
#     return admin and hash_pw(password) == admin[1]

# def check_security_answer(username, answer):
#     admin = find_admin(username)
#     return admin and hash_pw(answer.lower()) == admin[3]

# def update_password(username, new_password):
#     admins = []
#     found = False
#     with open(ADMIN_USER_FILE, 'r', newline='', encoding='utf-8') as f:
#         for row in csv.reader(f):
#             if row and row[0] == username:
#                 row[1] = hash_pw(new_password)
#                 found = True
#             admins.append(row)
#     if found:
#         with open(ADMIN_USER_FILE, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.writer(f)
#             writer.writerows(admins)
#         return True
#     return False



# @app.route('/captcha')
# def captcha():
#     generated_captcha = secrets.token_hex(3)
#     session['captcha_text'] = generated_captcha
#     image = ImageCaptcha(width=180, height=60)
#     data = image.generate(generated_captcha)
#     return send_file(data, mimetype='image/png')

# def admin_login_required(func):
#     from functools import wraps
#     @wraps(func)
#     def wrapped(*args, **kwargs):
#         if not session.get("admin_logged_in"):
#             flash("Please log in as admin.")
#             return redirect(url_for("login"))
#         return func(*args, **kwargs)
#     return wrapped

# @app.route('/')
# @app.route('/welcome')
# def welcome():
#     return render_template("welcome.html")

# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == "POST":
#         username = request.form.get("username", "").strip()
#         password = request.form.get("password", "")
#         conf_pw = request.form.get("confirm_password", "")
#         security_q = request.form.get("security_q")
#         security_a = request.form.get("security_a")
#         captcha_input = request.form.get("captcha", "")
#         captcha_correct = session.get("captcha_text", "")
#         if not username or not password or not conf_pw or not security_q or not security_a:
#             flash("Fill all fields.")
#         elif password != conf_pw:
#             flash("Passwords do not match.")
#         elif captcha_input.lower() != captcha_correct.lower():
#             flash("Invalid captcha.")
#         elif add_user(username, password, security_q, security_a):
#             flash("Admin registered successfully. Please login.")
#             return redirect(url_for("login"))
#         else:
#             flash("That username already exists.")
#     return render_template("signup.html")

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == "POST":
#         username = request.form.get("username", "")
#         password = request.form.get("password", "")
#         captcha_input = request.form.get("captcha", "")
#         captcha_correct = session.get("captcha_text", "")
#         if not username or not password:
#             flash("Fill all fields.")
#         elif captcha_input.lower() != captcha_correct.lower():
#             flash("Invalid captcha.")
#         elif check_credentials(username, password):
#             session["admin_logged_in"] = True
#             session["admin_username"] = username
#             flash(f"Welcome back, {username}!")
#             return redirect(url_for("dashboard"))
#         else:
#             flash("Incorrect username or password.")
#     return render_template("login.html")

# @app.route('/forgot', methods=['GET', 'POST'])
# def forgot():
#     if request.method == "POST":
#         username = request.form.get("username", "").strip()
#         security_a = request.form.get("security_a", "")
#         new_pw = request.form.get("new_password", "")
#         confirm_pw = request.form.get("confirm_password", "")
#         user_row = find_admin(username)
#         if not user_row:
#             flash("No such username.")
#             return render_template("forgot.html")
#         elif not security_a:
#             return render_template("forgot.html", username=username, security_q=user_row[2])
#         elif new_pw != confirm_pw:
#             flash("Passwords do not match.")
#             return render_template("forgot.html", username=username, security_q=user_row[2])
#         elif check_security_answer(username, security_a):
#             update_password(username, new_pw)
#             flash("Password reset successful. Please log in.")
#             return redirect(url_for('login'))
#         else:
#             flash("Incorrect answer to the security question.")
#             return render_template("forgot.html", username=username, security_q=user_row[2])
#     return render_template("forgot.html")

# @app.route('/logout')
# def logout():
#     session.clear()
#     flash("Logged out successfully.")
#     return redirect(url_for("login"))

# def run_script(script_name):
#     script_path = os.path.join(os.path.dirname(__file__), script_name)
#     python_exe = sys.executable

#     def target():
#         import subprocess
#         subprocess.Popen([python_exe, script_path])

#     threading.Thread(target=target).start()

# @app.route('/dashboard')
# @admin_login_required
# def dashboard():
#     return render_template("dashboard.html")

# @app.route('/add_faces')
# @admin_login_required
# def add_faces_route():
#     run_script("add_faces.py")
#     flash("Launching face registration...")
#     return redirect(url_for('dashboard'))

# # THIS IS THE ROUTE FOR THE 'START VOTING STATION' BUTTON
# # @app.route('/start_voting_station_route')
# # @admin_login_required
# # def start_voting_station_route():
# #     run_script("give_vote.py")
# #     flash("Launching voting station...")
# #     return redirect(url_for('dashboard'))

# @app.route('/start_voting_station_route')
# @admin_login_required
# def start_voting_station_route():
#     """
#     Run face verification (synchronously) using verify_face() from give_vote.py.
#     If face is recognized, store voter info in session and redirect to choose_election.
#     If not, flash error and return to dashboard.
#     """
#     try:
#         result = verify_face()  # expected: (mobile, name) or None (or a string/mobile)
#     except Exception as e:
#         flash(f"Face verification error: {e}")
#         return redirect(url_for('dashboard'))

#     if not result:
#         flash("Face not recognized. Please try again.")
#         return redirect(url_for('dashboard'))

#     # Handle flexible return types from verify_face
#     voter_mobile = None
#     voter_name = None
#     if isinstance(result, (tuple, list)):
#         if len(result) >= 1:
#             voter_mobile = result[0]
#         if len(result) >= 2:
#             voter_name = result[1]
#     else:
#         # single string returned (mobile or name)
#         voter_mobile = str(result)

#     # Save into session so vote submission routes can use it
#     session['voter_mobile'] = str(voter_mobile) if voter_mobile is not None else None
#     session['voter_name'] = voter_name

#     display_name = voter_name or voter_mobile or "Voter"
#     flash(f"Face recognized: {display_name}")
#     return redirect(url_for('choose_election'))



# @app.route('/vote_dashboard')
# @admin_login_required
# def dashboard_live_route():
#     run_script("vote_dashboard.py")
#     flash("Launching live vote dashboard...")
#     return redirect(url_for('dashboard'))

# @app.route('/clear_data', methods=['POST'])
# @admin_login_required
# def clear_data():
#     try:
#         election_files = ["vidhan_votes.csv", "loksabha_votes.csv", "rajyasabha_votes.csv", "panchayat_votes.csv"]
#         for fname in election_files:
#             if os.path.exists(fname):
#                 os.remove(fname)
#         if os.path.exists("voters.csv"):
#             os.remove("voters.csv")
#         data_dir = "data/registered_faces"
#         if os.path.exists(data_dir):
#             for file in os.listdir(data_dir):
#                 os.remove(os.path.join(data_dir, file))
#             os.rmdir(data_dir)
#         flash("All voter and vote data cleared.")
#     except Exception as e:
#         flash(f"Failed to clear data: {e}")
#     return redirect(url_for('dashboard'))

# def load_candidates(csv_file):
#     candidates = []
#     if os.path.exists(csv_file):
#         with open(csv_file, "r", encoding="utf-8") as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 row['ELECTION'] = row['ELECTION'].strip()  # clean election column
#                 candidates.append(row)
#     return candidates


# def has_voted(votes_file, voter_mobile, election=None):
#     """Check if a voter has already voted in a specific election."""
#     if not os.path.exists(votes_file):
#         return False
#     df = pd.read_csv(votes_file)
#     if election:
#         df = df[df['ELECTION'] == election]
#     return voter_mobile in df['MOBILE'].values

# @app.route('/choose_election', methods=['GET', 'POST'])
# @admin_login_required
# def choose_election():
#     if request.method == 'POST':
#         chunav_type = request.form.get("chunav")
#         allowed = ['vidhansabha', 'loksabha', 'rajyasabha', 'panchayat']
#         if chunav_type not in allowed:
#             flash("Please select a valid election type.")
#             return redirect(url_for('choose_election'))
#         session['chunav_type'] = chunav_type
#         if chunav_type == 'vidhansabha':
#             return redirect(url_for('vidhan_vote_page'))
#         elif chunav_type == 'loksabha':
#             return redirect(url_for('loksabha_vote_page'))
#         elif chunav_type == 'rajyasabha':
#             return redirect(url_for('rajya_vote_page'))
#         else:
#             return redirect(url_for('panchayat_vote_page'))
#     return render_template('election_choice.html')
# @app.route('/vidhan_vote')
# @admin_login_required
# def vidhan_vote_page():
#     candidates = load_candidates("candidates.csv")  # use full CSV
#     return render_template("vidhan_vote.html", candidates=candidates)

# @app.route('/loksabha_vote')
# @admin_login_required
# def loksabha_vote_page():
#     candidates = load_candidates("candidates.csv")
#     return render_template("loksabha_vote.html", candidates=candidates)

# @app.route('/rajya_vote')
# @admin_login_required
# def rajya_vote_page():
#     candidates = load_candidates("candidates.csv")
#     return render_template("rajya_vote.html", candidates=candidates)

# @app.route('/panchayat_vote')
# @admin_login_required
# def panchayat_vote_page():
#     candidates = load_candidates("candidates.csv")
#     return render_template("panchayat_vote.html", candidates=candidates)

# # ---------------------- Vote Submission Routes ----------------------

# @app.route('/submit_vidhan_vote', methods=['POST'])
# @admin_login_required
# def submit_vidhan_vote():
#     voter_name = session.get("voter_name", "Voter")
#     voter_mobile = session.get("voter_mobile", "")
#     candidate_id = request.form.get("candidate")
#     votes_file = "Votes.csv"

#     if not candidate_id:
#         flash("Please select a candidate.")
#         return redirect(url_for('vidhan_vote_page'))

#     # Prevent duplicate voting
#     # In submit_vidhan_vote:
#     if has_voted(votes_file, voter_mobile, "vidhan"):
#         session['last_voter_name'] = voter_name
#         return redirect(url_for('already_voted'))
    
#     # Save vote
#     save_vote(votes_file, voter_mobile, voter_name, "Vidhan", candidate_id)

#     # Candidate name lookup
#     candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Vidhan"]
#     candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

#     # Voice feedback
#     play_voice(f"आपने {candidate_name} को वोट दिया।")

#     # Prepare thank you page
#     session['last_voter_name'] = voter_name
#     session.pop("voter_name", None)
#     session.pop("voter_mobile", None)

#     return redirect(url_for("thank_you", voter_name=voter_name))


# @app.route('/submit_loksabha_vote', methods=['POST'])
# @admin_login_required
# def submit_loksabha_vote():
#     voter_name = session.get("voter_name", "Voter")
#     voter_mobile = session.get("voter_mobile", "")
#     candidate_id = request.form.get("candidate")
#     votes_file = "Votes.csv"

#     if not candidate_id:
#         flash("Please select a candidate.")
#         return redirect(url_for('loksabha_vote_page'))
    
#     # In submit_loksabha_vote:
#     if has_voted(votes_file, voter_mobile, "Loksabha"):
#         session['last_voter_name'] = voter_name
#         return redirect(url_for('already_voted'))


#     save_vote(votes_file, voter_mobile, voter_name, "Loksabha", candidate_id)

#     candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Loksabha"]
#     candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

#     play_voice(f"आपने {candidate_name} को वोट दिया।")

#     session['last_voter_name'] = voter_name
#     session.pop("voter_name", None)
#     session.pop("voter_mobile", None)

#     return redirect(url_for("thank_you", voter_name=voter_name))


# @app.route('/submit_rajya_vote', methods=['POST'])
# @admin_login_required
# def submit_rajya_vote():
#     voter_name = session.get("voter_name", "Voter")
#     voter_mobile = session.get("voter_mobile", "")
#     candidate_id = request.form.get("candidate")
#     votes_file = "Votes.csv"

#     if not candidate_id:
#         flash("Please select a candidate.")
#         return redirect(url_for('rajya_vote_page'))

    
# # In submit_rajya_vote:
#     if has_voted(votes_file, voter_mobile, "Rajya"):
#         session['last_voter_name'] = voter_name
#         return redirect(url_for('already_voted'))

#     save_vote(votes_file, voter_mobile, voter_name, "Rajya", candidate_id)

#     candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Rajya"]
#     candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

#     play_voice(f"आपने {candidate_name} को वोट दिया।")

#     session['last_voter_name'] = voter_name
#     session.pop("voter_name", None)
#     session.pop("voter_mobile", None)

#     return redirect(url_for("thank_you", voter_name=voter_name))


# @app.route('/submit_panchayat_vote', methods=['POST'])
# @admin_login_required
# def submit_panchayat_vote():
#     voter_name = session.get("voter_name", "Voter")
#     voter_mobile = session.get("voter_mobile", "")
#     candidate_id = request.form.get("candidate")
#     votes_file = "Votes.csv"

#     if not candidate_id:
#         flash("Please select a candidate.")
#         return redirect(url_for('panchayat_vote_page'))

#     # In submit_panchayat_vote:
#     if has_voted(votes_file, voter_mobile, "Panchayat"):
#         session['last_voter_name'] = voter_name
#         return redirect(url_for('already_voted'))

#     save_vote(votes_file, voter_mobile, voter_name, "Panchayat", candidate_id)

#     candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Panchayat"]
#     candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

#     play_voice(f"आपने {candidate_name} को वोट दिया।")

#     session['last_voter_name'] = voter_name
#     session.pop("voter_name", None)
#     session.pop("voter_mobile", None)

#     return redirect(url_for("thank_you", voter_name=voter_name))


# def tally_votes(election_csv, candidate_csv):
#     candidates = {}
#     if os.path.exists(candidate_csv):
#         with open(candidate_csv, "r", encoding="utf-8") as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 candidates[row["CANDIDATE"]] = row["CANDIDATE"]


#     vote_counts = {cid: 0 for cid in candidates}
#     if os.path.exists(election_csv):
#         with open(election_csv, "r", encoding="utf-8") as f:
#             reader = csv.reader(f)
#             for row in reader:
#                 cid = row[1].strip()
#                 if cid in vote_counts:
#                     vote_counts[cid] += 1
#     return [(candidates[cid], vote_counts[cid]) for cid in candidates]

# @app.route('/results_vidhan')
# @admin_login_required
# def results_vidhan():
#     results = tally_votes("vidhan_votes.csv", "vidhan_candidates.csv")
#     return render_template("results_generic.html",
#                            election="Vidhan Sabha",
#                            results=results)

# @app.route('/results_loksabha')
# @admin_login_required
# def results_loksabha():
#     results = tally_votes("loksabha_votes.csv", "loksabha_candidates.csv")
#     return render_template("results_generic.html",
#                            election="Lok Sabha",
#                            results=results)

# @app.route('/results_rajya')
# @admin_login_required
# def results_rajya():
#     results = tally_votes("rajyasabha_votes.csv", "rajyasabha_candidates.csv")
#     return render_template("results_generic.html",
#                            election="Rajya Sabha",
#                            results=results)

# @app.route('/results_panchayat')
# @admin_login_required
# def results_panchayat():
#     results = tally_votes("panchayat_votes.csv", "panchayat_candidates.csv")
#     return render_template("results_generic.html",
#                            election="Panchayat",
#                            results=results)

# @app.route('/thank_you')
# @admin_login_required
# def thank_you():
#     voter_name = session.get("last_voter_name", "Voter")
#     # Clear the last_voter_name after displaying
#     session.pop('last_voter_name', None)
#     return render_template("thank_you.html", voter_name=voter_name)

# @app.route('/already_voted')
# @admin_login_required
# def already_voted():
#     voter_name = session.get("last_voter_name", "Voter")
#     # Clear the last_voter_name after displaying
#     session.pop('last_voter_name', None)
#     return render_template("already_voted.html", voter_name=voter_name)



# if __name__ == "__main__":
#     print("Starting Flask admin panel on http://127.0.0.1:5000/")
#     app.run(debug=True, use_reloader=False)












import csv
import secrets
import hashlib
import threading
import sys
import os
import gtts
import tempfile
import pygame
import pandas as pd
from datetime import datetime
from functools import wraps # Import for admin_login_required

# Initialize pygame mixer once
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Pygame mixer initialization failed: {e}")

ELECTION_TYPES = {
    "vidhan": "Vidhan",
    "loksabha": "Loksabha",
    "rajya": "Rajya",
    "panchayat": "Panchayat"
}


def save_vote(votes_file, mobile, name, election, party):
    """Save a vote to Votes.csv with date and time."""
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


# --- The correct, robust has_voted function ---
def has_voted(votes_file, voter_mobile, election=None):
    """Check if a voter has already voted in a specific election."""
    # Ensure voter_mobile is valid before proceeding
    if not voter_mobile or not os.path.exists(votes_file):
        return False

    try:
        df = pd.read_csv(votes_file, dtype=str)
        # Normalize MOBILE column: remove whitespace and trailing '.0' from float conversion
        df['MOBILE'] = df['MOBILE'].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        # Normalize ELECTION column: remove whitespace and convert to lowercase
        df['ELECTION'] = df['ELECTION'].astype(str).str.strip().str.lower()
    except Exception as e:
        print(f"Error reading or normalizing Votes.csv: {e}")
        return False
    
    voter_mobile = str(voter_mobile).strip()
    
    if election:
        # Normalize the incoming election parameter for filtering
        election = election.strip().lower()
        df = df[df['ELECTION'] == election]

    return voter_mobile in df['MOBILE'].values


language_mode = 'hindi'  # or 'english'

def play_voice(text):
    def _play():
        try:
            # Re-initialize mixer if it was quit or never started
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


from flask import (
    Flask, render_template, session, request, redirect,
    url_for, flash, send_file, jsonify
)
from flask_session import Session
from captcha.image import ImageCaptcha
from give_vote import verify_face # Assuming verify_face is importable

import subprocess
import json

app = Flask(__name__)
app.config["SECRET_KEY"] = "CHANGE_THIS_TO_A_SECRET_RANDOM_STRING"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

ADMIN_USER_FILE = "admin_users.csv"
VOTES_DIRECTORY = "votes"

# Ensure the votes directory exists
if not os.path.exists(VOTES_DIRECTORY):
    os.makedirs(VOTES_DIRECTORY)

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



@app.route('/captcha')
def captcha():
    generated_captcha = secrets.token_hex(3)
    session['captcha_text'] = generated_captcha
    image = ImageCaptcha(width=180, height=60)
    data = image.generate(generated_captcha)
    return send_file(data, mimetype='image/png')

def admin_login_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in as admin.")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapped

@app.route('/')
@app.route('/welcome')
def welcome():
    return render_template("welcome.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conf_pw = request.form.get("confirm_password", "")
        security_q = request.form.get("security_q")
        security_a = request.form.get("security_a")
        captcha_input = request.form.get("captcha", "")
        captcha_correct = session.get("captcha_text", "")
        if not username or not password or not conf_pw or not security_q or not security_a:
            flash("Fill all fields.")
        elif password != conf_pw:
            flash("Passwords do not match.")
        elif captcha_input.lower() != captcha_correct.lower():
            flash("Invalid captcha.")
        elif add_user(username, password, security_q, security_a):
            flash("Admin registered successfully. Please login.")
            return redirect(url_for("login"))
        else:
            flash("That username already exists.")
    return render_template("signup.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        captcha_input = request.form.get("captcha", "")
        captcha_correct = session.get("captcha_text", "")
        if not username or not password:
            flash("Fill all fields.")
        elif captcha_input.lower() != captcha_correct.lower():
            flash("Invalid captcha.")
        elif check_credentials(username, password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            flash(f"Welcome back, {username}!")
            return redirect(url_for("dashboard"))
        else:
            flash("Incorrect username or password.")
    return render_template("login.html")

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        security_a = request.form.get("security_a", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")
        user_row = find_admin(username)
        if not user_row:
            flash("No such username.")
            return render_template("forgot.html")
        elif not security_a:
            return render_template("forgot.html", username=username, security_q=user_row[2])
        elif new_pw != confirm_pw:
            flash("Passwords do not match.")
            return render_template("forgot.html", username=username, security_q=user_row[2])
        elif check_security_answer(username, security_a):
            update_password(username, new_pw)
            flash("Password reset successful. Please log in.")
            return redirect(url_for('login'))
        else:
            flash("Incorrect answer to the security question.")
            return render_template("forgot.html", username=username, security_q=user_row[2])
    return render_template("forgot.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("login"))

def run_script(script_name):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    python_exe = sys.executable

    def target():
        import subprocess
        # Use Popen to run the script asynchronously
        subprocess.Popen([python_exe, script_path])

    threading.Thread(target=target).start()

@app.route('/dashboard')
@admin_login_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/add_faces')
@admin_login_required
def add_faces_route():
    run_script("add_faces.py")
    flash("Launching face registration...")
    return redirect(url_for('dashboard'))


@app.route('/start_voting_station_route')
@admin_login_required
def start_voting_station_route():
    """
    Run face verification (synchronously) using verify_face() from give_vote.py.
    If face is recognized, store voter info in session and redirect to choose_election.
    If not, flash error and return to dashboard.
    """
    # Clear any previous voter session data before starting a new verification
    session.pop('voter_mobile', None)
    session.pop('voter_name', None)
    
    try:
        # verify_face() is assumed to block until a result is found or it times out
        result = verify_face()  # expected: (mobile, name) or None
    except Exception as e:
        flash(f"Face verification error: {e}")
        return redirect(url_for('dashboard'))

    if not result:
        flash("Face not recognized. Please try again.")
        return redirect(url_for('dashboard'))

    # Handle flexible return types from verify_face
    voter_mobile = None
    voter_name = None
    if isinstance(result, (tuple, list)):
        if len(result) >= 1:
            voter_mobile = result[0]
        if len(result) >= 2:
            voter_name = result[1]
    else:
        # single string returned (mobile or name)
        voter_mobile = str(result)
        
    # Final check for a valid mobile number (essential for has_voted)
    if not voter_mobile or str(voter_mobile).strip() == "":
        flash("Voter mobile number not retrieved. Please try again.")
        return redirect(url_for('dashboard'))


    # Save into session so vote submission routes can use it
    session['voter_mobile'] = str(voter_mobile)
    session['voter_name'] = voter_name

    display_name = voter_name or voter_mobile or "Voter"
    flash(f"Face recognized: {display_name}")
    return redirect(url_for('choose_election'))



@app.route('/vote_dashboard')
@admin_login_required
def dashboard_live_route():
    run_script("vote_dashboard.py")
    flash("Launching live vote dashboard...")
    return redirect(url_for('dashboard'))

@app.route('/clear_data', methods=['POST'])
@admin_login_required
def clear_data():
    try:
        # Clear main votes file and election-specific result files
        vote_files = ["Votes.csv", "vidhan_votes.csv", "loksabha_votes.csv", "rajyasabha_votes.csv", "panchayat_votes.csv"]
        for fname in vote_files:
            if os.path.exists(fname):
                os.remove(fname)
        
        # Clear voter registration data
        if os.path.exists("voters.csv"):
            os.remove("voters.csv")
        data_dir = "data/registered_faces"
        if os.path.exists(data_dir):
            for file in os.listdir(data_dir):
                os.remove(os.path.join(data_dir, file))
            # os.rmdir(data_dir) # Removed rmdir to prevent error if dir is not empty
        
        flash("All voter and vote data cleared.")
    except Exception as e:
        flash(f"Failed to clear data: {e}")
    return redirect(url_for('dashboard'))

def load_candidates(csv_file):
    candidates = []
    if os.path.exists(csv_file):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Ensure ELECTION column is stripped of whitespace
                row['ELECTION'] = row.get('ELECTION', '').strip()
                candidates.append(row)
    return candidates

@app.route('/choose_election', methods=['GET', 'POST'])
@admin_login_required
def choose_election():
    # --- CRITICAL FIX: Check if a voter has successfully verified their face ---
    voter_mobile = session.get("voter_mobile")
    
    if not voter_mobile:
        # If voter_mobile is missing (either cleared after a vote, or user came directly here)
        flash("Please verify your face at the 'Start Voting Station' to begin voting.")
        # Force redirection to the dashboard to ensure the correct flow starts with face verification
        return redirect(url_for('dashboard')) 
    # --- END CRITICAL FIX ---
        
    if request.method == 'POST':
        chunav_type = request.form.get("chunav")
        allowed = ['vidhansabha', 'loksabha', 'rajyasabha', 'panchayat']
        
        if chunav_type not in allowed:
            flash("Please select a valid election type.")
            return redirect(url_for('choose_election'))
        
        session['chunav_type'] = chunav_type
        # Redirect to the correct voting page
        if chunav_type == 'vidhansabha':
            return redirect(url_for('vidhan_vote_page'))
        elif chunav_type == 'loksabha':
            return redirect(url_for('loksabha_vote_page'))
        elif chunav_type == 'rajyasabha':
            return redirect(url_for('rajya_vote_page'))
        else:
            return redirect(url_for('panchayat_vote_page'))
            
    return render_template('election_choice.html')

@app.route('/vidhan_vote')
@admin_login_required
def vidhan_vote_page():
    candidates = load_candidates("candidates.csv")  # use full CSV
    return render_template("vidhan_vote.html", candidates=candidates)

@app.route('/loksabha_vote')
@admin_login_required
def loksabha_vote_page():
    candidates = load_candidates("candidates.csv")
    return render_template("loksabha_vote.html", candidates=candidates)

@app.route('/rajya_vote')
@admin_login_required
def rajya_vote_page():
    candidates = load_candidates("candidates.csv")
    return render_template("rajya_vote.html", candidates=candidates)

@app.route('/panchayat_vote')
@admin_login_required
def panchayat_vote_page():
    candidates = load_candidates("candidates.csv")
    return render_template("panchayat_vote.html", candidates=candidates)

# ---------------------- Vote Submission Routes ----------------------

@app.route('/submit_vidhan_vote', methods=['POST'])
@admin_login_required
def submit_vidhan_vote():
    voter_name = session.get("voter_name", "Voter")
    voter_mobile = session.get("voter_mobile", "")
    candidate_id = request.form.get("candidate")
    votes_file = "Votes.csv"
    
    # Voter validation
    if not voter_mobile:
        flash("Voter identity lost. Please restart voting process.")
        return redirect(url_for('dashboard'))
    
    if not candidate_id:
        flash("Please select a candidate.")
        return redirect(url_for('vidhan_vote_page'))

    # --- CRITICAL FIX: Standardize election name passed to has_voted ---
    if has_voted(votes_file, voter_mobile, "vidhansabha"):
        session['last_voter_name'] = voter_name
        # Clear session to force re-verification if they try to navigate back
        session.pop("voter_name", None)
        session.pop("voter_mobile", None)
        return redirect(url_for('already_voted'))
    
    # Save vote (uses the capitalized name "Vidhan")
    save_vote(votes_file, voter_mobile, voter_name, "Vidhan", candidate_id)

    # Candidate name lookup (can be simplified if candidate_id contains full name)
    candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Vidhan"]
    candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

    # Voice feedback
    play_voice(f"आपने {candidate_name} को वोट दिया।")

    # Prepare thank you page and clear session
    session['last_voter_name'] = voter_name
    session.pop("voter_name", None)
    session.pop("voter_mobile", None)

    return redirect(url_for("thank_you", voter_name=voter_name))


@app.route('/submit_loksabha_vote', methods=['POST'])
@admin_login_required
def submit_loksabha_vote():
    voter_name = session.get("voter_name", "Voter")
    voter_mobile = session.get("voter_mobile", "")
    candidate_id = request.form.get("candidate")
    votes_file = "Votes.csv"

    # Voter validation
    if not voter_mobile:
        flash("Voter identity lost. Please restart voting process.")
        return redirect(url_for('dashboard'))
    
    if not candidate_id:
        flash("Please select a candidate.")
        return redirect(url_for('loksabha_vote_page'))
    
    # --- CRITICAL FIX: Standardize election name passed to has_voted ---
    if has_voted(votes_file, voter_mobile, "loksabha"):
        session['last_voter_name'] = voter_name
        # Clear session to force re-verification if they try to navigate back
        session.pop("voter_name", None)
        session.pop("voter_mobile", None)
        return redirect(url_for('already_voted'))


    save_vote(votes_file, voter_mobile, voter_name, "Loksabha", candidate_id)

    candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Loksabha"]
    candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

    play_voice(f"आपने {candidate_name} को वोट दिया।")

    session['last_voter_name'] = voter_name
    session.pop("voter_name", None)
    session.pop("voter_mobile", None)

    return redirect(url_for("thank_you", voter_name=voter_name))


@app.route('/submit_rajya_vote', methods=['POST'])
@admin_login_required
def submit_rajya_vote():
    voter_name = session.get("voter_name", "Voter")
    voter_mobile = session.get("voter_mobile", "")
    candidate_id = request.form.get("candidate")
    votes_file = "Votes.csv"

    # Voter validation
    if not voter_mobile:
        flash("Voter identity lost. Please restart voting process.")
        return redirect(url_for('dashboard'))

    if not candidate_id:
        flash("Please select a candidate.")
        return redirect(url_for('rajya_vote_page'))

    
    # --- CRITICAL FIX: Standardize election name passed to has_voted ---
    if has_voted(votes_file, voter_mobile, "rajyasabha"):
        session['last_voter_name'] = voter_name
        # Clear session to force re-verification if they try to navigate back
        session.pop("voter_name", None)
        session.pop("voter_mobile", None)
        return redirect(url_for('already_voted'))

    save_vote(votes_file, voter_mobile, voter_name, "Rajya", candidate_id)

    candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Rajya"]
    candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

    play_voice(f"आपने {candidate_name} को वोट दिया।")

    session['last_voter_name'] = voter_name
    session.pop("voter_name", None)
    session.pop("voter_mobile", None)

    return redirect(url_for("thank_you", voter_name=voter_name))


@app.route('/submit_panchayat_vote', methods=['POST'])
@admin_login_required
def submit_panchayat_vote():
    voter_name = session.get("voter_name", "Voter")
    voter_mobile = session.get("voter_mobile", "")
    candidate_id = request.form.get("candidate")
    votes_file = "Votes.csv"

    # Voter validation
    if not voter_mobile:
        flash("Voter identity lost. Please restart voting process.")
        return redirect(url_for('dashboard'))

    if not candidate_id:
        flash("Please select a candidate.")
        return redirect(url_for('panchayat_vote_page'))

    # --- CRITICAL FIX: Standardize election name passed to has_voted ---
    if has_voted(votes_file, voter_mobile, "panchayat"):
        session['last_voter_name'] = voter_name
        # Clear session to force re-verification if they try to navigate back
        session.pop("voter_name", None)
        session.pop("voter_mobile", None)
        return redirect(url_for('already_voted'))

    save_vote(votes_file, voter_mobile, voter_name, "Panchayat", candidate_id)

    candidates = [c for c in load_candidates("candidates.csv") if c["ELECTION"] == "Panchayat"]
    candidate_name = next((c["CANDIDATE"] for c in candidates if c["CANDIDATE"] == candidate_id), candidate_id)

    play_voice(f"आपने {candidate_name} को वोट दिया।")

    session['last_voter_name'] = voter_name
    session.pop("voter_name", None)
    session.pop("voter_mobile", None)

    return redirect(url_for("thank_you", voter_name=voter_name))


def tally_votes(election_csv, candidate_csv):
    candidates = {}
    if os.path.exists(candidate_csv):
        with open(candidate_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidates[row["CANDIDATE"]] = row["CANDIDATE"]


    vote_counts = {cid: 0 for cid in candidates}
    if os.path.exists(election_csv):
        with open(election_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 1:
                    cid = row[1].strip()
                    if cid in vote_counts:
                        vote_counts[cid] += 1
    return [(candidates[cid], vote_counts[cid]) for cid in candidates]

@app.route('/results_vidhan')
@admin_login_required
def results_vidhan():
    results = tally_votes("vidhan_votes.csv", "vidhan_candidates.csv")
    return render_template("results_generic.html",
                           election="Vidhan Sabha",
                           results=results)

@app.route('/results_loksabha')
@admin_login_required
def results_loksabha():
    results = tally_votes("loksabha_votes.csv", "loksabha_candidates.csv")
    return render_template("results_generic.html",
                           election="Lok Sabha",
                           results=results)

@app.route('/results_rajya')
@admin_login_required
def results_rajya():
    results = tally_votes("rajyasabha_votes.csv", "rajyasabha_candidates.csv")
    return render_template("results_generic.html",
                           election="Rajya Sabha",
                           results=results)

@app.route('/results_panchayat')
@admin_login_required
def results_panchayat():
    results = tally_votes("panchayat_votes.csv", "panchayat_candidates.csv")
    return render_template("results_generic.html",
                           election="Panchayat",
                           results=results)

@app.route('/thank_you')
@admin_login_required
def thank_you():
    voter_name = session.get("last_voter_name", "Voter")
    # Clear the last_voter_name after displaying
    session.pop('last_voter_name', None)
    return render_template("thank_you.html", voter_name=voter_name)

@app.route('/already_voted')
@admin_login_required
def already_voted():
    voter_name = session.get("last_voter_name", "Voter")
    # Clear the last_voter_name after displaying
    session.pop('last_voter_name', None)
    return render_template("already_voted.html", voter_name=voter_name)


if __name__ == "__main__":
    print("Starting Flask admin panel on http://127.0.0.1:5000/")
    app.run(debug=True, use_reloader=False)