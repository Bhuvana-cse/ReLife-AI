# ReLife AI — Intelligent Repair, Reuse & Recovery Engine

ReLife AI is a full-stack college-project prototype for exploring the next useful life of a product. It combines a React/Vite client with a Python FastAPI service and SQLite persistence.

## What is included

- Account registration with email and optional student ID, sign-in using either identifier, password hashing with PBKDF2-HMAC-SHA256, bearer-token protected endpoints, profile, and sign-out.
- Product assessment from user-entered category, age, condition, approximate optional location, visible damage, repair estimate, resale estimate, and an optional image upload with a preview.
- A transparent, input-sensitive decision comparison across repair, resale, donation, reuse, component salvage, and recycling. Reassessing a selected product updates the same product record and appends to its analysis history.
- Product-specific history and persistent afterlife passport IDs. The QR opens the browser app and resolves the passport only after the owner signs in; passport pages include analysis history, component states, recovery-plan progress, user-submitted timeline updates, and the demo transfer workflow.
- Sample recipient matching with category, condition, and optional approximate-location score explanations plus persisted pending/accepted/completed states.
- Persistent Working / Damaged / Untested component checklists for laptops, mobile phones, chairs, appliances, and general product categories. Illustrative salvage value ranges are shown only for user-marked working components when a demo range is available.
- An interactive future-life simulator that recalculates scenario cards and chart estimates while assumptions change, reports estimated cost per added year, and stores the latest comparison per product for refresh persistence.
- Condition-aware ranked recovery plans with safety-oriented route restrictions, sample provider suggestions, persistent Pending / Completed / Unavailable status, and a Find Alternative action.
- Recovery-center directory with live OpenStreetMap searches, mapped provider contacts, opening-hour status when valid hours are listed, and a separate clearly labeled sample directory. Also includes a CSV export of saved impact activity.

## Important prototype boundaries

- **No computer-vision model is configured.** Product recommendations use transparent, rule-based demo logic. JPG/PNG/WebP uploads (up to 5 MB) are previewed locally and sent for type/size validation; image bytes and original filenames are not retained or analyzed. A photo cannot establish internal faults.
- **Decision rules and estimates are not professional advice.** For poor/fair items, the demo compares the repair estimate to `max(80% of resale estimate, 50)` in the entered currency; for good/excellent items it checks whether stated resale exceeds repair cost. Broken items prioritize component inspection and suitable recycling. User inputs, category, inspection results, safety, and local rules can change the appropriate outcome.
- **Salvage values are illustrative only.** Example value ranges apply to selected user-marked-working components; they are not current market data or a statement that a hidden component functions. Untested components have no estimate.
- **QR passports remain private.** QR links resolve through the frontend and require the owning account to sign in. The lookup is user-scoped and does not expose a public passport. The signed-in owner must be able to access the frontend URL encoded into the QR.
- Recipient requests and the separate sample recovery directory are **demo data**. The live directory searches OpenStreetMap/Nominatim and Overpass for mapped providers and displays only contact information present in map tags. Published opening hours are parsed for an "open now" estimate; map records and hours can be stale or incomplete. OpenStreetMap does not provide appointment slots or real-time service capacity, so users must contact the provider to confirm. Accepted products are not verified.
- Passport ownership and submitted events are **not independently verified**. A transfer is a demo event only and does not change or establish ownership.
- Scenario outputs are illustrative, user-input-dependent proxies. The app does not claim precise carbon, environmental, or measured waste savings. Money saved is not fabricated.
- This is a local demonstration, not a production identity or recovery service. The included development secret must be replaced for deployment; use HTTPS, a managed secret store, token revocation, rate limiting, backups, and appropriate privacy controls before production use.
- Live provider search sends the manually entered city/district/postal code to public OpenStreetMap search services. Requests are cached and Nominatim lookups are rate-limited; follow the Nominatim and Overpass usage policies before deploying or scaling the application.

## Requirements

