import sqlite3
import os
from werkzeug.security import generate_password_hash

# Use the SAME absolute path as app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'athlete_tracker.db')

def hash_password(password):
    return generate_password_hash(password)

def main():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        print("Database already contains users. Skipping seed.")
        conn.close()
        return

    # ============================================
    # USERS (DO NOT specify id — let AUTOINCREMENT handle it)
    # user_code format: ADM001, COA001, ATH001 (matches app.py new_code())
    # ============================================
    users_raw = [
        ('ADM001', 'Admin Kumar', 'admin@college.edu', hash_password('ChangeMe!123'), 'admin', None, '9876543210', None, None),
        ('COA001', 'Coach Verma', 'verma@college.edu', hash_password('ChangeMe!123'), 'coach', 'Athletics', '9876543211', 'Male', '1985-03-15'),
        ('COA002', 'Coach Sharma', 'sharma@college.edu', hash_password('ChangeMe!123'), 'coach', 'Basketball', '9876543212', 'Male', '1982-07-22'),
        ('ATH001', 'Arjun Roy', 'arjun@college.edu', hash_password('ChangeMe!123'), 'player', 'Athletics', '9876543213', 'Male', '2005-03-12'),
        ('ATH002', 'Sneha Gupta', 'sneha@college.edu', hash_password('ChangeMe!123'), 'player', 'Basketball', '9876543214', 'Female', '2004-07-21'),
        ('ATH003', 'Kabir Ali', 'kabir@college.edu', hash_password('ChangeMe!123'), 'player', 'Football', '9876543215', 'Male', '2003-11-18'),
        ('ATH004', 'Meera Das', 'meera@college.edu', hash_password('ChangeMe!123'), 'player', 'Athletics', '9876543216', 'Female', '2006-02-02'),
        ('ATH005', 'Rohan Singh', 'rohan@college.edu', hash_password('ChangeMe!123'), 'player', 'Basketball', '9876543217', 'Male', '2004-09-30'),
    ]

    for user in users_raw:
        cursor.execute(
            """INSERT INTO users (user_code, name, email, password_hash, role, sport, contact_number, gender, date_of_birth, email_verified, account_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'active')""",
            user
        )

    # Build email → id lookup for foreign keys
    cursor.execute("SELECT id, email, role FROM users")
    user_map = {row['email']: {'id': row['id'], 'role': row['role']} for row in cursor.fetchall()}

    def uid(email):
        return user_map[email]['id']

    # ============================================
    # COACH-ATHLETE ASSIGNMENTS
    # ============================================
    assignments = [
        (uid('verma@college.edu'), uid('arjun@college.edu')),
        (uid('verma@college.edu'), uid('meera@college.edu')),
        (uid('sharma@college.edu'), uid('sneha@college.edu')),
        (uid('sharma@college.edu'), uid('rohan@college.edu')),
        (uid('verma@college.edu'), uid('kabir@college.edu')),
    ]
    for coach_id, athlete_id in assignments:
        cursor.execute(
            "INSERT INTO coach_athletes (coach_id, athlete_id) VALUES (?, ?)",
            (coach_id, athlete_id)
        )

    # ============================================
    # PHYSICAL ASSESSMENTS
    # ============================================
    assessments = [
        (uid('arjun@college.edu'), uid('verma@college.edu'), '2026-08-05', 178, 64, 22.1, None, None, None, None, None, None,
         '7/10', '8/10', 'Good', 'None', None, 'None', '74', '72', '-2kg',
         'Improved conditioning', '2026-09-05'),
        (uid('sneha@college.edu'), uid('sharma@college.edu'), '2026-08-05', 170, 69, 22.5, None, None, None, None, None, None,
         '9/10', '9/10', 'Excellent', 'None', None, 'None', '65', '64', '-1kg',
         'Recovery progressing well', '2026-09-05'),
        (uid('kabir@college.edu'), uid('verma@college.edu'), '2026-08-06', 175, 58, 21.3, None, None, None, None, None, None,
         '8/10', '7/10', 'Fair', 'Knee soreness', 'Shoulder stiffness', 'Avoid jumping drills for 1 week',
         '70', '69', '-1kg', 'Mobility improved', '2026-09-06'),
        (uid('meera@college.edu'), uid('verma@college.edu'), '2026-08-06', 165, None, None, None, None, None, None, None, None,
         None, None, None, None, None, 'Reduce sprint volume', '59', '58', '-1kg',
         'Needs strengthening work', '2026-09-06'),
        (uid('rohan@college.edu'), uid('sharma@college.edu'), '2026-08-07', 182, None, None, None, None, None, None, None, None,
         None, None, None, None, None, 'Avoid overhead presses', '81', '80', '-1kg',
         'Flexibility needs improvement', '2026-09-07'),
    ]
    for a in assessments:
        cursor.execute(
            """INSERT INTO physical_assessments 
               (athlete_id, coach_id, assessment_date, height_cm, weight_kg, bmi, body_fat_pct,
                waist_circumference, hip_circumference, chest_circumference, thigh_circumference, arm_circumference,
                flexibility_score, mobility_score, posture_assessment, injury_status, injury_notes,
                medical_restrictions, previous_measurement, current_measurement, change_value,
                assessment_remarks, next_assessment_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            a
        )

    # ============================================
    # TRAINING SESSIONS (31 columns)
    # ============================================
    sessions = [
        (uid('arjun@college.edu'), uid('verma@college.edu'), '2026-08-01', 'Athletics', 90, 'High', 8,
         '100m Sprint, Long Jump, Push-ups', 'Sprint: 5x100m, Push-ups: 3x15',
         None, None, None, None, 25, None, None, None, None, None, None, None,
         None, None, None, 'Present', 100, None,
         'Good session. Sprint form improving.', 'Maintain arm drive during acceleration.',
         'Continue plyometric work.', 'Speed endurance'),
        (uid('sneha@college.edu'), uid('sharma@college.edu'), '2026-08-02', 'Basketball', 120, 'Medium', 6,
         'Dribbling drills, Shooting practice, Defense', 'Dribbling: 10 min, Shooting: 50 attempts',
         None, None, None, None, None, None, None, None, None, None, None, None,
         None, None, None, 'Present', 85, None,
         'Shooting accuracy needs work.', 'Focus on follow-through.',
         'Increase shooting reps next session.', 'Shooting mechanics'),
        (uid('kabir@college.edu'), uid('verma@college.edu'), '2026-08-03', 'Football', 105, 'High', 9,
         'Passing drills, Sprint intervals, Ball control', 'Passing: 100 reps, Sprints: 10x50m',
         None, None, None, None, None, None, None, None, None, None, None, None,
         None, None, None, 'Present', 95, None,
         'Excellent intensity. High RPE but maintained form.', 'Monitor fatigue levels.',
         'Light recovery session tomorrow.', 'Tactical positioning'),
    ]
    for s in sessions:
        cursor.execute(
            """INSERT INTO training_sessions
               (athlete_id, coach_id, session_date, sport_type, duration_minutes, intensity_level, rpe,
                exercises_performed, sets_reps_weights, squat_load, deadlift_load, bench_press_load,
                pushups_count, pullups_count, plank_time, running_distance, sprint_time, shuttle_run_time,
                agility_test_score, vertical_jump_height, broad_jump_distance, sleep_hours, fatigue_level,
                muscle_soreness_level, attendance, completion_pct, missed_session_reason, session_observation,
                technical_feedback, training_recommendation, next_session_focus)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            s
        )

    # ============================================
    # GOALS
    # ============================================
    goals = [
        (uid('arjun@college.edu'), uid('verma@college.edu'), '100m Sprint under 12 seconds', 'Fitness',
         'Reduce 100m sprint time from 14.2s to under 12s',
         '14.2s', '12.0s', '13.5s', 45, 'In Progress', '2026-08-01', '2026-12-01', '2026-09-01',
         'None', None, None, None, 'No', None, None, 7, 'High', 'High', 'Time management with classes',
         None, None, None),
        (uid('sneha@college.edu'), uid('sharma@college.edu'), 'Improve 3-point shooting to 70%', 'Skill',
         'Increase 3-point shooting accuracy to 70%',
         '45%', '70%', '52%', 28, 'In Progress', '2026-08-01', '2026-11-01', '2026-09-01',
         'None', None, None, None, 'No', None, None, 6, 'Medium', 'High', 'Inconsistent release point',
         None, None, None),
        (uid('kabir@college.edu'), uid('verma@college.edu'), 'Complete full 90-min match', 'Fitness',
         'Build endurance to play full 90-minute match',
         '60 min', '90 min', '75 min', 50, 'In Progress', '2026-08-01', '2026-10-01', '2026-09-01',
         'None', None, None, None, 'No', None, None, 8, 'High', 'High', 'None so far',
         None, None, None),
    ]
    for g in goals:
        cursor.execute(
            """INSERT INTO goals
               (athlete_id, coach_id, goal_title, goal_type, goal_description, baseline_value, target_value,
                current_value, progress_pct, goal_status, start_date, target_date, review_date,
                injury_status, injury_area, expected_recovery_date, current_limitation, training_restriction,
                rehabilitation_exercise, recovery_progress_pct, self_rating, confidence_level, effort_level,
                challenges_faced, goal_achieved_date, final_result, next_goal)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            g
        )

    # ============================================
    # COACH FEEDBACK
    # ============================================
    feedbacks = [
        (uid('arjun@college.edu'), uid('verma@college.edu'), '2026-08-05', 'Session 1 - Sprint Training',
         'Good starting blocks position, Strong arm drive',
         'Knee lift could be higher, Landing mechanics need work',
         7, 'Good baseline fitness, Needs more core strength',
         'Can maintain pace for 60m then drops', 'Lower body strength adequate',
         'Hamstring flexibility limiting stride length',
         'Good tactical awareness', 'Proper lane discipline', 'Understands race strategy',
         'Punctual and focused', 'Listens well to corrections', 'Steady improvement shown',
         'Maintains concentration during drills', 'Supports teammates during practice',
         7, 'Strong work ethic', 'Flexibility and sprint mechanics',
         'Arjun shows consistent improvement. Focus on flexibility work and knee drive.',
         'Daily hamstring stretches, Core plank holds 3x60s',
         'Practice block starts 3x/week', 'Speed endurance + flexibility',
         '2026-08-12'),
        (uid('sneha@college.edu'), uid('sharma@college.edu'), '2026-08-05', 'Session 2 - Shooting Practice',
         'Good footwork on catch-and-shoot, Quick release',
         'Inconsistent elbow position, Follow-through varies',
         6, 'Agile and quick, Good lateral movement',
         'Can run full court without fatigue', 'Upper body strength good for position',
         'Ankle mobility affecting defensive stance',
         'Reads screens well', 'Good help defense position', 'Anticipates passes',
         'Always early to practice', 'Asks questions proactively', 'Growing confidence',
         'Stays engaged during film sessions', 'Encourages younger players',
         7, 'Coachable attitude and quick learner', 'Shooting consistency under pressure',
         'Sneha has great potential. Shooting mechanics need refinement for game situations.',
         'Form shooting 100 reps daily before practice', 'Film study on shooting form',
         'Shooting drills + game simulation', '2026-08-12'),
    ]
    for f in feedbacks:
        cursor.execute(
            """INSERT INTO coach_feedback
               (athlete_id, coach_id, feedback_date, session_reference, technical_strengths,
                technical_corrections, skill_execution_rating, fitness_observation, endurance_observation,
                strength_observation, flexibility_mobility_observation, decision_making, positioning,
                game_awareness, discipline, communication, confidence, focus_concentration, teamwork,
                overall_rating, key_strength, key_improvement_area, performance_summary, immediate_action,
                home_practice_task, next_session_focus, follow_up_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            f
        )

    conn.commit()
    conn.close()

    print("=" * 60)
    print("✅ DATABASE SEEDED SUCCESSFULLY")
    print("=" * 60)
    print("\nLogin Credentials:")
    print("  admin@college.edu  / 1234  →  Admin")
    print("  verma@college.edu  / 1234  →  Coach (Athletics)")
    print("  sharma@college.edu / 1234  →  Coach (Basketball)")
    print("  arjun@college.edu  / 1234  →  Player (Arjun Roy - ATH001)")
    print("  sneha@college.edu  / 1234  →  Player (Sneha Gupta - ATH002)")
    print("  kabir@college.edu  / 1234  →  Player (Kabir Ali - ATH003)")
    print("  meera@college.edu  / 1234  →  Player (Meera Das - ATH004)")
    print("  rohan@college.edu  / 1234  →  Player (Rohan Singh - ATH005)")
    print("\nDatabase contains:")
    print("  • 1 Admin, 2 Coaches, 5 Players")
    print("  • 5 Physical Assessments")
    print("  • 3 Training Sessions")
    print("  • 3 Goals")
    print("  • 2 Coach Feedbacks")

if __name__ == "__main__":
    main()
