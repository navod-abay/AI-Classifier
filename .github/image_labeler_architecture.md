# Laptop Flask Labeler System Design

## Purpose

This guide describes exactly how to build and run the **Flask-based labeling server** and the **sync worker** on a Windows laptop. The system labels images with keep/delete decisions and manages face recognition interactively while working offline. The laptop **does not run any OCR itself** — it only pulls OCR text data already prepared and stored on the NAS. Synchronization runs automatically every 10 minutes as a **Windows Scheduled Task** that runs a Python script and exits.

---

## Required Directories

- `cache/images/` — Local images to label
- `cache/ocr/` — OCR text files pulled from NAS (no OCR happens on the laptop)
- `cache/labels.csv` — Image file names with keep/delete decision
- `cache/faces.pkl` — Known face embeddings and names

## SMB Mount

- Map the NAS share as a Windows network drive (e.g., `Z:`).

---

## Background Sync Worker

- Implemented as a **Python script (`worker.py`)**.
- Uses `rsync` for Windows (e.g., cwRsync).
- The Windows Scheduled Task runs the Python script every 10 minutes and exits.
- The SSID condition is enforced in Task Scheduler: the task runs only if connected to Wi-Fi SSID "Abayasekera".
- The Python script runs these exact commands:
  - `rsync -av --ignore-existing Z:/photos_preprocessed/ cache/images/`
  - `rsync -av --ignore-existing Z:/ocr_data/ cache/ocr/`  *(OCR text is only pulled; no OCR is done locally)*
  - `rsync -av cache/labels.csv Z:/labels/`
  - `rsync -av cache/faces.pkl Z:/known_faces/`

---

## Flask Labeler Server

- Runs locally on Windows.
- Provides a web UI at `http://127.0.0.1:5000`.
- Loads images and OCR from `cache/`.
- Detects faces with the `face_recognition` library.
- Compares embeddings to `faces.pkl`.
- Displays cropped faces with name suggestions.
- User can rename or confirm names.
- Saves new faces to `faces.pkl`.
- Stores keep/delete decisions in `labels.csv`.

## Python Dependencies

- Flask
- face_recognition
- numpy
- pandas
- pickle

## Files to Provide

- `app.py` — Flask server
- `worker.py` — Python sync worker
- `requirements.txt`

## How to Run

1. Map the NAS SMB share to `Z:`.
2. Register `worker.py` as a Windows Scheduled Task that runs every 10 minutes, only when connected to SSID "Abayasekera".
3. Run `app.py` with `python app.py`.
4. Open the web interface to start labeling.

## Behavior

- Sync only runs when connected to "Abayasekera" Wi-Fi.
- The laptop does not run any OCR — OCR text is always fetched from NAS.
- Local labeling works offline using cached data.
- Labeled data syncs automatically when reconnected.

---

## Deliverables

A complete local cache, a Python sync worker run as a Windows Scheduled Task, and a Flask web server for labeling and face recognition. The laptop never performs OCR locally.