- Windows 10/11 with Python 3.10+ and Node.js 18+ (Node 20 LTS recommended).
- Two PowerShell terminals opened at the workspace root.

## Install

### Terminal 1 — backend

```powershell
cd C:\Users\Bhuvana\Desktop\ReLife-AI\backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a private, random `RELIFE_SECRET_KEY` in `backend\.env` before running beyond a local demo. For the default local development run, the app uses a clearly development-only fallback. The SQLite database is created automatically at `backend\relife.db`.

Run the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API docs: <http://localhost:8000/docs>  
Health check: <http://localhost:8000/api/health>

### Terminal 2 — frontend

```powershell
cd C:\Users\Bhuvana\Desktop\ReLife-AI\frontend
npm.cmd install
npm.cmd run dev
```

Open <http://localhost:5173>. The default client API URL is `http://localhost:8000/api`. To change it, create `frontend\.env.local` with `VITE_API_URL=http://localhost:8000/api` and restart Vite.

## Tests and production build

Backend tests (from `backend`):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend production build (from `frontend`):

```powershell
npm.cmd run build
```

## College presentation walkthrough: all ten feature areas

1. **Login and registration:** Create a student account, sign out, sign back in, show password visibility, and explain that the database stores a salted PBKDF2 hash rather than a password. Forgot-password messaging explains that reset delivery is not configured.
2. **Dashboard:** Show product count, the saved recommendation pathway chart, recent products, and shortcuts. Start empty, then return after making an assessment.
3. **Analysis and decision engine:** Enter an example damaged laptop: electronics, Laptop, age 4 years, fair condition, repair estimate 25, resale estimate 100, useful-life estimate 2 years. Submit once. Review the recommended repair route, the displayed cost-threshold calculation, and the suitability notes for all six alternatives. Change the repair estimate above 80 and analyze again; show that the recommendation changes while the product ID stays the same and a new assessment is appended. Optional photos are not analyzed and cannot reveal internal faults.
4. **Product passport and QR:** Open the laptop passport and point out its stable product ID and the analysis history. Scan the QR (or open its URL) while signed in as the same user; refresh the page and show it resolves to the same product. Review component condition, plan progress, and timeline after those later steps are saved. Explain that another account cannot resolve the private QR and that user-submitted history/ownership is not independently verified.
5. **Need-before-waste matching:** Select a saved product, compare category/condition/location-ranked sample requests, then move one from pending to accepted to completed. Emphasize that the sample recipients are not contacted.
6. **Salvage intelligence:** Select the same Laptop record, generate its laptop-specific component list, mark RAM Working, SSD Untested, and battery Damaged, then save. Show that only a supported user-marked-working component receives an illustrative range. Refresh and verify that the states remain; explain that component function is not independently verified.
7. **Future-life simulator:** Select that same laptop. Edit repair/resale amounts, additional useful life, comparison period, reuse/salvage assumptions, and replacement cost. Show the chart, six live-updating scenarios, estimated cost per additional year, calculation formula, and uncertainty. Save a comparison and refresh to show assumptions persist. Do not claim measured environmental savings.
8. **Rescue chain:** Generate a plan for the same laptop. Mark a step unavailable, use Find Alternative, then mark the fallback completed. Refresh and show both statuses persist. Broken products avoid whole-item resale/donation/reuse routes; battery and electrical work requires safe, qualified handling.
9. **Recovery centers:** Search OpenStreetMap by city/district/postal code and pathway, then review map-listed phone/email/site details and any parsed opening-hour status. Open the map entry and explain that hours may be stale and service capacity must be confirmed. Switch to the sample directory to filter demo records by category and pathway.
10. **History and impact report:** Return to history, open passports, review user-marked completed steps, export the activity CSV, and clarify that environmental and monetary totals are deliberately not invented.

## Project layout

```text
ReLife-AI/
├── backend/
│   ├── app/
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/UI.jsx
│   │   ├── pages/AuthPage.jsx
│   │   ├── services/api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```
