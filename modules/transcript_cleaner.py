"""
MeetSense — Transcript Cleaner
Fixes messy/corrupted transcripts:
- Removes filler words
- Fixes speaker label gaps
- Detects missing context (late join simulation)
- Normalizes crosstalk sections
"""

import re
from dataclasses import dataclass, field


@dataclass
class CleanResult:
    original_text: str
    cleaned_text: str
    issues_found: list
    quality_score: float      # 0-100
    word_count_before: int
    word_count_after: int
    missing_context_risk: str  # low / medium / high


FILLER_WORDS = [
    r'\bum+\b', r'\buh+\b', r'\ber+\b', r'\blike\b(?=\s+\blike\b)',
    r'\byou know\b', r'\bI mean\b', r'\bbasically\b', r'\bactually\b(?=\s+\bactually\b)',
    r'\bso so\b', r'\bright right\b', r'\bokay okay\b'
]

CROSSTALK_MARKERS = ['[crosstalk]', '[inaudible]', '[overlap]', '...', '[unclear]']

MISSING_CONTEXT_SIGNALS = [
    'as I was saying', 'as mentioned earlier', 'going back to',
    'like I said', 'continuing from', 'to summarize what we discussed'
]


def detect_issues(text: str) -> list:
    """Detect quality issues in a transcript."""
    issues = []
    text_lower = text.lower()

    crosstalk_count = sum(text_lower.count(m.lower()) for m in CROSSTALK_MARKERS)
    if crosstalk_count > 2:
        issues.append(f"High crosstalk detected ({crosstalk_count} instances) — accuracy may be 60-80%")

    speaker_gaps = len(re.findall(r'\[Speaker \?+\]|\[Unknown\]', text, re.IGNORECASE))
    if speaker_gaps > 0:
        issues.append(f"Unidentified speakers: {speaker_gaps} instances")

    filler_count = sum(len(re.findall(p, text_lower)) for p in FILLER_WORDS)
    if filler_count > 5:
        issues.append(f"Excessive filler words: {filler_count} found")

    context_signals = [s for s in MISSING_CONTEXT_SIGNALS if s in text_lower]
    if context_signals:
        issues.append(f"Possible missing context — references to earlier discussion: {context_signals}")

    sentences = [s.strip() for s in text.split('.') if s.strip()]
    incomplete = [s for s in sentences if len(s.split()) < 3 and s]
    if len(incomplete) > 3:
        issues.append(f"Fragmented sentences detected: {len(incomplete)} — possible mid-call drop")

    return issues


def clean_transcript(text: str, remove_fillers: bool = True) -> CleanResult:
    """
    Clean and analyze a meeting transcript.

    Args:
        text           : Raw transcript text
        remove_fillers : Whether to strip filler words

    Returns:
        CleanResult with cleaned text + quality analysis
    """
    issues = detect_issues(text)
    original_words = len(text.split())
    cleaned = text

    if remove_fillers:
        for pattern in FILLER_WORDS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r'\[crosstalk\]|\[inaudible\]|\[unclear\]', '[unclear segment]',
                     cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'\.{2,}', '...', cleaned)
    cleaned = cleaned.strip()

    cleaned_words = len(cleaned.split())

    # Quality score
    deductions = len(issues) * 10
    quality = max(10, 100 - deductions)

    # Missing context risk
    context_issues = [i for i in issues if 'missing context' in i or 'earlier' in i]
    frag_issues    = [i for i in issues if 'Fragmented' in i]
    if context_issues or len(issues) >= 3:
        risk = 'high'
    elif frag_issues or len(issues) == 2:
        risk = 'medium'
    else:
        risk = 'low'

    return CleanResult(
        original_text=text,
        cleaned_text=cleaned,
        issues_found=issues,
        quality_score=round(quality, 1),
        word_count_before=original_words,
        word_count_after=cleaned_words,
        missing_context_risk=risk
    )


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    samples = [
        {
            "label": "Clean transcript",
            "text": "John: Good morning everyone. Let's start with Q3 results. Sarah: Yes, revenue was up 15%. John: Great. Next steps are to finalize the report by Friday."
        },
        {
            "label": "Corrupted transcript (late join + crosstalk)",
            "text": "...[crosstalk]... as I was saying the budget um uh [inaudible] was already approved. [Speaker ?]: Right right so like the next steps... [crosstalk] ...going back to what we discussed, the deadline is... [unclear]"
        },
        {
            "label": "Mid-call drop simulation",
            "text": "Alice: The proposal looks. Bob: Yes and. Alice: So we should. [inaudible]. Bob: Continuing from earlier discussion, the client wants."
        }
    ]

    print("=" * 55)
    print("MeetSense — Transcript Cleaner Test")
    print("=" * 55)
    for s in samples:
        result = clean_transcript(s["text"])
        print(f"\n[{s['label']}]")
        print(f"Quality Score : {result.quality_score}/100")
        print(f"Context Risk  : {result.missing_context_risk.upper()}")
        print(f"Issues        : {result.issues_found}")
        print(f"Words before  : {result.word_count_before} → after: {result.word_count_after}")
