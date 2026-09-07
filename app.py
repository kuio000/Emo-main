import json

import os

from datetime import datetime



from flask import Flask, render_template, request, jsonify, redirect, url_for

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import inspect, text





# ====================

# Configuration

# ====================

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "development-only-change-me")



BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_DIR = os.path.join(BASE_DIR, "db")



# Changed: save captured images instead of webcam videos

IMAGE_SAVE_DIR = os.path.join(BASE_DIR, "captured_images")



os.makedirs(DB_DIR, exist_ok=True)

os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)



app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(DB_DIR, "CSProject.db")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["RESEARCH_CONTACT_NAME"] = os.environ.get(

    "RESEARCH_CONTACT_NAME", "Research Team"

)

app.config["RESEARCH_CONTACT_EMAIL"] = os.environ.get(

    "RESEARCH_CONTACT_EMAIL", "3155060W@student.gla.ac.uk"

)

app.config["PARTICIPANT_INFORMATION_URL"] = os.environ.get(

    "PARTICIPANT_INFORMATION_URL", ""

)

app.config["EXPERIMENT_VIDEO_URL"] = os.environ.get(

    "EXPERIMENT_VIDEO_URL", ""

)



# Keep this because many images may still be large

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024   # 500 MB upload cap



db = SQLAlchemy(app)





# ====================

# Database model

# ====================

class Participant(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)



    consent_given = db.Column(db.Boolean, default=False)

    consent_name = db.Column(db.String(200), nullable=True)

    consent_time = db.Column(db.DateTime, nullable=True)

    consent_signed_date = db.Column(db.Date, nullable=True)

    consent_responses = db.Column(db.Text, nullable=True)

    age = db.Column(db.Integer, nullable=True)

    ethnicity = db.Column(db.String(100), nullable=True)

    data_consent_option = db.Column(db.String(50), nullable=True)

    data_consent_submitted_at = db.Column(db.DateTime, nullable=True)



    # Keep the old field name to avoid changing the database structure.

    # Now this stores the image folder name, not a video filename.

    recording_filename = db.Column(db.String(300), nullable=True)

    recording_uploaded_at = db.Column(db.DateTime, nullable=True)



    phq9_score = db.Column(db.Integer, nullable=True)

    phq9_submitted_at = db.Column(db.DateTime, nullable=True)

    comedy_path = db.Column(db.String(500), nullable=True)

    neutral_path = db.Column(db.String(500), nullable=True)

    sad_path = db.Column(db.String(500), nullable=True)





# ====================

# Constants

# ====================

PHQ9_QUESTIONS = [

    "Little interest or pleasure in doing things?",

    "Feeling down, depressed, or hopeless?",

    "Trouble falling or staying asleep, or sleeping too much?",

    "Feeling tired or having little energy?",

    "Poor appetite or overeating?",

    "Feeling bad about yourself — or that you are a failure or have let yourself or your family down?",

    "Trouble concentrating on things, such as reading or watching TV?",

    "Moving or speaking so slowly that other people could have noticed? Or the opposite – being fidgety or restless?",

    "Thoughts that you would be better off dead, or of hurting yourself in some way?"

]



CONSENT_STATEMENTS = [

    "I confirm that I have read and understood the Participant Information Sheet for the above study and have had the opportunity to ask questions.",

    "I understand that my participation is voluntary and that I am free to withdraw at any time, without giving any reason.",

    "I consent to interviews and workshops being video-recorded.",

    "I consent to physiological data and self-reported scores being collected.",

    "I acknowledge that participants will be referred to by pseudonym.",

    "I acknowledge that there will be no effect on my grades/employment arising from my participation or non-participation in this research.",

    "All names and other material likely to identify individuals will be anonymised. Materials that are hard to anonymise will only be used for academic use with permission.",

    "The material will be treated as confidential and kept in secure storage at all times.",

    "The material will be retained in secure storage for use in future academic research.",

    "The material may be used in future publications, both print and online.",

    "I acknowledge the provision of a Privacy Notice in relation to this research project.",

    "Authenticated researchers may use my anonymised words in publications, reports, web pages, and other research outputs, only if they agree to preserve the confidentiality of the information as requested in this form."

]



