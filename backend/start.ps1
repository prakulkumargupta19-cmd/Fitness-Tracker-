# Save this as: backend/start.ps1
$env:SECRET_KEY="dev-secret-key-32-chars-long"
$env:FITNESS_TEST_MODE="false"
$env:FLASK_DEBUG="true"
python app.py