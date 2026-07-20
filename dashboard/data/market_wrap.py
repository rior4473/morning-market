"""Three-sentence synopsis of *why* markets moved on the previous trading day.

Two modes:
  * "claude"     — Claude (Opus 4.8) with the web-search server tool actually
                   researches the session and writes the synopsis. Needs
                   ANTHROPIC_API_KEY (or an `ant auth login` profile).
  * "extractive" — keyless fallback. One data-derived sentence plus the two
                   most explanatory market-wrap headlines already in the cache.

The extractive mode means the feature works with zero setup, exactly like the
rest of the dashboard; the Claude mode is the upgrade.
"""
from __future__ import annotations

import os
import re
from datetime import datetime

MODEL = "claude-opus-4-8"

# Headlines that actually explain a session (vs. single-stock noise)
_WRAP_HINTS = [
    "stocks", "wall street", "s&p", "nasdaq", "dow", "market", "shares",
    "rally", "rallied", "slid", "slipped", "jumped", "tumbled", "fell",
    "rose", "close", "closed", "higher", "lower", "yields", "investors",
]
_WHY_HINTS = ["after", "as ", "amid", "following", "on hopes", "on fears",
              "because", "driven by", "spurred", "sparked"]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 25]


def _pct(v) -> str:
    return "n/a" if v is None else f"{v:+.2f}%"


def _data_sentence(sections: dict) -> tuple[str, str | None]:
    """One factual sentence built from the cached prices. Returns (text, as_of)."""
    def row(group, asset):
        for r in sections.get(group, {}).get("rows", []):
            if r.get("asset") == asset:
                return r
        return {}

    sp = row("equity_index", "S&P 500")
    nq = row("equity_index", "Nasdaq Composite")
    as_of = sp.get("as_of")

    bits = []
    if sp.get("pct_change") is not None:
        bits.append(f"the S&P 500 {'rose' if sp['pct_change'] >= 0 else 'fell'} "
                    f"{abs(sp['pct_change']):.2f}%")
    if nq.get("pct_change") is not None:
        bits.append(f"the Nasdaq {'rose' if nq['pct_change'] >= 0 else 'fell'} "
                    f"{abs(nq['pct_change']):.2f}%")

    ten = next((r for r in sections.get("yields", {}).get("rows", [])
                if r.get("maturity") == "10Y"), {})
    if ten.get("change") is not None:
        bp = abs(ten["change"]) * 100
        bits.append(f"the 10-year Treasury yield {'rose' if ten['change'] >= 0 else 'fell'} "
                    f"{bp:.0f} {'bp' if round(bp) == 1 else 'bps'} to {ten['latest']:.2f}%")

    if not bits:
        return ("Market data unavailable for the last session.", as_of)
    joined = bits[0] if len(bits) == 1 else ", ".join(bits[:-1]) + " and " + bits[-1]
    when = f"In the {as_of} session, " if as_of else "In the last session, "
    return (when + joined + ".", as_of)


def _extractive(sections: dict, news: list[dict]) -> dict:
    """Keyless: data sentence + the two most explanatory wrap headlines."""
    data_sentence, as_of = _data_sentence(sections)

    scored = []
    for n in news:
        blob = f"{n.get('title','')} {n.get('summary','')}".lower()
        if not n.get("summary"):
            continue
        score = sum(2 for h in _WRAP_HINTS if h in blob)
        score += sum(3 for h in _WHY_HINTS if h in blob)
        if score >= 6:
            scored.append((score, n))
    scored.sort(key=lambda x: x[0], reverse=True)

    lines, sources = [data_sentence], []
    for _score, n in scored[:2]:
        s = _sentences(n["summary"])
        if not s:
            continue
        lines.append(s[0].rstrip(".") + f" ({n['source']}).")
        sources.append({"title": n["title"], "url": n.get("link", ""),
                        "source": n["source"]})

    while len(lines) < 3:
        lines.append("No single catalyst dominated the session in the "
                     "headlines available.")

    return {"text": " ".join(lines[:3]), "sources": sources,
            "mode": "extractive", "as_of": as_of,
            "generated_at": datetime.now().astimezone().isoformat()}


def _claude(sections: dict, news: list[dict]) -> dict | None:
    """Claude + web search. Returns None if unavailable so caller can fall back."""
    try:
        import anthropic
    except ImportError:
        return None

    data_sentence, as_of = _data_sentence(sections)
    headlines = "\n".join(f"- {n['source']}: {n['title']}" for n in news[:15])

    system = (
        "You are a markets analyst writing a concise morning brief for a "
        "buy-side analyst. Use the web_search tool to research why U.S. "
        "markets moved during the most recent completed trading session. "
        "Then write EXACTLY three sentences explaining WHY securities rose or "
        "fell — name the actual catalysts (data prints, Fed commentary, "
        "earnings, geopolitics, rates, commodities). Be specific and factual; "
        "no hedging, no preamble, no bullet points, no headings. "
        "Output only the three sentences."
    )
    user = (
        f"Today is {datetime.now():%Y-%m-%d}. The most recent session with data "
        f"is {as_of or 'the latest trading day'}.\n\n"
        f"Measured moves: {data_sentence}\n\n"
        f"Headlines already collected:\n{headlines}\n\n"
        "Search the web for that session's market wrap and explain the drivers."
    )

    try:
        client = anthropic.Anthropic()
        messages = [{"role": "user", "content": user}]
        resp = None
        for _ in range(4):  # server tools can return pause_turn
            resp = client.messages.create(
                model=MODEL,
                max_tokens=2000,
                thinking={"type": "adaptive"},
                system=system,
                tools=[{"type": "web_search_20260209", "name": "web_search",
                        "max_uses": 6}],
                messages=messages,
            )
            if resp.stop_reason != "pause_turn":
                break
            messages = [{"role": "user", "content": user},
                        {"role": "assistant", "content": resp.content}]

        if resp is None or resp.stop_reason == "refusal":
            return None

        text = " ".join(b.text.strip() for b in resp.content
                        if b.type == "text" and b.text.strip())
        if not text:
            return None

        sources = []
        for block in resp.content:
            if block.type == "web_search_tool_result":
                results = block.content
                if isinstance(results, list):
                    for r in results:
                        url = getattr(r, "url", None)
                        if url:
                            sources.append({"title": getattr(r, "title", url),
                                            "url": url,
                                            "source": re.sub(r"^www\.", "",
                                                             url.split("/")[2])})
        seen, uniq = set(), []
        for s in sources:
            if s["source"] not in seen:
                seen.add(s["source"])
                uniq.append(s)

        return {"text": text.strip(), "sources": uniq[:5], "mode": "claude",
                "as_of": as_of,
                "generated_at": datetime.now().astimezone().isoformat()}
    except Exception:
        return None


def build_wrap(sections: dict, news: list[dict]) -> dict:
    """Claude-researched synopsis when credentials exist, else extractive."""
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        result = _claude(sections, news)
        if result:
            return result
    return _extractive(sections, news)
