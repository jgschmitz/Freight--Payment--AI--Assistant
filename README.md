# Freight Payment AI Assistant – MongoDB Atlas Vector Search Demo

This repository demonstrates how to power an AI-driven Freight Payment dashboard using **MongoDB Atlas Vector Search** and **Voyage AI embeddings**. The goal is to show how semantic search can identify related invoice events, carrier issues, and audit alerts—supporting an assistant experience like the example UI.

---

## 🚀 Overview

The system ingests event records containing fields such as transaction status, carrier updates, and error reasons.  
We embed the **`reason`** text using the *voyage-3-large* embedding model and store the vector in MongoDB Atlas under:

```
Reason_Embedded
```

A Vector Search index is created on this field, enabling queries like:

> “Show me events similar to ‘payload validation failed’”

This allows the AI Assistant to surface meaningful patterns and related alerts even when the text does not match exactly.

---

## 🗂 Project Structure

```
.
├── README.md
├── embed.py          # Script to generate embeddings and store Reason_Embedded
├── qvec.py           # Script to run semantic vector search queries
└── requirements.txt  # Python dependencies
```

---

## 📦 Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure keys inside `embed.py` and `qvec.py`

Set:

```python
MONGODB_URI = "<your MongoDB Atlas connection string>"
VOYAGE_API_KEY = "<your VoyageAI key>"
```

### 3. Run the embedding pipeline

```bash
python3 embed.py
```

This script:
- Reads `event.eventData.subTypeData.reason`
- Generates embeddings via VoyageAI
- Stores them into the document as `Reason_Embedded`

---

## 🔍 Create the Vector Search Index

In the MongoDB Atlas UI → **Indexes → Create Vector Search Index → JSON**, use:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "Reason_Embedded",
      "numDimensions": 1024,
      "similarity": "cosine"
    }
  ]
}
```

---

## 🧠 Run Semantic Search

Use `qvec.py`:

```bash
python3 qvec.py
```

Example output:

```
{'score': 0.83, 'reason': 'Payload validation failed'}
{'score': 0.74, 'reason': 'Notification sent to client'}
{'score': 0.73, 'reason': 'Awaiting downstream confirmation'}
```
