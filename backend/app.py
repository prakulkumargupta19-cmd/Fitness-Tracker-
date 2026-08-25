"""Athlete Tracker authentication server with reusable email OTP workflows."""
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import json, os, secrets, smtplib, sqlite3, ssl
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "athlete_tracker.db")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
OTP_MINUTES = 10
app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("SECRET_KEY", "athlete-tracker-development-secret-change-me"), PERMANENT_SESSION_LIFETIME=timedelta(days=7), SESSION_COOKIE_SAMESITE="Lax")
CORS(app, supports_credentials=True)

def get_db():
    db = sqlite3.connect(DATABASE); db.row_factory = sqlite3.Row; return db
def now(): return datetime.now(timezone.utc)
def generate_otp(): return f"{secrets.randbelow(1_000_000):06d}"

def print_otp_to_terminal(email, otp, purpose):
    print("\n" + "=" * 70)
    print("🔐 ATHLETE TRACKER OTP")
    print(f"📌 Purpose : {purpose}")
    print(f"📧 Email   : {email}")
    print(f"🔢 OTP     : {otp}")
    print(f"⏱️ Expires : {OTP_MINUTES} minutes")
    print("=" * 70 + "\n")
def canonical_role(role): return "player" if str(role or "").lower() == "student" else str(role or "").lower()
def display_role(role): return "Student" if role == "player" else role.capitalize()
def valid_password(password): return len(password) >= 8
def init_db():
    """
    Initialize the database using schema.sql.

    The schema file is the single source of truth for database
    structure. It uses CREATE TABLE IF NOT EXISTS, so restarting
    Flask will NOT delete existing data.
    """

    db = get_db()

    try:
        # Keep SQLite foreign-key enforcement enabled.
        db.execute("PRAGMA foreign_keys = ON")

        # Locate schema.sql in the same backend directory.
        schema_path = os.path.join(BASE_DIR, "schema.sql")

        # Read and execute the complete schema.
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()

        db.executescript(schema_sql)
        db.commit()

        app.logger.info("Database schema initialized successfully.")

    except (OSError, sqlite3.Error) as error:
        db.rollback()
        app.logger.error("Database initialization failed: %s", error)
        raise

    finally:
        db.close()


def send_email(recipient, subject, body):
    username,password=os.getenv("MAIL_USERNAME"),os.getenv("MAIL_PASSWORD")
    if not username or not password:
        app.logger.warning("Email not sent: MAIL_USERNAME and MAIL_PASSWORD are not configured"); return False
    message=EmailMessage(); message["Subject"],message["From"],message["To"]=subject,os.getenv("MAIL_FROM",username),recipient; message.set_content(body)
    try:
        with smtplib.SMTP(os.getenv("MAIL_SERVER","smtp.gmail.com"),int(os.getenv("MAIL_PORT","587")),timeout=15) as server:
            server.starttls(context=ssl.create_default_context()); server.login(username,password); server.send_message(message)
        return True
    except (OSError,smtplib.SMTPException,ValueError) as error:
        app.logger.error("Email delivery failed: %s",error); return False

def send_otp_email(email,name,purpose,otp):
    action="password reset" if purpose == "password_reset" else "account verification"
    return send_email(email,f"Athlete Tracker – {action.title()} OTP",f"Hello {name},\n\nYour Athlete Tracker {action} OTP is:\n\n{otp}\n\nThis OTP expires in {OTP_MINUTES} minutes.\n\nThank you,\nAthlete Tracker Team")
def send_account_created_email(email,name,role):
    return send_email(email,"Athlete Tracker Account Created Successfully",f"Hello {name},\n\nCongratulations!\n\nYour Athlete Tracker account has been successfully created.\n\nAccount Type: {display_role(role)}\n\nYou can now log in and access your dashboard.\n\nThank you,\nAthlete Tracker Team")
def send_password_reset_success_email(email,name):
    return send_email(email,"Password Reset Successful",f"Hello {name},\n\nYour Athlete Tracker password has been reset successfully.\n\nIf you did not perform this action, please contact the administrator.\n\nThank you,\nAthlete Tracker Team")

