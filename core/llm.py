"""Optional AI polish for negotiation messages (Ollama, local)."""
import json
import re

import ollama

SYSTEM = (
    "You are an expert, ethical salary-negotiation coach. Use ONLY the facts and figures provided; never invent numbers, "
    "competing offers or achievements. Keep messages polite, confident and collaborative. Reply with a single valid JSON object only."
)


def parse_json(raw: str) -> dict:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise ValueError("Model did not return JSON.")
        return json.loads(m.group(0))


def list_models(host: str | None = None) -> list[str]:
    try:
        client = ollama.Client(host=host) if host else ollama.Client()
        resp = client.list()
        models = resp["models"] if isinstance(resp, dict) else resp.models
        return sorted((m["model"] if isinstance(m, dict) else m.model) for m in models)
    except Exception:
        return []


def _chat(prompt, model, host, temperature) -> dict:
    client = ollama.Client(host=host) if host else ollama.Client()
    resp = client.chat(model=model, messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                       format="json", options={"temperature": temperature})
    content = resp["message"]["content"] if isinstance(resp, dict) else resp.message.content
    return parse_json(content)


def normalize_script(d: dict, fallback: dict) -> dict:
    body = str(d.get("body", "")).strip()
    return {"subject": str(d.get("subject", "")).strip() or fallback["subject"], "body": body or fallback["body"]}


def normalize_critique(d: dict) -> dict:
    lst = lambda v: [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []
    return {"strengths": lst(d.get("strengths")), "improvements": lst(d.get("improvements")), "rewrite": str(d.get("rewrite", "")).strip()}


def polish_script(draft: dict, kind: str, facts: str, tone: str, model="llama3.2", host=None, temperature=0.4) -> dict:
    prompt = (f"Improve this {kind} in a {tone.lower()} tone. Keep every figure exactly as written. Keep it under 200 words.\n"
              f"FACTS:\n{facts}\n\nDRAFT SUBJECT: {draft['subject']}\nDRAFT BODY:\n{draft['body']}\n\n"
              'Return JSON: {"subject": "...", "body": "..."}')
    return normalize_script(_chat(prompt, model, host, temperature), draft)


def critique_draft(text: str, facts: str, model="llama3.2", host=None, temperature=0.2) -> dict:
    prompt = (f"Review this salary negotiation message written by the candidate.\nFACTS:\n{facts}\n\nMESSAGE:\n{text[:4000]}\n\n"
              'Return JSON: {"strengths": ["..."], "improvements": ["specific and actionable"], "rewrite": "an improved version"}')
    return normalize_critique(_chat(prompt, model, host, temperature))
