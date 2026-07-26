# AI expenses report

> Smart API that extracts and categorizes expenses from receipt photos and PDFs using AI (Gemini/OpenAI), with auto-deduplication, individual item filtering, and financial summaries by period.

**🔥 What used to take hours now happens in seconds:**
- 📸 Processes receipt photos, bank transfers, and PDFs
- 🧠 AI extracts amount, merchant, date, and category automatically
- 🚫 Auto-deduplicates (same receipt from multiple photos)
- 🎯 Filters out individual line items vs real totals
- 📊 Period summary ready to share

### Tech Stack
`FastAPI` `Python` `Gemini API` `OpenAI` `PyMuPDF` `Pydantic` `Tenacity`

### Quick Start
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Topics
`fastapi` `python` `gemini-api` `openai` `computer-vision` `expense-tracker` `financial-api` `pdf-parser` `fintech`