ETHNICITY_OPTIONS = [

    "Asian or Asian British",

    "Black, African, Caribbean or Black British",

    "Mixed or multiple ethnic groups",

    "White",

    "Other ethnic group",

    "Prefer not to say"

]





# ====================

# Helpers

# ====================

def get_participant(participant_id):

    """Return Participant by id, or None if id is missing/not found."""

    if not participant_id:

        return None

    return Participant.query.get(participant_id)



# 根据PHQ9分数划分等级+建议文本

def get_phq_level(score):

    if score <= 4:

        level = "Minimal or no depression symptoms"

        suggestion = "Keep maintaining regular rest and social activities. Continue paying attention to your emotional state."

    elif score <=9:

        level = "Mild depression symptoms"

        suggestion = "Try regular exercise and communicate with relatives and friends. Adjust your work and rest schedule."

    elif score <=14:

        level = "Moderate depression symptoms"

        suggestion = "It is recommended to actively arrange relaxation activities. If low mood lasts more than two weeks, seek professional consultation."

    elif score <=19:

        level = "Moderately severe depression symptoms"

        suggestion = "You are suggested to contact a psychological counselor or general practitioner for further assessment."

    else:

        level = "Severe depression symptoms"

        suggestion = "Please seek professional mental health support as soon as possible."

    return level, suggestion



def ensure_participant_schema():

    """Add new Participant columns to existing SQLite databases."""

    inspector = inspect(db.engine)

    participant_columns = {

        column["name"] for column in inspector.get_columns(Participant.__tablename__)

    }



    columns_to_add = {

        "consent_signed_date": "DATE",

        "consent_responses": "TEXT",

        "age": "INTEGER",

        "ethnicity": "VARCHAR(100)",

        "data_consent_option": "VARCHAR(50)",

        "data_consent_submitted_at": "DATETIME"

    }



    with db.engine.begin() as connection:

        for column_name, column_type in columns_to_add.items():

            if column_name not in participant_columns:

                connection.execute(

                    text(

                        f"ALTER TABLE {Participant.__tablename__} "

                        f"ADD COLUMN {column_name} {column_type}"

                    )

                )





# ====================

# Experiment flow:

#   /  ->  /consent  ->  /data_consent  ->  /experiment

#      ->  /upload_recording  ->  /phq9  ->  result

# ====================



@app.route("/")

def welcome():

    """

    Landing page.

    Creates a participant record on visit.

    """

    participant = Participant()

    db.session.add(participant)

    db.session.commit()



    return render_template(

        "welcome.html",

        participant_id=participant.id,

        contact_name=app.config["RESEARCH_CONTACT_NAME"],

        contact_email=app.config["RESEARCH_CONTACT_EMAIL"],

        participant_information_url=app.config["PARTICIPANT_INFORMATION_URL"]

    )





@app.route("/data_consent", methods=["GET", "POST"])

def data_consent():

    """

    Intermediate data consent / information page.

    Saves the participant's webcam photo usage preference.

    """

    if request.method == "POST":

        participant_id = request.form.get("participant_id", type=int)

    else:

        participant_id = request.args.get("participant_id", type=int)



    participant = get_participant(participant_id)



    if not participant:

        return redirect(url_for("welcome"))



    if not participant.consent_given:

        return redirect(url_for("consent", participant_id=participant.id))



    if request.method == "POST":

        consent_option = request.form.get("consent_option")

        valid_options = {

            "open_research",

            "this_research_only",

            "immediate_deletion"

        }



        if consent_option not in valid_options:

            return "Please choose how your photos may be used.", 400



        participant.data_consent_option = consent_option

        participant.data_consent_submitted_at = datetime.utcnow()

        db.session.commit()



        return redirect(url_for("experiment", participant_id=participant.id))



    return render_template(

        "data_consent.html",

        participant_id=participant.id

    )





@app.route("/experiment")

def experiment():

    participant_id = request.args.get("participant_id", type=int)

    participant = get_participant(participant_id)



    if not participant:

        return redirect(url_for("welcome"))



    if not participant.consent_given:

        return redirect(url_for("consent", participant_id=participant.id))



    return render_template(

        "experiment.html",

        participant_id=participant.id,

        experiment_video_url=app.config["EXPERIMENT_VIDEO_URL"]

    )





VIDEO_ROOT = "./user_videos"

os.makedirs(VIDEO_ROOT, exist_ok=True)



