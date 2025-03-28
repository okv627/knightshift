# ♞ KnightShift: Lichess Data Pipeline

KnightShift is a production-style chess data pipeline that ingests real-time
Lichess TV games, parses PGN data, and stores structured game records in a
PostgreSQL database.

This project simulates real-world data engineering practices—secure
secrets management, stream-style ingestion, schema-aware transformation,
and upsert logic.

---

## 🧠 What It Does

- Streams live chess games from multiple Lichess TV channels (e.g. blitz, rapid, horde).
- Parses PGN-formatted chess data into structured records.
- Transforms raw PGN into a clean schema: player names, ratings, results, time control, etc.
- Performs upserts into PostgreSQL using SQLAlchemy Core.
- Uses AWS Secrets Manager to securely load DB credentials.

---

## 🛠 Tech Stack

- **Python 3.10+**
- **PostgreSQL**
- **SQLAlchemy Core**
- **AWS Secrets Manager** (`boto3`)
- **Requests** (API interaction)

---

## 📁 Project Structure

```
knightshift/
├── docs/
│   ├── README.md                     # Project overview, instructions, and docs
│   ├── CHANGESLOG.md                # Change history and version notes
│   └── database_schema.md           # Markdown version of database schema
├── src/
│   ├── __init__.py                  # Makes src a Python package
│   ├── clean_invalid_games.py       # Data cleaning: remove invalid game records
│   ├── db_utils.py                  # Shared DB credential and connection utilities
│   ├── get_games_from_tv.py         # Fetch games from Lichess TV
│   ├── get_games_from_users.py     # Fetch games for a particular user
│   ├── main.py                      # Orchestrator: runs full pipeline
│   ├── update_all_games.py         # Update games in the database
│   └── .env.local                   # Local environment variables
├── .env.docker                      # Docker-specific environment variables
├── .gitignore                       # Git ignore file
├── Dockerfile                       # Docker image setup for the pipeline
├── docker-compose.yml               # Defines and runs both DB and pipeline
├── requirements.txt                 # List of Python dependencies
└── run.sh                           # Shell script to run the project
```

---

## 🔐 Secrets Management

Credentials are securely pulled from AWS Secrets Manager.

Expected secret format:

```json
{
  "PGHOST": "your-db-host",
  "PGPORT": "5432",
  "PGDATABASE": "your-db-name",
  "PGUSER": "your-username",
  "PGPASSWORD": "your-password"
}
```

---

## ▶️ How to Run

1. Create a Postgres database and store credentials in AWS Secrets Manager.

2. Install Python dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Run the pipeline:

   ```
   python main.py
   ```

The pipeline fetches Lichess games every 40 seconds for 5 hours, 
processes them, and stores them in your Postgres database.

---

## 🚧 Future Expansion: Chess Analytics Pipeline (Multi-Source)

This project will evolve into a full **Chess Analytics Pipeline** with:

### ✈️ Multiple Data Sources

- **Lichess (Real-Time):** PGN from TV stream and export API
- **Kaggle Archive:** Millions of historical games
- **FIDE Ratings:** Public CSVs with official player data

### ⚙️ Architecture Components

- **Staging in RDS (PostgreSQL)**
- **Raw Data in S3 Buckets**
- **Transformation Jobs via AWS Glue or Python**
- **Partitioned Tables & Concurrency Controls**
- **Analytics Layer in Redshift or a second Postgres**
- **Dashboards with AWS QuickSight**

### 🏗 Planned Expansion by Month

**Month 1:**

- Refactor ingestion scripts
- Local Docker + Postgres setup
- Create first working Dockerfile

**Month 2:**

- Automate ingestion via cron or Airflow (locally)
- Add simple data validation (e.g. ELO range checks)

**Month 3:**

- Partition Postgres by date
- Add concurrency safety (transactions or row locks)
- Add full PGN enrichment via Lichess export API

**Month 4:**

- Deploy ingestion & enrichment in Kubernetes (Minikube/Kind)
- Run Airflow inside K8s cluster

**Month 5:**

- Add Great Expectations for data quality
- Monitor jobs with Prometheus & Grafana

**Month 6:**

- Load to Redshift or warehouse instance
- Create aggregated views (fact/dimension tables)
- Build public dashboards with QuickSight

---

## 📌 Final Goal

Build a robust, multi-source chess data pipeline capable of:

- Continuous real-time ingestion
- Historical + official data merging
- Schema evolution
- Analytics-ready warehousing
- Production-grade monitoring
- BI dashboards

---

## 📅 Built By

[Matthew Tripodi](https://github.com/okv627)

Let me know if you’d like to see the public dashboard or learn more about
the architecture behind KnightShift.