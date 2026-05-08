# CVify

CVify is a desktop CV builder that helps you craft ATS-friendly CVs with AI-assisted tailoring. It stores your profile locally in SQLite and can generate a LaTeX-based PDF for each job description.

## Features
- Guided CV sections with autosave
- AI-enhanced bullet points and summaries
- Job description match analysis
- LaTeX CV generation with PDF preview
- Local data storage (SQLite)

## Requirements
- Python 3.10+ (tested on Python 3.13)
- Windows, macOS, or Linux
- Optional: LaTeX (pdflatex) for PDF output
- Optional: OpenRouter API key for real AI output
- Optional: SMTP credentials to send verification emails

## Setup

### 1) Clone and create a virtual environment

Windows (PowerShell):
```powershell
git clone https://github.com/HxRJILI/CVify
cd CVify
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
git clone https://github.com/HxRJILI/CVify
cd CVify
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

If the large PyQt6-Qt6 download times out, just rerun the install command until it completes.

### 3) Create a .env file
Create a `.env` file in the project root:
```env
DATABASE_URL=sqlite:///cvify.db
OPENROUTER_API_KEY=your_openrouter_api_key_here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com
SECRET_KEY=change-me
```

Notes:
- If `OPENROUTER_API_KEY` is missing, the app uses mock AI responses.
- If SMTP values are missing, OTP codes are printed to the terminal instead of being emailed.

## Run the app
```bash
python main.py
```

## Usage flow
1. Sign up with an email and password.
2. Verify the account using the OTP (printed in the terminal if SMTP is not configured).
3. Fill in CV sections (Essentials, Power-Ups, Differentiators, Personal Touch).
4. Go to Generate CV, paste a job description, analyze match, and generate a LaTeX/PDF CV.
5. Output files are saved to `~/Documents/CVify`.

## Optional: Enable PDF output
To generate PDFs, install a LaTeX distribution with `pdflatex`:
- Windows: MiKTeX
- macOS: MacTeX
- Linux: TeX Live

If `pdflatex` is not installed, the app saves a `.tex` file instead.

## Troubleshooting
- Font warnings on startup mean custom fonts are missing from `assets/fonts`. The UI will still run with system fonts.
- If you see `ModuleNotFoundError` for PyQt6 or SQLAlchemy, re-run `pip install -r requirements.txt`.
- The database file is `cvify.db` in the project root by default.
