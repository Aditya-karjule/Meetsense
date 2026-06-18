"""
MeetSense — Meeting Scorer
Scores a meeting on:
- Clarity (were decisions made?)
- Efficiency (talk ratio, filler words)
- Actionability (action items with owners)
- Engagement (questions asked, participation)
Gives an overall MeetScore out of 100.
"""

import re
from dataclasses import dataclass


@dataclass
class MeetScore:
    overall: float           # 0-100
    clarity: float
    efficiency: float
    actionability: float
    engagement: float
    grade: str               # A / B / C / D / F
    feedback: list           # list of improvement tips
    talk_ratio: dict         # {"Speaker": percentage}
    duration_estimate_mins: int


def score_meeting(transcript: str, action_items: list, decisions: list) -> MeetScore:
    """
    Score a meeting transcript on 4 dimensions.

    Args:
        transcript   : Raw or cleaned transcript text
        action_items : List of extracted action items (from action_extractor)
        decisions    : List of decisions made
    Returns:
        MeetScore with breakdown + tips
    """
    text_lower = transcript.lower()
    words = transcript.split()
    sentences = [s.strip() for s in re.split(r'[.!?]', transcript) if s.strip()]

    # ── Clarity (decisions made, clear outcomes) ─────────────
    clarity = min(100, len(decisions) * 20 + (20 if decisions else 0))
    if not decisions:
        clarity = 20

    # ── Efficiency (filler words ratio, meeting length) ───────
    filler_patterns = [r'\bum+\b', r'\buh+\b', r'\blike\b', r'\byou know\b', r'\bbasically\b']
    filler_count = sum(len(re.findall(p, text_lower)) for p in filler_patterns)
    filler_ratio = filler_count / max(len(words), 1)
    efficiency = max(20, 100 - int(filler_ratio * 500))

    # ── Actionability (action items with clear owners) ─────────
    items_with_owner = [a for a in action_items if a.get('owner') not in ['Team', '', None]]
    items_with_deadline = [a for a in action_items if a.get('deadline', 'not specified') != 'not specified']
    actionability = min(100,
        len(action_items) * 15 +
        len(items_with_owner) * 10 +
        len(items_with_deadline) * 10
    )
    if not action_items:
        actionability = 10

    # ── Engagement (questions, multiple speakers) ─────────────
    question_count = transcript.count('?')
    speaker_pattern = re.findall(r'^([A-Z][a-z]+):', transcript, re.MULTILINE)
    unique_speakers = len(set(speaker_pattern))
    engagement = min(100, question_count * 8 + unique_speakers * 15)
    if unique_speakers < 2:
        engagement = max(10, engagement - 30)

    # ── Overall ───────────────────────────────────────────────
    overall = round((clarity * 0.3 + efficiency * 0.2 + actionability * 0.35 + engagement * 0.15), 1)

    # ── Grade ─────────────────────────────────────────────────
    if overall >= 85:
        grade = 'A'
    elif overall >= 70:
        grade = 'B'
    elif overall >= 55:
        grade = 'C'
    elif overall >= 40:
        grade = 'D'
    else:
        grade = 'F'

    # ── Feedback tips ─────────────────────────────────────────
    feedback = []
    if clarity < 50:
        feedback.append("No clear decisions recorded — end meetings with explicit decision log")
    if efficiency < 50:
        feedback.append(f"High filler word usage ({filler_count} instances) — consider structured agenda")
    if actionability < 40:
        feedback.append("Action items lack owners or deadlines — use RACI format")
    if engagement < 40:
        feedback.append("Low participation — try round-robin check-ins or direct questions")
    if unique_speakers == 1:
        feedback.append("Only one speaker detected — was this a solo monologue meeting?")
    if not feedback:
        feedback.append("Great meeting! Clear structure, decisions, and accountable action items.")

    # ── Talk ratio ────────────────────────────────────────────
    speaker_lines = {}
    for match in re.finditer(r'^([A-Z][a-z]+):\s*(.+)', transcript, re.MULTILINE):
        name, line = match.group(1), match.group(2)
        speaker_lines[name] = speaker_lines.get(name, 0) + len(line.split())

    total_spoken = sum(speaker_lines.values()) or 1
    talk_ratio = {k: round(v / total_spoken * 100, 1) for k, v in speaker_lines.items()}

    # ── Duration estimate (avg meeting: 130 wpm) ──────────────
    duration = max(1, round(len(words) / 130))

    return MeetScore(
        overall=overall,
        clarity=round(clarity, 1),
        efficiency=round(efficiency, 1),
        actionability=round(actionability, 1),
        engagement=round(engagement, 1),
        grade=grade,
        feedback=feedback,
        talk_ratio=talk_ratio,
        duration_estimate_mins=duration
    )


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    sample_transcript = """
    John: Good morning everyone. Today we're reviewing the Q3 launch plan.
    Sarah: I think we should finalize vendor selection first.
    John: Agreed. We decided to go with Vendor A. Sarah will send the contract by Friday.
    Tom: What about client onboarding? Who is handling that?
    Sarah: Good question. Tom, can you own that?
    Tom: Yes I will handle client onboarding by next week.
    John: Perfect. So um basically the next step is uh the product demo on Thursday.
    Sarah: Should we invite the client team as well?
    John: Yes, let's do that. I will send the invite today.
    """

    sample_actions = [
        {"task": "Send the contract", "owner": "Sarah", "deadline": "by Friday"},
        {"task": "Handle client onboarding", "owner": "Tom", "deadline": "next week"},
        {"task": "Send demo invite", "owner": "John", "deadline": "today"},
    ]
    sample_decisions = ["Go with Vendor A", "Client team invited to demo"]

    score = score_meeting(sample_transcript, sample_actions, sample_decisions)

    print("=" * 55)
    print("MeetSense — Meeting Scorer Test")
    print("=" * 55)
    print(f"\nOverall Score : {score.overall}/100 (Grade: {score.grade})")
    print(f"Clarity       : {score.clarity}/100")
    print(f"Efficiency    : {score.efficiency}/100")
    print(f"Actionability : {score.actionability}/100")
    print(f"Engagement    : {score.engagement}/100")
    print(f"Duration Est. : ~{score.duration_estimate_mins} mins")
    print(f"\nTalk Ratio    : {score.talk_ratio}")
    print(f"\nFeedback:")
    for tip in score.feedback:
        print(f"  • {tip}")
