# fitness-tracker
a tracker for the athletes to track their progress and even for coach to track their student's progress 
ADMIN 2 PAGES WITHOUT CREATE ACCOUNT

## Project separation

`backend/` is now an API-only Flask service. It does not serve any file from
`frontend1/`; frontend development and deployment can therefore happen
independently. Run the backend from `backend/` with `python setup_and_run.py`.

The API returns CORS headers, so a separately hosted frontend can call its
`/api/...` endpoints. Configure the frontend's API base URL to the backend
address (for example, `http://127.0.0.1:5000`) when it is served from a
different origin.