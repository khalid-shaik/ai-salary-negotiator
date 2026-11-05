# 💰 AI Salary Negotiator

** AI agents.** Analyse a job offer, build a negotiation plan, write the message and practise the conversation. Runs locally; **everything except optional AI polish works offline**.

## Features
- **Offer & market:** total compensation (base, expected variable, haircut ESOP, benefits, joining bonus), fixed-pay share, and an approximate market percentile from the range you enter
- **Strategy:** leverage score from a checklist, then an anchor (first ask), target and walk-away with plain-English reasoning, plus non-salary items to ask for
- **Scripts:** counter-offer email, call talking points, reply to "this is our best offer", request more time, decline, accept. Three tones, editable, downloadable. Optional AI polish via Ollama
- **Draft reviewer:** paste your own message and get an offline checklist score (thanks, specific figure, reasons, collaborative tone, no ultimatums) plus optional AI feedback
- **Practice:** negotiate against a simulated recruiter with a hidden budget. It rewards specific asks with reasons and shows how much room was left at the end
- **Compare offers:** side-by-side steady and year-1 totals with a chart
- INR (lakhs), USD, EUR, GBP

## Tech stack
Python · Streamlit · Ollama · pandas · pytest · GitHub Actions

## Quick start
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
Click **Load sample data** in the sidebar to try it. For AI polish, install Ollama and run `ollama pull llama3.2`.

## Project structure
```
app.py               Streamlit UI (5 tabs)
core/money.py        formatting and parsing amounts like "9 LPA", "95k", "12,00,000"
core/analyze.py      total comp, percentile, leverage, negotiation plan
core/scripts.py      message templates and the draft critic
core/roleplay.py     rule-based recruiter for practice
core/llm.py          optional Ollama polish and critique
tests/               pytest unit and UI tests (46)
```

## Important notes
- Market ranges are entered by you. This app does not fetch live salary data, so use AmbitionBox, Glassdoor, Levels.fyi or LinkedIn Salary.
- It does not compute income tax or in-hand pay. Compare in-hand pay with an up-to-date tax calculator before deciding.
- The percentile is an approximation based on your low / mid / high inputs.
- Never lie about competing offers. The tool is built around honest, collaborative negotiation.

## Tests
```bash
pytest -q
```

## Roadmap
- [ ] India in-hand salary estimator (old vs new tax regime)
- [ ] Save and load negotiation sessions
- [ ] Voice practice
