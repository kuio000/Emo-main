
# Privacy-Preserving Mobile Web Framework for Depression Screening

A cross-platform, privacy-first mobile web application that integrates real-time client-side MediaPipe landmark tracking with digital PHQ-9 questionnaires for decentralized depression screening. 

By executing MediaPipe Face Mesh via WebAssembly (WASM) directly within the user's mobile browser, the platform extracts frame-by-frame Eye Aspect Ratio (EAR), Mouth Aspect Ratio (MAR), and Eyebrow Distance (EBD) features without transmitting raw video feeds, ensuring full GDPR biometric privacy compliance and client-side data sovereignty.

## Key Features

* **Client-Side Edge Inference**: Real-time 468-point 3D facial landmark tracking powered by MediaPipe Face Mesh and WebAssembly (WASM).
* **GDPR Biometric Privacy**: Raw camera streams are processed entirely in browser memory frame-by-frame and immediately discarded; zero raw video leaves the client device.
* **Multi-Stage Consent Flow**: Granular participant registration, ethical consent collection, and customizable biometric data preservation choices.
* **Synchronized Affective Stimuli**: Embedded video playback pipeline featuring standardized Comedy, Neutral, and Sad Cinema clips.
* **Digital Psychometric Assessment**: Mobile-optimized, touch-friendly 9-item PHQ-9 questionnaire with automated clinical score calculation.
* **Automated Data Analysis**: Integrated Python analytics suite for Pearson correlation analysis, Ridge regression modeling, and Leave-One-Out Cross-Validation (LOOCV).

---

## Repository Structure

```text
Emo-main/
├── app.py                  # Flask backend server & REST API routes
├── extract_features.py     # Batch feature extraction & landmark processing
├── analyze_data.py         # Statistical correlation analysis & Ridge regression script
├── dataset.csv             # Anonymized statistical biomarker dataset (N=20)
├── face_landmarker.task    # MediaPipe Task Vision model binary for 3D landmarking
├── requirements.txt        # Python dependency specifications
├── .env.example            # Environment variables configuration template
├── .gitignore              # Version control exclusion rules
├── ngrok.exe               # Secure HTTPS tunneling utility for mobile remote testing
├── db/
│   └── CSProject.db        # SQLite database for participant metadata & PHQ-9 records
├── static/
│   ├── images/             # Static UI graphic assets and icons
│   └── stimulus_videos/    # Standardized video stimuli (Comedy, Neutral, Sad)
└── templates/              # Jinja2 HTML templates for multi-step workflow
    ├── welcome.html        # Landing page & study entry
    ├── consent.html        # Information sheet & general ethical consent
    ├── data_consent.html   # Biometric privacy & photo retention options
    ├── consent_declined.html
    ├── experiment.html     # Real-time WASM video elicitation & tracking page
    ├── phq9.html           # Touch-optimized digital PHQ-9 survey
    └── result.html         # Score summary & clinical disclaimer feedback

```

---

## Quick Start & Local Deployment

### 1. Prerequisites

* Python 3.9+ installed
* Modern Web Browser (Safari Mobile, Chrome Mobile, or Firefox) with WebGL enabled
* Webcam/Front Camera access

### 2. Environment Setup

Clone the repository and create a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 3. Configuration

Copy the template configuration file and configure environment variables:

```bash
cp .env.example .env

```

### 4. Run the Flask Backend

Initialize the server:

```bash
python app.py

```

### 5. Accessing & Testing the Platform

* **Local Desktop Testing**: Open your browser and navigate directly to:
```text
[http://127.0.0.1:5000](http://127.0.0.1:5000)

```


* **Remote Mobile Testing (HTTPS Tunneling)**: MediaPipe webcam access on mobile browsers requires a secure origin (`https://`). To test on remote physical smartphones:
```bash
./ngrok.exe http 5000

```

Open the generated HTTPS forwarding URL (or the active public tunnel link: https://gangly-kindly-fragrant.ngrok-free.dev) on your mobile device.

---

## Data Analysis & Machine Learning Pipeline

Once trial participant sessions are completed and logged, execute the analytical scripts:

1. **Feature Processing**:
```bash
python extract_features.py

```


2. **Statistical Correlation & Model Training**:
```bash
python analyze_data.py

```


*Runs Pearson correlation (`r`, `p-values`) between extracted dynamic ratios (`MAR`, `EAR`, `EBD`) and `PHQ-9` scores, followed by Leave-One-Out Cross-Validation (LOOCV) via regularized Ridge regression.*

---

## License & Ethics

This project was developed as part of an MSc Computer Science dissertation at the School of Computing Science, University of Glasgow. All experimental protocols strictly comply with GDPR data protection standards and ethical research guidelines.