# Mergington High School Activities API

A FastAPI application for viewing extracurricular activities. Teachers can sign in
to register and unregister students; visitors can view activities and participants.

## Features

- View activities, descriptions, schedules, participant lists, and remaining spots.
- Teacher-only student registration and unregistration.
- Teacher credentials stored locally as salted password hashes in `src/teachers.json`.
- Signed, HTTP-only teacher session cookies.

Activity and signup data is held in memory and resets when the server restarts.

## Getting Started

Run these commands from the repository root:

1. Install the dependencies:

   ```sh
   pip install -r requirements.txt
   ```

2. Create a teacher account. The script prompts for a username and password and
   writes the salted password hash to the ignored local file `src/teachers.json`:

   ```sh
   python -m src.manage_teachers
   ```

   Run the command again for each additional teacher. The JSON structure is
   illustrated in `src/teachers.example.json`. Do not commit `src/teachers.json`.

3. Configure a persistent secret for signing session cookies. For local
   development, generate one with:

   ```sh
   export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   ```

   If `SESSION_SECRET` is omitted, the app generates an in-memory secret and
   existing sessions will become invalid when the server restarts.

4. Start the application:

   ```sh
   uvicorn src.app:app --reload
   ```

5. Open:
   - Web application: http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - Alternative API documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/activities` | Get activities and participant details |
| GET | `/auth/session` | Check whether a teacher is signed in |
| POST | `/auth/login` | Sign in with a configured teacher username and password |
| POST | `/auth/logout` | Sign out and clear the session cookie |
| POST | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher sign-in required) |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher sign-in required) |