def save_otp(email,purpose,otp,payload=""):
    db=get_db()
    try:
        db.execute("UPDATE otp_requests SET used=1 WHERE email=? AND purpose=? AND used=0",(email,purpose))
        db.execute("INSERT INTO otp_requests (email,purpose,otp_hash,payload,expires_at,created_at) VALUES (?,?,?,?,?,?)",(email,purpose,generate_password_hash(otp),payload,(now()+timedelta(minutes=OTP_MINUTES)).isoformat(),now().isoformat())); db.commit()
    finally: db.close()
def get_otp(email,purpose):
    db=get_db()
    try:return db.execute("SELECT * FROM otp_requests WHERE email=? AND purpose=? AND used=0 ORDER BY id DESC LIMIT 1",(email,purpose)).fetchone()
    finally:db.close()
def verify_otp(email,purpose,otp,consume=False):
    record=get_otp(email,purpose)
    if not record or datetime.fromisoformat(record["expires_at"]) < now(): return None,"OTP expired. Please request a new OTP."
    if record["attempts"] >= 5:return None,"Too many incorrect attempts. Please request a new OTP."
    if not check_password_hash(record["otp_hash"],otp):
        db=get_db()
        try:db.execute("UPDATE otp_requests SET attempts=attempts+1 WHERE id=?",(record["id"],));db.commit()
        finally:db.close()
        return None,"Invalid OTP"
    db=get_db()
    try:db.execute("UPDATE otp_requests SET verified=1,used=? WHERE id=?",(1 if consume else 0,record["id"]));db.commit()
    finally:db.close()
    return record,None
def new_code(db,role):
    prefix={"admin":"ADM","coach":"COA","player":"ATH"}[role]; existing={r[0] for r in db.execute("SELECT user_code FROM users WHERE user_code LIKE ?",(prefix+"%",))}; number=1
    while f"{prefix}{number:03d}" in existing:number+=1
    return f"{prefix}{number:03d}"
def establish_session(user):
    session.clear();session.permanent=True;session.update(user_id=user["id"],user_code=user["user_code"],user_name=user["name"],user_email=user["email"],role=user["role"])
    if user["role"]=="admin":session.update(admin_id=user["id"],admin_name=user["name"],admin_email=user["email"],admin_user_code=user["user_code"])

@app.get("/")
def home():return send_from_directory(FRONTEND_DIR,"index.html")
@app.get("/<path:asset_path>")
def frontend_asset(asset_path):return send_from_directory(FRONTEND_DIR,asset_path)

def signup(data,forced_role=None):
    name,email,password=str(data.get("name"," ")).strip(),str(data.get("email","")).strip().lower(),str(data.get("password",""));role=forced_role or canonical_role(data.get("role"))
    if not name or not email or "@" not in email or not valid_password(password) or role not in {"player","coach","admin"}:return None,(jsonify(success=False,message="Enter a name, valid email, and password of at least 8 characters."),400)
    db=get_db()
    try:
        if db.execute("SELECT 1 FROM users WHERE lower(email)=?",(email,)).fetchone():return None,(jsonify(success=False,message="Email already registered"),400)
    finally:db.close()
    payload=json.dumps({"name":name,"email":email,"password_hash":generate_password_hash(password),"role":role,"sport":data.get("sport") or None,"contact_number":data.get("contact_number") or None,"gender":data.get("gender") or None,"date_of_birth":data.get("date_of_birth") or None})
    otp=generate_otp(); print_otp_to_terminal(email, otp, "Account Signup"); save_otp(email,"signup",otp,payload)
    if not send_otp_email(email,name,"signup",otp):return None,(jsonify(success=False,message="Email service is not configured or OTP delivery failed."),503)
    return email,None
@app.post("/api/register")
def register():
    _,error=signup(request.get_json(silent=True) or {});return error or (jsonify(success=True,message="OTP sent to your email"),201)
@app.post("/api/admin-signup")
def admin_signup():
    _,error=signup(request.get_json(silent=True) or {},"admin");return error or (jsonify(success=True,message="OTP sent to your email"),201)

def resend_signup():
    data=request.get_json(silent=True) or {};email=str(data.get("email","")).strip().lower();record=get_otp(email,"signup")
    if not record:return jsonify(success=False,message="Signup session expired. Please register again."),400
    payload=json.loads(record["payload"]);otp=generate_otp(); print_otp_to_terminal(email, otp, "Signup OTP Resend"); save_otp(email,"signup",otp,record["payload"])
    if not send_otp_email(email,payload["name"],"signup",otp):return jsonify(success=False,message="Email service is not configured or OTP delivery failed."),503
    return jsonify(success=True,message="New OTP sent to your email")
