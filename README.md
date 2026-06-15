# AI Job Hunter 🚀

An automated job search pipeline that scrapes job postings, matches them against your specific skills and preferences, notifies you via Telegram, and displays the results in a local interactive Dashboard.

## 🌟 Features
- **Automated Job Scraping:** Scrapes job listings from reliable job board APIs (RemoteOK, Arbeitnow, Jobicy, and FindWork).
- **Skill-Based Matching:** Uses custom regex word boundary logic to match job descriptions against your technical skills and calculates a relevance score.
- **Telegram Notifications:** Sends real-time alerts to your personal Telegram via a Telegram Bot for high-scoring job matches.
- **Interactive Dashboard:** Provides a local graphical web interface (`dashboard/index.html`) to visualize, filter, and track job postings.
- **Local Database:** Silently stores job history via `database.py` so you continuously build an archive of matching job listings without duplicates.
- **Automated Scheduling:** Includes scripts to easily set up automated background execution natively on Windows.

## 📁 Project Structure
```text
.
├── config.yaml                # Core configuration (Telegram tokens, user profile, skills)
├── resume_knowledge.txt       # Your resume context text
├── requirements.txt           # Python package dependencies
├── run.bat                    # Batch script to execute the script manually
├── setup_scheduler.ps1        # PowerShell script to automate running on a schedule
├── dashboard/
│   ├── index.html             # The frontend dashboard GUI
│   └── data.js                # Auto-generated job data for the dashboard UI
├── data/                      # Auto-generated folder containing the database and logs
└── src/
    ├── main.py                # Main orchestrator linking scraping, matching, and notifying
    ├── database.py            # Local database operations handler
    ├── matcher.py             # Rule-based skill matching and scoring engine
    ├── notifier.py            # Telegram messaging integration
    └── scrapers.py            # API implementations for the different job boards
```

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Python 3.8+** installed on your system.
- A **Telegram Bot Token** (Create one via [@BotFather](https://t.me/BotFather) on Telegram).

### 2. Install Dependencies
From the project root directory, install all required packages:
```bash
pip install -r requirements.txt
```

### 3. Customize Your Profile
Open `config.yaml` and configure it with your details:
- **Telegram Credentials:** Insert your `bot_token` and `chat_id`. 
  *(Tip: The script can attempt to auto-detect your `chat_id` if you send a message to your bot and leave it blank)*
- **Contact Details:** Update with your name, email, GitHub, and LinkedIn.
- **Job Targeting:** Carefully outline your `keywords`, `skills`, and `location_preferences` list so the matcher engine scores jobs accurately.
- *(Optional)* Update `resume_knowledge.txt` to include more context about your work experience if utilized by future LLM matching updates.

### 4. Running the Pipeline
You can test and run the agent manually by executing:
```bash
run.bat
```
Alternatively, in your terminal:
```bash
python src/main.py
```

### 5. Accessing the Dashboard
To see the jobs it has found and scored for you, simply double-click and open the following file in any web browser:
> `dashboard/index.html`

The script automatically generates `dashboard/data.js` containing your matched jobs, so the dashboard will accurately reflect the most recent run.

## 🔄 Windows Background Automation
Don't want to run it manually? You can schedule the pipeline to run perpetually in the background. 
Simply Right-Click `setup_scheduler.ps1` and choose **Run with PowerShell**. This leverages the Windows Task Scheduler to execute the hunter at regular intervals.
