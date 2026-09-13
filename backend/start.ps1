$env:FITNESS_TEST_MODE="true"
$env:FLASK_DEBUG = if ($env:FLASK_DEBUG) { $env:FLASK_DEBUG } else { "false" }
python app.py