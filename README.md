# ITR Assistant – AI-Powered Income Tax Return Filing Assistant

An AI-powered tax filing assistant that simplifies the Indian Income Tax Return (ITR) filing process using OCR, Large Language Models (LLMs), and an interactive field-level AI assistant.

The application helps users select the correct ITR form, extract information from tax documents, auto-fill form fields, and receive contextual assistance while completing their tax returns.

---

## Overview

ITR Assistant is designed to reduce the complexity of tax filing by combining:

* AI-powered ITR form selection
* OCR-based document processing
* Intelligent tax data extraction
* Automatic form population
* Interactive field-level assistance

Unlike traditional form-filling systems, users can interact with an AI assistant throughout the filing process to understand tax concepts and complete forms accurately.

---

## Key Features

### AI-Powered ITR Selection Assistant

Before filing begins, users interact with an intelligent tax assistant that helps determine the appropriate Income Tax Return form.

#### Capabilities

* Conversational chat-based interface
* Natural language interaction
* Follow-up question generation
* Income source analysis
* Tax profile assessment
* Intelligent ITR recommendation

#### Supported Forms

* ITR-1
* ITR-2
* ITR-3
* ITR-4

#### Example

**User:** "I have salary income and some stock market gains."

**Assistant:** Asks follow-up questions and recommends the appropriate ITR form.

---

### Smart PDF Processing

* Upload tax-related PDF documents
* Supports both digital and scanned PDFs
* Automatic text extraction
* Multi-page document support
* OCR fallback for scanned documents

---

### OCR-Based Document Understanding

Powered by Tesseract OCR.

#### Features

* Scanned PDF support
* Image-based document processing
* Automatic text recognition
* Tax document digitization

---

### AI-Powered Data Extraction

The system uses Large Language Models to understand extracted document content and populate tax forms automatically.

#### Capabilities

* Intelligent information extraction
* Schema-aware field mapping
* JSON-based structured output
* Validation-aware processing
* Reduced manual data entry

---

### Interactive AI Field Assistant ⭐

One of the most unique features of the application.

Users can interact with an AI assistant directly from any form field.

#### How It Works

1. User double-clicks any field.
2. A contextual AI chat panel opens.
3. The assistant explains the selected field.
4. Users ask questions related to that field.
5. The assistant maintains field-specific context.
6. If enough information is provided, the field is automatically populated.

#### Capabilities

* Field explanations
* Tax guidance
* Context-aware conversations
* Dropdown assistance
* Value recommendations
* Automatic field updates

####

---

### Session Management

* Create filing sessions
* Save progress
* Resume previous sessions
* Manage multiple filing records

---

### Privacy-Focused PDF Redaction

Users can redact sensitive information before document processing.

#### Benefits

* Enhanced privacy
* Controlled data extraction
* Sensitive information protection

---

## Application Workflow

```text
User Opens Application
        │
        ▼
AI ITR Selection Assistant
        │
        ▼
ITR Form Recommendation
        │
        ▼
Initialize Selected ITR Form
        │
        ▼
Upload Tax Documents (Optional)
        │
        ▼
PDF Text Extraction (PyMuPDF)
        │
        ▼
OCR Processing (Tesseract)
        │
        ▼
LLM-Based Information Extraction
        │
        ▼
Schema Validation & Mapping
        │
        ▼
Pre-filled ITR Form
        │
        ▼
Interactive AI Field Assistant
        │
        ▼
Automatic Field Updates
        │
        ▼
Save Filing Session
```

---

## Technology Stack

### Backend

* FastAPI
* Python

### AI & LLM

* OpenAI GPT-4o Mini
* OpenRouter API

### OCR & Document Processing

* Tesseract OCR
* PyMuPDF
* Pillow

### Frontend

* HTML
* CSS
* JavaScript

### Data Storage

* JSON-Based Templates
* Session-Based Storage

---

## Project Structure

```text
ITR-Assistant/
│
├── app.py
├── ai_logic.py
├── tools.py
├── requirements.txt
│
├── data/
│   ├── itr1_template.json
│   ├── itr2_template.json
│   ├── itr3_template.json
│   └── itr4_template.json
│
├── static/
│   ├── index.html
│   ├── login.html
│   ├── ITR1.html
│   ├── ITR2.html
│   ├── ITR3.html
│   ├── ITR4.html
│   └── shared.js
│
├── data/sessions/
│
└── Sample data for test/
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/Prashant-7058/itr-assistant.git
cd itr-assistant
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / macOS

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_api_key_here
```

---

## Run the Application

```bash
uvicorn app:app --reload
```

Open:

```text
http://localhost:8000
```

##