@app.post("/api/account-verification/send")
@app.post("/api/admin-signup/resend-otp")
def resend_signup_otp():return resend_signup()

def finish_signup():
    data=request.get_json(silent=True) or {};email,otp=str(data.get("email","")).strip().lower(),str(data.get("otp","")).strip()
    if not email or len(otp)!=6:return jsonify(success=False,message="Email and a 6-digit OTP are required"),400
    record,error=verify_otp(email,"signup",otp,True)
    if error:return jsonify(success=False,message=error),400
    payload=json.loads(record["payload"]);db=get_db()
    try:
        if db.execute("SELECT 1 FROM users WHERE lower(email)=?",(email,)).fetchone():return jsonify(success=False,message="Email already registered"),400
        code=new_code(db,payload["role"]);cursor=db.execute("INSERT INTO users (user_code,name,email,password_hash,role,sport,contact_number,gender,date_of_birth,email_verified) VALUES (?,?,?,?,?,?,?,?,?,1)",(code,payload["name"],email,payload["password_hash"],payload["role"],payload["sport"],payload["contact_number"],payload["gender"],payload["date_of_birth"]));db.commit();user=db.execute("SELECT * FROM users WHERE id=?",(cursor.lastrowid,)).fetchone()
    except sqlite3.Error as error:
        db.rollback();app.logger.error("Signup database error: %s",error);return jsonify(success=False,message="Unable to create account"),500
    finally:db.close()
    establish_session(user);send_account_created_email(email,user["name"],user["role"])
    return jsonify(success=True,message="Account verified successfully",user_code=user["user_code"],user={k:user[k] for k in ("id","name","email","role","user_code")})
@app.post("/api/account-verification/verify")
@app.post("/api/admin-signup/verify-otp")
def verify_signup_otp():return finish_signup()

@app.post("/api/login")
def login():
    data=request.get_json(silent=True) or {};email,password=str(data.get("email","")).strip().lower(),str(data.get("password",""));role=canonical_role(data.get("role","player"));db=get_db()
    try:user=db.execute("SELECT * FROM users WHERE lower(email)=? AND role=?",(email,role)).fetchone()
    finally:db.close()
    if not user or not check_password_hash(user["password_hash"],password):return jsonify(success=False,message="Invalid email or password"),401
    establish_session(user);return jsonify(success=True,message="Login successful",user={k:user[k] for k in ("id","name","email","role","user_code")})

@app.post("/api/admin-login")
def admin_login():
    data=request.get_json(silent=True) or {};email,password=str(data.get("email","")).strip().lower(),str(data.get("password",""));db=get_db()
    try:user=db.execute("SELECT * FROM users WHERE lower(email)=? AND role='admin'",(email,)).fetchone()
    finally:db.close()
    if not user or not check_password_hash(user["password_hash"],password):return jsonify(success=False,message="Invalid admin email or password"),401
    otp=generate_otp(); print_otp_to_terminal(email, otp, "Admin Login"); save_otp(email,"admin_login",otp,str(user["id"]))
    if not send_otp_email(email,user["name"],"admin login",otp):return jsonify(success=False,message="Email service is not configured or OTP delivery failed."),503
    return jsonify(success=True,message="OTP sent to your email")
@app.post("/api/admin-login/verify-otp")
def verify_admin_login():
    data=request.get_json(silent=True) or {};email,otp=str(data.get("email","")).strip().lower(),str(data.get("otp","")).strip();record,error=verify_otp(email,"admin_login",otp,True)
    if error:return jsonify(success=False,message=error),400
    db=get_db()
    try:user=db.execute("SELECT * FROM users WHERE id=? AND role='admin'",(record["payload"],)).fetchone()
    finally:db.close()
    if not user:return jsonify(success=False,message="Admin account not found"),401
    establish_session(user);return jsonify(success=True,message="Admin login successful",admin={k:user[k] for k in ("id","name","email","role","user_code")})
@app.post("/api/admin-login/resend-otp")
def resend_admin_login():
    data=request.get_json(silent=True) or {};email=str(data.get("email","")).strip().lower();record=get_otp(email,"admin_login")
    if not record:return jsonify(success=False,message="Login OTP expired. Please log in again."),400
    db=get_db()
    try:user=db.execute("SELECT * FROM users WHERE id=?",(record["payload"],)).fetchone()
    finally:db.close()
    otp=generate_otp(); print_otp_to_terminal(email, otp, "Admin Login OTP Resend"); save_otp(email,"admin_login",otp,record["payload"])
    if not user or not send_otp_email(email,user["name"],"admin login",otp):return jsonify(success=False,message="Email delivery failed."),503
    return jsonify(success=True,message="New OTP sent to your email")

