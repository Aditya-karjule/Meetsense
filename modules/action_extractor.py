"""
MeetSense — Action Item Extractor
Uses Claude API to extract from meeting transcripts:
- Action items with owner + deadline
- Key decisions made
- Open questions / blockers
- Follow-up email draft
Falls back to rule-based extraction if no API key.
"""

import os
import json
import re
from dataclasses import dataclass, field


@dataclass
class MeetingInsights:
    action_items: list       # [{"task": ..., "owner": ..., "deadline": ...}]
    decisions: list          # list of strings
    open_questions: list     # list of strings
    follow_up_email: str
    one_line_summary: str
    source: str              # "claude-api" or "rule-based"


SYSTEM_PROMPT = """You are an expert meeting analyst. Given a meeting transcript, extract structured insights.
Return ONLY a valid JSON object with these keys:
- action_items: list of objects with "task", "owner" (person name or "Team"), "deadline" (e.g. "by Friday", "next week", or "not specified")
- decisions: list of key decisions made in the meeting (strings)
- open_questions: list of unresolved questions or blockers (strings)
- follow_up_email: a short professional follow-up email (subject + body, plain text)
- one_line_summary: one sentence capturing the entire meeting purpose and outcome

Return ONLY valid JSON. No markdown, no explanation, no backticks."""


def extract_insights(transcript: str) -> MeetingInsights:
    """
    Extract action items, decisions, and follow-up email from transcript.
    Uses Claude API if available, else falls back to rule-based.
    """
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return _extract_with_claude(transcript, api_key)
    except ImportError:
        pass
    return _extract_rule_based(transcript)


def _extract_with_claude(transcript: str, api_key: str) -> MeetingInsights:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Meeting transcript:\n\n{transcript}"}]
    )
    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    return MeetingInsights(
        action_items=data.get("action_items", []),
        decisions=data.get("decisions", []),
        open_questions=data.get("open_questions", []),
        follow_up_email=data.get("follow_up_email", ""),
        one_line_summary=data.get("one_line_summary", ""),
        source="claude-api"
    )


def _extract_rule_based(transcript: str) -> MeetingInsights:
    """Rule-based fallback — no API needed."""
    text_lower = transcript.lower()
    sentences = [s.strip() for s in re.split(r'[.!?]', transcript) if s.strip()]

    # Action items — sentences with task signals
    action_signals = ['will', 'should', 'need to', 'action', 'follow up',
                      'by friday', 'next week', 'tomorrow', 'send', 'share', 'complete', 'finish']
    action_items = []
    for s in sentences:
        s_lower = s.lower()
        if any(sig in s_lower for sig in action_signals) and len(s.split()) > 4:
            # Try to find owner (capitalized name)
            words = s.split()
            owner = next((w for w in words if w[0].isupper() and len(w) > 2
                         and w not in ['I', 'The', 'We', 'This', 'That', 'In']), "Team")
            deadline = "not specified"
            for dl in ['by friday', 'next week', 'tomorrow', 'by monday', 'end of week']:
                if dl in s_lower:
                    deadline = dl.title()
                    break
            action_items.append({"task": s.strip(), "owner": owner, "deadline": deadline})

    # Decisions
    decision_signals = ['decided', 'agreed', 'confirmed', 'approved', 'will go with',
                        'we chose', 'final decision', 'moving forward with']
    decisions = [s.strip() for s in sentences
                 if any(sig in s.lower() for sig in decision_signals) and len(s.split()) > 4]

    # Open questions
    question_signals = ['?', 'unclear', 'not sure', 'need to check', "don't know",
                        'pending', 'TBD', 'to be confirmed', 'open question']
    open_questions = []
    for s in sentences:
        if ('?' in s or any(sig in s.lower() for sig in question_signals)) and len(s.split()) > 3:
            open_questions.append(s.strip())

    # Simple summary
    if action_items:
        summary = f"Meeting covered {len(action_items)} action items and {len(decisions)} decisions."
    else:
        summary = "Meeting transcript analyzed — no clear action items detected."

    # Follow-up email
    email = _build_email(action_items, decisions, open_questions)

    return MeetingInsights(
        action_items=action_items[:5],
        decisions=decisions[:4],
        open_questions=open_questions[:3],
        follow_up_email=email,
        one_line_summary=summary,
        source="rule-based"
    )


def _build_email(actions: list, decisions: list, questions: list) -> str:
    lines = ["Subject: Meeting Follow-Up — Action Items & Next Steps", "",
             "Hi team,", "",
             "Thank you for the meeting. Here's a quick summary:"]
    if decisions:
        lines += ["", "Key Decisions:"] + [f"  • {d}" for d in decisions[:3]]
    if actions:
        lines += ["", "Action Items:"] + [f"  • {a['task']} — {a['owner']} ({a['deadline']})"
                                           for a in actions[:4]]
    if questions:
        lines += ["", "Open Questions:"] + [f"  • {q}" for q in questions[:2]]
    lines += ["", "Please let me know if anything is missing.", "", "Best,", "[Your Name]"]
    return "\n".join(lines)


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    sample = """
    John: Good morning. Let's review Q3. Sarah will finalize the budget report by Friday.
    Sarah: Agreed. We decided to go with vendor A for the new software. 
    John: Tom needs to send the contract by next week. 
    Tom: Sure. One open question — who is handling client onboarding? Not sure yet.
    Sarah: We need to check with the manager. TBD on that.
    John: Okay. Moving forward with the launch plan then. Meeting done.
    """

    print("=" * 55)
    print("MeetSense — Action Extractor Test")
    print("=" * 55)
    result = extract_insights(sample)
    print(f"\nSummary : {result.one_line_summary}")
    print(f"Source  : {result.source}")
    print(f"\nActions ({len(result.action_items)}):")
    for a in result.action_items:
        print(f"  • {a['task']} | Owner: {a['owner']} | {a['deadline']}")
    print(f"\nDecisions ({len(result.decisions)}):")
    for d in result.decisions:
        print(f"  • {d}")
    print(f"\nOpen Questions ({len(result.open_questions)}):")
    for q in result.open_questions:
        print(f"  • {q}")
    print(f"\nFollow-up Email:\n{result.follow_up_email}")
