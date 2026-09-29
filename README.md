# 📡 Resilient Zero-Token Hourly News Aggregator
> **پایگاه خبری بدون توکن، تاب‌آور در شرایط اینترنت ملی و مسدودسازی کامل شبکه**  
> Deployed on GitHub Actions, GitHub Pages, and Vercel.

A fully autonomous, zero-cost news monitoring system designed for severe internet throttling, DNS poisoning, and national intranet (NIN / شبکه ملی اطلاعات) blackouts in Iran.

---

## 🌟 Key Architectural Features

- **Zero LLM Tokens ($0.00 / month):** Runs on pure Python standard library (`urllib.request`, `xml.etree.ElementTree`). Requires zero external LLM API tokens (OpenAI, Anthropic, Gemini), eliminating foreign billing traps, sanctions barriers, or upstream API rate limits.
- **High-Trust Source Ingestion:** Aggregates real-time feeds across:
  * **Persian News:** BBC Persian, Radio Farda, Iran International, Euronews Persian, DW Persian.
  * **Global Wire:** Reuters, Associated Press (AP News).
  * **Tech & Open Source:** Hacker News.
- **Hourly Snapshot Architecture:** Saves immutable hourly archives to `news/YYYY-MM-DD/HH-00.md`, maintains rolling `news/latest.md`, and compiles a chronological archive index in `index.md`.
- **Dual Timezone Formatting:** All entries and headlines carry both **UTC** and **Iran Standard Time (IRST = UTC+3:30)** timestamps.
- **Micro-Payload Engineering (< 15 KB):** In conditions where a normal 6 MB news website times out and fails, raw Markdown downloads in under 3 seconds even on a throttled 32 kbps connection.
- **Dual Hosting & Redundancy:**
  * **GitHub Pages & Raw CDN:** Accessible via `raw.githubusercontent.com` and GitHub Pages.
  * **Vercel Edge Anycast:** Instant global edge routing via `*.vercel.app` with zero-config deployment.
- **Local & Offline Friendly:** Clone once; an incremental `git pull` takes seconds and updates your entire local archive, seamlessly readable in Obsidian, VS Code, or Termux.

---

## 📂 Project Directory Structure

```text
resilient-news-aggregator/
├── .github/
│   └── workflows/
│       └── news.yml             # Hourly GitHub Actions cron workflow
├── news/
│   ├── YYYY-MM-DD/
│   │   ├── 00-00.md             # Hourly snapshots (UTC / IRST)
│   │   ├── ...
│   │   └── 23-00.md
│   └── latest.md                # Rolling latest headlines digest
├── public/
│   ├── index.html               # Lightweight (<30 KB) RTL static web dashboard
│   └── latest.json              # Machine-readable JSON feed for curl / CLI
├── aggregator.py                # Pure Python standard-library aggregator engine
├── run_local.sh                 # Local / VPS crontab execution script
├── vercel.json                  # Vercel edge deployment configuration
├── index.md                     # Root archive index & quick access links
├── state.json                   # SHA-256 deduplication state cache
├── BLACKOUT_RESILIENCE.md       # Technical deep-dive on Iranian network topology
└── README.md                    # Project documentation
```

---

## 🚀 Quickstart & Deployment

### 1. GitHub Actions Setup (Zero Maintenance)
1. Fork or push this repository to GitHub.
2. Go to **Settings → Actions → General → Workflow permissions**.
3. Select **Read and write permissions** (allows the workflow to commit hourly news files).
4. Go to **Settings → Pages**:
   - Source: **GitHub Actions** (the workflow deploys automatically).
5. The workflow in `.github/workflows/news.yml` will automatically run at the start of every hour (`cron: '0 * * * *'`), or trigger it manually anytime under the **Actions** tab via **Run workflow**.

### 2. Vercel Mirror Setup (1-Click)
1. Log in to [Vercel](https://vercel.com) and click **Add New Project**.
2. Select this GitHub repository.
3. In Build & Output Settings:
   - Output Directory: `public` (pre-configured in `vercel.json`).
4. Click **Deploy**. Vercel will automatically redeploy on every hourly commit pushed by GitHub Actions.

### 3. Local Machine / Remote Linux VPS Setup
To run the sync locally or on a personal VPS:

```bash
# Clone the repository
git clone https://github.com/<your-username>/resilient-news-aggregator.git
cd resilient-news-aggregator

# Run immediately
python3 aggregator.py

# Add to crontab for hourly updates
crontab -e
# Add the following line:
0 * * * * /home/ubuntu/resilient-news-aggregator/run_local.sh >> /var/log/news_sync.log 2>&1
```

---

## 📱 How to Access News During Network Blackouts

### 1. Minimal Bandwidth Raw Markdown (Fastest)
Open directly in any mobile or desktop browser:
```text
https://raw.githubusercontent.com/<user>/<repo>/main/news/latest.md
```
Or stream in your terminal:
```bash
curl -sL https://raw.githubusercontent.com/<user>/<repo>/main/news/latest.md | less
```

### 2. Machine-Readable JSON for Scripts & Bots
```bash
curl -sL https://raw.githubusercontent.com/<user>/<repo>/main/public/latest.json | jq .
```

### 3. Git-Over-SSH (Bypassing TLS Middleboxes)
If HTTPS ports (443) are subject to aggressive DPI throttling:
```bash
git pull origin main
```
Git fetches compressed zlib packfiles over SSH (port 22), evading TLS SNI middleboxes.

### 4. Offline Obsidian / Markdown Reader
Clone this repository directly into an **Obsidian** vault. Even if you only get a 5-second window of connectivity per day, a single `git pull` downloads all missed hourly bulletins into your local searchable notes.

---

## 🛡️ Deep Resilience Technical Analysis

For an in-depth technical analysis of:
- Why `github.com` and `raw.githubusercontent.com` survive Iranian national intranet (NIN) whitelisting,
- The domestic tech ecosystem dependency shield (Snapp, Digikala, Divar, npm, pip, go get),
- Fastly Anycast and Vercel edge IP distribution,
- Layer 7 SNI inspection vs Layer 3/4 border gateway drops,

👉 **Read the full whitepaper:** [`BLACKOUT_RESILIENCE.md`](BLACKOUT_RESILIENCE.md).
