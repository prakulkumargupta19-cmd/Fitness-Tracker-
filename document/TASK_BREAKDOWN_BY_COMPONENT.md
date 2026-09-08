# 🎯 FITNESS TRACKER — TASK BREAKDOWN BY COMPONENT

**Last Updated:** September 1, 2026  
**Total Hours (Sprint 1):** 26-33 hours  
**Total Hours (Sprint 2):** 15-20 hours

---

## 📋 QUICK REFERENCE MATRIX

| Task ID | Component | Title | Hours | Priority | Status | Dependencies |
|---------|-----------|-------|-------|----------|--------|--------------|
| **F-1** | Frontend | Fix Login Form Submission | 2-3 | 🔴 CRITICAL | ❌ BLOCKED | None |
| **B-1** | Backend | Secure Seed Script | 1 | 🔴 CRITICAL | ⏳ PENDING | None |
| **F-3** | Frontend | Coach Dashboard Integration | 8-10 | 🟡 HIGH | ⏳ PENDING | F-1 |
| **F-4** | Frontend | Admin Dashboard Integration | 6-8 | 🟡 HIGH | ⏳ PENDING | F-1 |
| **B-2** | Backend | Input Validation | 5-6 | 🟡 HIGH | ⏳ PENDING | None |
| **F-2** | Frontend | Replace Alert() Patterns | 2-3 | 🟡 HIGH | ⏳ PENDING | None |
| **F-5** | Frontend | Fix Admin OTP Verification | 1-2 | 🟡 HIGH | ⏳ PENDING | None |
| | | **SPRINT 1 TOTAL** | **26-33** | | | |
| **B-3** | Backend | Pagination Implementation | 3-4 | 🔵 MEDIUM | 📋 BACKLOG | None |
| **B-4** | Backend | CSRF Protection | 3 | 🔵 MEDIUM | 📋 BACKLOG | None |
| **B-5** | Backend | Rate Limiting | 2-3 | 🔵 MEDIUM | 📋 BACKLOG | None |
| **B-6** | Backend | Audit Logging System | 4-5 | 🔵 MEDIUM | 📋 BACKLOG | None |
| **B-7** | Backend | User Management API | 5-6 | 🔵 MEDIUM | 📋 BACKLOG | None |
| **F-6** | Frontend | Responsive Tables | 3-4 | 🔵 MEDIUM | 📋 BACKLOG | None |
| **F-7** | Frontend | Loading Skeletons | 2-3 | 🔵 MEDIUM | 📋 BACKLOG | None |
| | | **SPRINT 2 TOTAL** | **15-20** | | | |

---

## 🔧 BACKEND TASKS

### ⚡ SPRINT 1 (CRITICAL & HIGH)

#### **B-1: Secure Seed Script** [1 hour]
**Status:** PENDING  
**Severity:** 🔴 CRITICAL - Security Vulnerability  
**File:** `backend/seed.py`

**What's Wrong:**
```python
# Currently: All test accounts use password "1234" and are hardcoded
('ATH001', 'Arjun Roy', 'arjun@college.edu', hash_password('1234'), 'player')
```

**What to Do:**
1. [ ] Rename `seed.py` → `seed-dev.py` (development only)
2. [ ] Generate random strong passwords for each test account
3. [ ] Create `.env.test` file with test credentials (add to `.gitignore`)
4. [ ] Update `.env.example` to show template format
5. [ ] Update `README.md` with setup instructions
6. [ ] Add note: "Never run seed in production"

**Output Deliverables:**
- `backend/seed-dev.py` — Development seed with random passwords
- `.env.test.example` — Template (no actual values)
- `README.md` — Updated with test setup

**Testing:**
```bash
# After fix:
python backend/seed-dev.py  # Should succeed
# Check .env.test for credentials
# Login with new test accounts
```

---

#### **B-2: Input Validation** [5-6 hours]
**Status:** PENDING  
**Severity:** 🟡 HIGH - Data Quality Risk  
**Files:** `backend/app.py` (coach write endpoints)

**What's Wrong:**
```python
# Currently: No validation
height_cm = request.json.get('height_cm')  # Could be -999 or "hello"
weight_kg = request.json.get('weight_kg')  # No type checking
intensity_level = request.json.get('intensity_level')  # Could be "EXTREME"
```

**What to Do:**
1. [ ] Create validation function `validate_assessment_data(data)`
2. [ ] Create validation function `validate_training_session_data(data)`
3. [ ] Create validation function `validate_goal_data(data)`
4. [ ] Create validation function `validate_feedback_data(data)`
5. [ ] Apply validation to all coach write endpoints
6. [ ] Return 400 error with clear message if validation fails

**Validation Rules:**
```python
# Assessment validation
- height_cm: 50-300 (float)
- weight_kg: 20-300 (float)
- bmi: 10-60 (float)
- body_fat_pct: 0-60 (float)
- flexibility_score, mobility_score: string, max 50 chars
- injury_status: required field
- assessment_remarks: string, max 500 chars

# Training session validation
- duration_minutes: 1-600 (integer)
- intensity_level: ENUM('Low', 'Medium', 'High')
- rpe: 1-10 (integer)
- completion_pct: 0-100 (integer)

# Goals validation
- progress_pct: 0-100 (integer)
- goal_status: ENUM('Not Started', 'In Progress', 'Achieved', 'Delayed')
- self_rating: 1-10 (integer)

# Feedback validation
- skill_execution_rating: 1-10 (integer)
- overall_rating: 1-10 (integer)
- technical_strengths: max 500 chars
- technical_corrections: max 500 chars
```

**Code Template:**
```python
def validate_assessment_data(data):
    """Validate assessment data before saving to DB"""
    errors = []
    
    # Height validation
    if 'height_cm' in data and data['height_cm'] is not None:
        try:
            h = float(data['height_cm'])
            if h < 50 or h > 300:
                errors.append("Height must be between 50 and 300 cm")
        except (ValueError, TypeError):
            errors.append("Height must be a valid number")
    
    # Weight validation
    if 'weight_kg' in data and data['weight_kg'] is not None:
        try:
            w = float(data['weight_kg'])
            if w < 20 or w > 300:
                errors.append("Weight must be between 20 and 300 kg")
        except (ValueError, TypeError):
            errors.append("Weight must be a valid number")
    
    # Return list of errors (empty if all valid)
    return errors

# Usage in endpoint:
@app.post("/api/assessments")
@login_required
@role_required('coach')
def create_assessment():
    data = request.json
    errors = validate_assessment_data(data)
    
    if errors:
        return jsonify({
            "success": False,
            "message": errors[0]  # Return first error
        }), 400
    
    # ... proceed with creation ...
```

**Testing:**
```python
# Test cases
assert validate_assessment_data({'height_cm': -50}) == ["Height must be..."]
assert validate_assessment_data({'height_cm': 999}) == ["Height must be..."]
assert validate_assessment_data({'height_cm': 180}) == []
assert validate_assessment_data({'height_cm': "abc"}) == ["Height must be..."]
```

---

### 📋 SPRINT 2 (MEDIUM PRIORITY)

#### **B-3: Pagination** [3-4 hours]
**Status:** BACKLOG  
**Severity:** 🔵 MEDIUM - Performance  
**Files:** `backend/app.py` (data read endpoints)

**Endpoints to Update:**
- `GET /api/assessments`
- `GET /api/training-sessions`
- `GET /api/goals`
- `GET /api/feedback`

**Implementation:**
```python
@app.get("/api/assessments")
@login_required
def get_assessments():
    # Parse pagination params
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid pagination params"}), 400
    
    if offset < 0:
        return jsonify({"success": False, "message": "offset must be >= 0"}), 400
    
    # ... existing query logic ...
    
    # Add LIMIT and OFFSET
    cursor.execute(f"""SELECT * FROM physical_assessments 
                      WHERE {filter_clause} 
                      LIMIT {limit} OFFSET {offset}""")
    records = cursor.fetchall()
    
    # Get total count
    cursor.execute(f"SELECT COUNT(*) as total FROM physical_assessments WHERE {filter_clause}")
    total = cursor.fetchone()['total']
    
    return jsonify({
        "success": True,
        "data": records,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_next": (offset + limit) < total,
            "has_prev": offset > 0
        }
    })
```

---

#### **B-4: CSRF Protection** [3 hours]
**Status:** BACKLOG  
**Severity:** 🔵 MEDIUM - Security  
**Files:** `backend/app.py`

**Installation:**
```bash
pip install Flask-WTF
```

**Implementation:**
```python
from flask_wtf.csrf import CSRFProtect, generate_csrf

csrf = CSRFProtect(app)

# Add CSRF token endpoint
@app.get("/api/csrf-token")
def get_csrf_token():
    return jsonify({"token": generate_csrf()})

# Update session cookie
app.config.update(
    SESSION_COOKIE_SAMESITE="Strict",  # Change from Lax to Strict
)

# Apply to all POST/PUT/DELETE endpoints
@app.post("/api/assessments")
@csrf.protect  # Add this
@login_required
def create_assessment():
    ...
```

---

#### **B-5: Rate Limiting** [2-3 hours]
**Status:** BACKLOG  
**Severity:** 🔵 MEDIUM - Security  
**Files:** `backend/app.py`

**Installation:**
```bash
pip install Flask-Limiter
```

**Implementation:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.post("/api/login")
@limiter.limit("5 per minute")
def login():
    ...

@app.post("/api/forgot-password")
@limiter.limit("3 per hour")
def forgot_password():
    ...

@app.post("/api/admin-login/resend-otp")
@limiter.limit("5 per minute")
def admin_resend_otp():
    ...
```

---

#### **B-6: Audit Logging** [4-5 hours]
**Status:** BACKLOG  
**Severity:** 🔵 MEDIUM - Compliance  
**Files:** `backend/schema.sql`, `backend/app.py`

**Database Table:**
```sql
CREATE TABLE audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,  -- 'CREATE', 'UPDATE', 'DELETE', 'VIEW'
    resource_type VARCHAR(50) NOT NULL,  -- 'assessment', 'training', 'goal', 'feedback'
    resource_id INT NOT NULL,
    details TEXT,  -- JSON with field values
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, created_at)
);
```

**Implementation:**
```python
def log_audit(action, resource_type, resource_id, details=None):
    """Log audit trail"""
    user_id = session.get('user_id')
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (user_id, action, resource_type, resource_id, json.dumps(details), ip, user_agent)
    )
    db.commit()

# Usage
@app.post("/api/assessments")
def create_assessment():
    # ... create assessment ...
    log_audit('CREATE', 'assessment', assessment_id, {
        'athlete_id': athlete_id,
        'height_cm': height_cm,
        'weight_kg': weight_kg
    })
```

---

#### **B-7: User Management API** [5-6 hours]
**Status:** BACKLOG  
**Severity:** 🔵 MEDIUM - Feature Completion  
**Files:** `backend/app.py`

**New Endpoints:**
```python
# Get single user
@app.get("/api/users/<int:user_id>")
@login_required
@role_required('admin')
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    return jsonify({"success": True, "data": user})

# Create user
@app.post("/api/users")
@login_required
@role_required('admin')
def create_user():
    data = request.json
    # Validate input
    # Create user record
    # Return created user

# Update user
@app.put("/api/users/<int:user_id>")
@login_required
@role_required('admin')
def update_user(user_id):
    data = request.json
    # Update user role, status, etc.

# Delete user (soft delete)
@app.delete("/api/users/<int:user_id>")
@login_required
@role_required('admin')
def delete_user(user_id):
    # Mark as inactive
```

---

## 🎨 FRONTEND TASKS

### ⚡ SPRINT 1 (CRITICAL & HIGH)

#### **F-1: Fix Login Form Submission** [2-3 hours]
**Status:** ❌ BLOCKED  
**Severity:** 🔴 CRITICAL - Cannot Login  
**Files:** `frontend/student/student-login.html`, `frontend/coach/coach-login.html`, `frontend/admin/admin-login.html`

**Symptoms:**
- User enters credentials
- Clicks "Log In"
- Nothing happens
- No error message
- Page doesn't redirect

**Root Cause Analysis:**
```
Need to verify:
1. [ ] `<base target="_blank">` in HTML - might interfere with form submission
2. [ ] api-client.js loading - is API object defined?
3. [ ] JavaScript errors - check browser console
4. [ ] Network request - is POST going to /api/login?
5. [ ] CORS - is response blocked?
6. [ ] Backend - is server running?
```

**Debug Steps:**
```javascript
// Open Console (F12 → Console tab)
1. Type: API
   Expected: See API object with methods
   If undefined: api-client.js not loaded
   
2. Type: API.login({email: "test@test.com", password: "test"})
   Expected: Promise object
   If error: Check what error
   
3. Go to Network tab
4. Try login again
5. Look for POST to /api/login
6. Check response status and body
```

**Possible Fixes:**
```html
<!-- Option 1: Remove <base target="_blank"> if not needed -->
<!-- REMOVE THIS LINE if it's interfering -->
<base target="_blank">

<!-- Option 2: Set form target explicitly -->
<form id="loginForm" target="_self">
</form>

<!-- Option 3: Use explicit submit handler -->
<button onclick="submitLoginForm()" type="button">Log In</button>
<script>
function submitLoginForm() {
    // Explicit form submission
    const form = document.getElementById("loginForm");
    form.dispatchEvent(new Event('submit'));
}
</script>
```

**Verification Checklist:**
- [ ] Form submits when button clicked
- [ ] POST request appears in Network tab
- [ ] POST goes to `http://localhost:5000/api/login`
- [ ] Response is 200 with `{"success": true}`
- [ ] Session cookie set (check Application → Cookies)
- [ ] Redirects to dashboard after 800ms
- [ ] Works in Chrome, Firefox, Safari

---

#### **F-2: Replace Browser Alerts with Styled Messages** [2-3 hours]
**Status:** PENDING  
**Severity:** 🟡 HIGH - UX Consistency  
**Files:**
- `frontend/admin/admin-loginotp.html` (Line 822)
- `frontend/admin/forgot-password.html` (Line 213)
- `frontend/admin/reset-password.html` (Line 250)
- Any other `alert()` calls

**What's Wrong:**
```javascript
// ❌ BAD - Uses browser alert
alert("Verification code sent successfully!");

// ✅ GOOD - Uses styled message
API.showMessage("message", "Verification code sent successfully!", "success");
```

**What to Do:**
1. [ ] Find all `alert()` calls in frontend
2. [ ] Find all `showError()` custom functions
3. [ ] Replace with `API.showMessage()` pattern
4. [ ] Test each page manually

**Search Command:**
```bash
# Find all alert() calls
grep -r "alert(" frontend/
```

**Replacement Pattern:**
```javascript
// BEFORE
alert("Message here");

// AFTER
API.showMessage("message", "Message here", "info");  // or "success", "error"
```

**Ensure API method exists in api-client.js:**
```javascript
showMessage: function (elementId, message, type) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    el.textContent = message;
    el.className = `message ${type}`;
    el.style.display = "block";
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        el.style.display = "none";
    }, 5000);
}
```

**Files Affected:**
- admin-loginotp.html
- admin-signup-verify.html
- admin-forgot-password.html
- admin-reset-password.html
- forgot-password.html
- reset-password.html

---

#### **F-3: Integrate Coach Dashboard with Backend API** [8-10 hours]
**Status:** PENDING  
**Severity:** 🟡 HIGH - Feature Incomplete  
**File:** `frontend/coach/coach-dashboard.html`

**Currently:**
- UI looks polished
- All data is hardcoded or from localStorage
- Cannot create/edit real records

**After Fix:**
- Loads real athlete list from backend
- Creates real assessments in database
- Records real training sessions
- Stores goals and feedback in database
- Shows real athlete data

**Implementation Phases:**

**Phase 1: Load Athlete List [1 hour]**
```javascript
async function loadAthletes() {
    try {
        const res = await API.getCoachAthletes();
        if (res.ok && res.data.success) {
            athletes = res.data.data;
            renderAthleteList();
        } else {
            showError("Failed to load athletes: " + res.data.message);
        }
    } catch (err) {
        showError("Network error: " + err.message);
    }
}

// Add to api-client.js
getCoachAthletes: function () {
    return apiRequest("GET", "/api/coach/athletes");
}

// On page load
document.addEventListener("DOMContentLoaded", loadAthletes);
```

**Phase 2: Display Assessments [2 hours]**
```javascript
async function loadAssessments(athleteId) {
    const res = await API.getAssessments(athleteId);
    if (res.ok && res.data.success) {
        renderAssessmentTable(res.data.data);
    }
}

// Add to api-client.js
getAssessments: function (athleteId, options={}) {
    const params = new URLSearchParams({
        athlete_id: athleteId,
        limit: options.limit || 50,
        offset: options.offset || 0
    });
    return apiRequest("GET", "/api/assessments?" + params);
}
```

**Phase 3: Create Assessment Modal [2 hours]**
```html
<div id="assessmentModal" style="display: none;">
    <form id="assessmentForm">
        <input type="date" id="assessmentDate" required>
        <input type="number" id="height" placeholder="Height (cm)" required>
        <input type="number" id="weight" placeholder="Weight (kg)" required>
        <input type="number" id="bmi" placeholder="BMI" required>
        <!-- ... more fields ... -->
        <button type="submit">Save Assessment</button>
        <button type="button" onclick="closeAssessmentModal()">Cancel</button>
    </form>
</div>

<script>
function showAssessmentModal() {
    document.getElementById("assessmentModal").style.display = "block";
}

function closeAssessmentModal() {
    document.getElementById("assessmentModal").style.display = "none";
}

document.getElementById("assessmentForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const data = {
        athlete_id: selectedAthleteId,
        assessment_date: document.getElementById("assessmentDate").value,
        height_cm: parseFloat(document.getElementById("height").value),
        weight_kg: parseFloat(document.getElementById("weight").value),
        bmi: parseFloat(document.getElementById("bmi").value),
    };
    
    const res = await API.createAssessment(data);
    if (res.ok && res.data.success) {
        API.showMessage("message", "Assessment saved!", "success");
        closeAssessmentModal();
        loadAssessments(selectedAthleteId);
    } else {
        API.showMessage("message", res.data.message, "error");
    }
});
</script>
```

**Phase 4: Training Sessions [2 hours]**
```javascript
async function loadTrainingSessions(athleteId) {
    const res = await API.getTrainingSessions(athleteId);
    if (res.ok) {
        renderSessionTable(res.data.data);
    }
}

// Form submission
document.getElementById("trainingForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
        athlete_id: selectedAthleteId,
        session_date: document.getElementById("sessionDate").value,
        duration_minutes: parseInt(document.getElementById("duration").value),
        intensity_level: document.getElementById("intensity").value,
        // ... other fields ...
    };
    const res = await API.createTrainingSession(data);
    if (res.ok) {
        API.showMessage("message", "Session recorded!", "success");
        loadTrainingSessions(selectedAthleteId);
    }
});
```

**Phase 5: Goals & Feedback [2 hours]**
```javascript
// Similar pattern for goals and feedback
```

**API Methods to Add to api-client.js:**
```javascript
getCoachAthletes: function () { ... },
getAssessments: function (athleteId, options) { ... },
getTrainingSessions: function (athleteId, options) { ... },
getGoals: function (athleteId, options) { ... },
getFeedback: function (athleteId, options) { ... },
createAssessment: function (data) { ... },
createTrainingSession: function (data) { ... },
createGoal: function (data) { ... },
createFeedback: function (data) { ... },
updateAssessment: function (id, data) { ... },
```

**Testing:**
- [ ] Load page as logged-in coach
- [ ] Athlete list appears
- [ ] Click athlete to load their data
- [ ] Create new assessment → appears in table
- [ ] Record training session → appears in table
- [ ] Add goal → appears in table
- [ ] Add feedback → appears in table
- [ ] Refresh page → data persists

---

#### **F-4: Integrate Admin Dashboard with Backend API** [6-8 hours]
**Status:** PENDING  
**Severity:** 🟡 HIGH - Feature Incomplete  
**File:** `frontend/admin/admin-dashboard.html`

**Phase 1: Load User List [2 hours]**
```javascript
async function loadUsers() {
    try {
        const res = await API.getUsers({ limit: 100, offset: 0 });
        if (res.ok && res.data.success) {
            renderUserTable(res.data.data);
            updateStatistics(res.data.pagination.total);
        }
    } catch (err) {
        showError("Failed to load users");
    }
}

// Add to api-client.js
getUsers: function (options={}) {
    const params = new URLSearchParams({
        limit: options.limit || 100,
        offset: options.offset || 0,
        role: options.role || ''
    });
    return apiRequest("GET", "/api/users?" + params);
}
```

**Phase 2: User Statistics [1 hour]**
```javascript
function updateStatistics(totalUsers) {
    // Count by role from loaded data
    const students = users.filter(u => u.role === 'player').length;
    const coaches = users.filter(u => u.role === 'coach').length;
    const admins = users.filter(u => u.role === 'admin').length;
    
    document.getElementById("totalUsers").textContent = totalUsers;
    document.getElementById("studentCount").textContent = students;
    document.getElementById("coachCount").textContent = coaches;
    document.getElementById("adminCount").textContent = admins;
}
```

**Phase 3: User Search/Filter [2 hours]**
```javascript
function filterUsers(searchTerm, roleFilter) {
    const filtered = users.filter(u => {
        const matchesSearch = u.email.includes(searchTerm) || u.name.includes(searchTerm);
        const matchesRole = roleFilter === '' || u.role === roleFilter;
        return matchesSearch && matchesRole;
    });
    renderUserTable(filtered);
}

// Add event listeners
document.getElementById("searchInput").addEventListener("input", (e) => {
    filterUsers(e.target.value, selectedRole);
});

document.getElementById("roleFilter").addEventListener("change", (e) => {
    filterUsers(searchTerm, e.target.value);
});
```

**Phase 4: User Management (After B-7) [2 hours]**
```javascript
// Create user modal
document.getElementById("createUserForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        role: document.getElementById("role").value,
    };
    const res = await API.createUser(data);
    if (res.ok) {
        API.showMessage("message", "User created!", "success");
        loadUsers();
    }
});
```

---

#### **F-5: Fix Admin OTP Verification** [1-2 hours]
**Status:** PENDING  
**Severity:** 🟡 HIGH - Blocks Admin Registration  
**File:** `frontend/admin/admin-signup-verify.html`

**What's Wrong:**
```javascript
// ❌ HARDCODED - Blocks real admin registration
if (otp !== "123456") {
    return showError("Invalid OTP. Please enter 123456 for this demo.");
}
// Always accepts "123456"
```

**What to Do:**
```javascript
// ✅ USE REAL API
async function verifyOtp() {
    const email = localStorage.getItem("signup_email");
    const otp = document.getElementById("otpInput").value.trim();
    
    if (!otp || otp.length !== 6) {
        showError("Please enter 6-digit OTP");
        return;
    }
    
    try {
        const res = await API.verifySignupOtp({ email, otp });
        
        if (res.ok && res.data.success) {
            // OTP verified
            API.showMessage("message", "Email verified! Setting up password...", "success");
            localStorage.setItem("email_verified", "true");
            setTimeout(() => {
                showPasswordSetupForm();
            }, 1000);
        } else {
            const msg = res.data.message || "Invalid OTP";
            showError(msg);
            document.getElementById("otpInput").focus();
        }
    } catch (err) {
        showError("Network error: " + err.message);
    }
}

// Wire up event listener
document.getElementById("verifyButton").addEventListener("click", verifyOtp);
```

**Testing:**
1. Navigate to admin signup
2. Fill form and submit
3. Should receive OTP via email (or see in console if TEST_MODE=true)
4. Enter OTP
5. Should verify successfully
6. Should show password setup form

---

### 📋 SPRINT 2 (MEDIUM PRIORITY)

#### **F-6: Responsive Table Improvements** [3-4 hours]
**Status:** BACKLOG  
**Severity:** 🔵 MEDIUM - Mobile Experience  
**Files:** `frontend/coach/coach-dashboard.html`, `frontend/admin/admin-dashboard.html`

**Improvements:**
1. Horizontal scroll on small screens
2. Collapsible rows on mobile
3. Touch-friendly sorting

**Implementation:**
```css
/* Responsive wrapper */
@media (max-width: 768px) {
    .table-wrapper {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    table {
        min-width: 600px;
    }
}

/* Stack on very small screens */
@media (max-width: 480px) {
    table, thead, tbody, tr, td {
        display: block;
        width: 100%;
    }
    
    tr {
        margin-bottom: 15px;
        border: 1px solid #ddd;
        padding: 10px;
    }
    
    td {
        text-align: right;
        padding-left: 50%;
        position: relative;
    }
    
    td:before {
        content: attr(data-label);
        position: absolute;
        left: 10px;
        font-weight: bold;
        text-align: left;
    }
}
```

---

#### **F-7: Loading Skeletons** [2-3 hours]
**Status:** BACKLOG  
**Severity:** 🔵 MEDIUM - Perceived Performance  
**Files:** `frontend/coach/coach-dashboard.html`, `frontend/admin/admin-dashboard.html`

**Implementation:**
```html
<div id="loadingState" class="skeleton-loader">
    <div class="skeleton-row">
        <div class="skeleton-cell" style="width: 30%;"></div>
        <div class="skeleton-cell" style="width: 50%;"></div>
        <div class="skeleton-cell" style="width: 20%;"></div>
    </div>
</div>

<div id="dataState" style="display: none;">
    <!-- Real data here -->
</div>
```

**CSS:**
```css
.skeleton-loader {
    animation: shimmer 2s infinite;
}

.skeleton-row {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
    padding: 15px;
    background: #f5f5f5;
    border-radius: 8px;
}

.skeleton-cell {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

**JavaScript:**
```javascript
function showLoading() {
    document.getElementById("loadingState").style.display = "block";
    document.getElementById("dataState").style.display = "none";
}

function hideLoading() {
    document.getElementById("loadingState").style.display = "none";
    document.getElementById("dataState").style.display = "block";
}

// Usage
async function loadData() {
    showLoading();
    const res = await API.getAthletes();
    hideLoading();
    renderData(res.data.data);
}
```

---

## 📊 RESOURCE ALLOCATION EXAMPLE

**Team:** 2 developers (1 backend, 1 frontend)

### Week 1
- **Backend Dev:** B-1 (1h), B-2 part 1 (2h)
- **Frontend Dev:** F-1 (3h), F-2 (3h)

### Week 2
- **Backend Dev:** B-2 complete (3h), B-2 testing (1h)
- **Frontend Dev:** F-3 Phase 1-2 (3h)

### Week 3
- **Backend Dev:** Ready for integration
- **Frontend Dev:** F-3 Phase 3-5 (7h)

### Week 4
- **Backend Dev:** Support/fixes
- **Frontend Dev:** F-4 (6h), F-5 (2h)

---

## ✅ ACCEPTANCE CRITERIA

### F-1 Done When
- User can log in successfully
- Session cookie created
- Redirects to dashboard
- Works in multiple browsers

### F-3 Done When
- Coach can see assigned athletes
- Can create assessments → persisted in DB
- Can record training sessions → persisted in DB
- All data loads from backend, not hardcoded

### B-2 Done When
- All validation functions written and tested
- All endpoints return 400 for invalid data
- Clear error messages for each validation failure

---

**Generated:** September 1, 2026  
**Version:** 1.0  
**Next Review:** After F-1 completion
