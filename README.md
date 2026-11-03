# VIT-AP Smart Hostel Management — Demo

A mobile-friendly college-project demo built with Flask, SQLite/SQLAlchemy, HTML and CSS.
It uses fictional sample records. It is not an official VIT-AP system.

## Run locally (Android-friendly cloud IDE or laptop)

1. Install Python 3.10+.
2. Extract this ZIP and open a terminal in the project folder.
3. Run:
   ```bash
   pip install -r requirements.txt
   flask --app app init-db
   flask --app app run --host=0.0.0.0
   ```
4. Open the address shown by Flask in your browser.

## Demo logins

- Admin: `admin@vitap.demo` / `Admin@123`
- Warden: `warden@vitap.demo` / `Warden@123`
- Student: `student@vitap.demo` / `Student@123`

Students can also register a new demo account.

## Deploy online

This project includes `render.yaml` and a `Procfile` for deployment on Render:
1. Create a GitHub repository and upload the extracted project files.
2. In Render, create a new Blueprint and connect that repository.
3. Deploy the service. Render will provide a public URL.
4. For persistent production data, attach a managed PostgreSQL database and set `DATABASE_URL` to its internal connection string. The included SQLite setting is suitable for a short demo only.

## Important demo limitations

- Use fictional data only. Do not enter real student records, passwords, phone numbers or other private information.
- Before public deployment, set a strong secret key and use a persistent database.
- This is an academic prototype, not an approved university service. Have an authorized administrator review security, privacy and workflow requirements before real use.
- Room allocation approvals and complaint updates are demo workflows.