@app.route('/upload_recording', methods=["POST"])

def upload_recording():

    participant_id = request.form.get("participant_id", type=int)

    video_type = request.form.get("video_type") # comedy / neutral / sad



    participant = get_participant(participant_id)

    if not participant:

        return jsonify({"success": False, "msg": "Participant not found"}), 400

    if not participant.consent_given:

        return jsonify({"success": False, "msg": "Consent required"}), 403



    if "video" not in request.files:

        return jsonify({"success": False, "msg": "No video file"}), 400



    video_file = request.files["video"]

    save_folder = os.path.join(VIDEO_ROOT, str(participant_id))

    os.makedirs(save_folder, exist_ok=True)

    save_filename = f"{video_type}.mp4"

    full_path = os.path.join(save_folder, save_filename)

    video_file.save(full_path)



    # 根据视频类型，存入对应字段

    if video_type == "comedy":

        participant.comedy_path = full_path

    elif video_type == "neutral":

        participant.neutral_path = full_path

    elif video_type == "sad":

        participant.sad_path = full_path



    db.session.commit()

    return jsonify({

        "success": True,

        "next_url": url_for("phq9", participant_id=participant.id)

    })





@app.route("/phq9", methods=["GET", "POST"])

def phq9():

    participant_id = request.args.get("participant_id", type=int)

    participant = get_participant(participant_id)



    if not participant:

        return redirect(url_for("welcome"))



    if request.method == "POST":

        scores = []



        for i in range(9):

            value = request.form.get(f"q{i}")

            if value is None:

                return f"Missing answer for question {i + 1}", 400

            scores.append(int(value))



        total_score = sum(scores)

        participant.phq9_score = total_score

        participant.phq9_submitted_at = datetime.utcnow()

        db.session.commit()



        # PHQ-9 等级判断【缩进在POST内部】

        level, suggestion = get_phq_level(total_score)

        # 面部反馈占位文字

        face_text = "At this stage, the platform collects facial video data for offline analysis. The automatic evaluation function will be updated in future versions."



        # 跳转我们新建的 result.html

        return render_template(

            "result.html",

            phq_score=total_score,

            depression_level=level,

            suggestion_text=suggestion,

            face_feedback=face_text

        )



    # GET访问：加载问卷页面

    return render_template(

        "phq9.html",

        questions=PHQ9_QUESTIONS,

        participant_id=participant.id

    )





# ====================

# Internal consent form

# ====================

@app.route("/consent", methods=["GET", "POST"])

def consent():

    participant_id = request.form.get("participant_id", type=int)

    if request.method == "GET":

        participant_id = request.args.get("participant_id", type=int)



    participant = get_participant(participant_id)

    if not participant:

        return redirect(url_for("welcome"))



    if request.method == "POST":

        participant_name = request.form.get("name", "").strip()

        age_value = request.form.get("age", type=int)

        ethnicity = request.form.get("ethnicity")

        final_consent = request.form.get("final_consent")

       

        if (

            not participant_name

            or age_value is None

            or not 0 <= age_value <= 120

            or ethnicity not in ETHNICITY_OPTIONS

            or final_consent not in {"agree", "disagree"}

        ):

            return render_template(

                "consent.html",

                participant_id=participant.id,

                consent_statements=CONSENT_STATEMENTS,

                ethnicity_options=ETHNICITY_OPTIONS,

                error="Please answer every question and provide a valid name, age, and ethnicity selection."

            ), 400



        participant.consent_given = final_consent == "agree"

        participant.consent_name = participant_name

        participant.age = age_value

        participant.ethnicity = ethnicity

        participant.consent_responses = json.dumps({

            "final_consent": final_consent

        })

        participant.consent_time = datetime.utcnow()

        db.session.commit()



        if not participant.consent_given:

            return render_template(

                "consent_declined.html",

                participant_id=participant.id

            )



        return redirect(url_for("data_consent", participant_id=participant.id))



    return render_template(

        "consent.html",

        participant_id=participant.id,

        ethnicity_options=ETHNICITY_OPTIONS

    )





# ====================

# Entry point

# ====================

with app.app_context():

    db.create_all()

    ensure_participant_schema()





if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(os.environ.get("PORT", "5000")),

        debug=os.environ.get("FLASK_DEBUG") == "1",

        #ssl_context="adhoc"

    )