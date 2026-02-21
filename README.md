# MIVA LMS Automation (Playwright · Python)

Automates routine activity completion on Miva University’s LMS using Playwright.  
Features smart resume, reconnaissance scanning, parallel processing, and detailed progress/reporting.

---

## 🚀 Features

- Reconnaissance scan to estimate workload and plan course order  
- Smart resume prioritizing in-progress courses  
- Parallel processing (4 tabs) for faster throughput  
- Balanced-fast timing for human-like interaction  
- Robust retry logic with screenshots on errors  
- Progress tracking to JSON with detailed final reports  
- Cookie-based session reuse (no credentials stored)  

---

## 🛠 Tech Stack

- Python 3.10+
- Playwright (async) `playwright==1.48.0`

---

## 📂 Project Structure

- `miva_automation_ultimate.py` — Main automation engine  
- `test_login.py` — Interactive login helper (saves cookies)  
- `miva_session_cookies.json` — Saved session cookies  
- `miva_progress.json` — Progress tracking (per course, activities)  
- `miva_report_YYYYMMDD_HHMMSS.json` — Run summaries  
- `miva_screenshots/` — Error/debug screenshots  
- `requirements.txt` — Python dependencies  

---

## ⚡ Quick Start

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
playwright install
```

### 2️⃣ Save Login Cookies (Interactive Helper)

```bash
python test_login.py
```

Steps:
- Log in to MIVA LMS in the opened browser  
- Navigate to your courses dashboard  
- Return to the terminal and press ENTER  
- Cookies will be saved to `miva_session_cookies.json`  

### 3️⃣ Run the Automation

```bash
python miva_automation_ultimate.py
```

What happens:
- Script reuses saved cookies  
- Scans courses  
- Prioritizes intelligently  
- Processes activities  
- Generates final report  

---

## ⚙️ Configuration

All key settings live inside `CONFIG` in `miva_automation_ultimate.py`.

### URLs
- `base_url`
- `courses_url`

### Session Files
- `cookies_file`
- `progress_file`
- `screenshots_dir`

### Speed / Timing
- `page_load_wait`
- `content_view_time`
- `between_activities`
- `between_courses`
- `scroll_pause`

### Parallelism
- `parallel_tabs` (default: 4)

### Behavior Flags
- `skip_quizzes`
- `skip_assignments`
- `auto_resume`
- `run_reconnaissance`
- `headless`

### Activity Filters
- `skip_patterns`
- `complete_patterns`

Set `headless=True` to run without opening a visible browser.

---

## 🧠 How It Works

- Discovers courses and activities from LMS dashboard  
- Skips quizzes and assignments by default  
- Processes pages, URLs, forums  
- Marks completion where manual controls exist  
- Retries failed activities up to `max_retries`  
- Writes cumulative progress to `miva_progress.json`  
- Saves final summary to `miva_report_YYYYMMDD_HHMMSS.json`  

---

## 🛠 Troubleshooting

**Not logged in?**  
→ Run `python test_login.py` again and ensure you're on the courses page before pressing ENTER.

**Empty course list?**  
→ Verify LMS access and confirm `courses_url` is correct.

**Playwright errors?**  
→ Re-run `playwright install` and confirm Chromium launches properly.

**Need debugging context?**  
→ Check `miva_screenshots/`.

---

## ⚖️ Ethics & Use

Use responsibly and in accordance with MIVA University policies.  
This tool assists with repetitive navigation and tracking — it does not bypass academic requirements.

---

## 📜 License

Personal / educational use.  
Adapt as needed.