@app.post("/api/forgot-password")
def forgot_password():
    data=request.get_json(silent=True) or {};email=str(data.get("email","")).strip().lower();db=get_db()
    try:user=db.execute("SELECT * FROM users WHERE lower(email)=?",(email,)).fetchone()
    finally:db.close()
    if not user:return jsonify(success=False,message="No account exists for this email."),404
    otp=generate_otp(); print_otp_to_terminal(email, otp, "Password Reset"); save_otp(email,"password_reset",otp,str(user["id"]))
    if not send_otp_email(email,user["name"],"password_reset",otp):return jsonify(success=False,message="Email service is not configured or OTP delivery failed."),503
    return jsonify(success=True,message="OTP sent to your email")
@app.post("/api/forgot-password/resend-otp")
def resend_reset():
    data=request.get_json(silent=True) or {};email=str(data.get("email","")).strip().lower();record=get_otp(email,"password_reset")
    if not record:return jsonify(success=False,message="Reset session expired. Please request a new OTP."),400
    db=get_db()
    try:user=db.execute("SELECT * FROM users WHERE id=?",(record["payload"],)).fetchone()
    finally:db.close()
    otp=generate_otp(); print_otp_to_terminal(email, otp, "Password Reset OTP Resend"); save_otp(email,"password_reset",otp,record["payload"])
    if not user or not send_otp_email(email,user["name"],"password_reset",otp):return jsonify(success=False,message="Email delivery failed."),503
    return jsonify(success=True,message="New OTP sent to your email")
@app.post("/api/forgot-password/verify-otp")
@app.post("/api/verify-otp")
def verify_reset():
    data=request.get_json(silent=True) or {};email,otp=str(data.get("email","")).strip().lower(),str(data.get("otp","")).strip();_,error=verify_otp(email,"password_reset",otp)
    return (jsonify(success=False,message=error),400) if error else (jsonify(success=True,message="OTP verified successfully",email=email),200)
@app.post("/api/reset-password")
def reset_password():
    data=request.get_json(silent=True) or {};email,otp=str(data.get("email","")).strip().lower(),str(data.get("otp","")).strip();password=str(data.get("new_password",data.get("password","")));confirm=str(data.get("confirm_password",password))
    if password!=confirm or not valid_password(password):return jsonify(success=False,message="Passwords must match and contain at least 8 characters."),400
    record,error=verify_otp(email,"password_reset",otp,True)
    if error:return jsonify(success=False,message=error),400
    db=get_db()
    try:
        user=db.execute("SELECT * FROM users WHERE id=?",(record["payload"],)).fetchone()
        if not user:return jsonify(success=False,message="User account could not be found"),404
        db.execute("UPDATE users SET password_hash=? WHERE id=?",(generate_password_hash(password),user["id"]));db.commit()
    finally:db.close()
    send_password_reset_success_email(email,user["name"]);return jsonify(success=True,message="Password reset successfully")

@app.get("/api/session")
def current_session():
    if not session.get("user_id"):return jsonify(authenticated=False,message="Session expired"),401
    return jsonify(authenticated=True,user={"id":session["user_id"],"name":session.get("user_name"),"email":session.get("user_email"),"role":session.get("role")})
@app.get("/api/admin/session")
def admin_session():
    if session.get("role")!="admin" or not session.get("user_id"):return jsonify(authenticated=False,message="Session expired"),401
    return jsonify(authenticated=True,admin={"id":session["user_id"],"user_code":session.get("user_code"),"name":session.get("user_name"),"email":session.get("user_email"),"role":"admin"})
@app.post("/api/logout")
@app.post("/api/admin/logout")
def logout():session.clear();return jsonify(success=True,message="Logged out successfully")
@app.get("/api/users")
def users():
    db=get_db()
    try:rows=db.execute("SELECT id,user_code,name,email,role,sport,contact_number,gender,date_of_birth,created_at,email_verified FROM users ORDER BY id DESC").fetchall()
    finally:db.close()
    return jsonify([dict(row) for row in rows])

init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )