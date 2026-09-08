# Save this as: backend/start.ps1
$env:SECRET_KEY="dev-secret-key-32-chars-long"
$env:FITNESS_TEST_MODE="true"
$env:FLASK_DEBUG="true"
python app.py

# cd backend
#.\start.ps1 --> to run the file