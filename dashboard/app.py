"""
MeetSense — Streamlit Dashboard
Run: streamlit run dashboard/app.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from modules.transcript_cleaner import clean_transcript
from modules.action_extractor import extract_insights
from modules.meeting_scorer import score_meeting

st.set_page_config(page_title="MeetSense", page_icon="🎯", layout="wide")

st.markdown("""
<style>
.grade-A { color: #22c55e; font-size: 3rem; font-weight: bold; }
.grade-B { color: #84cc16; font-size: 3rem; font-weight: bold; }
.grade-C { color: #f59e0b; font-size: 3rem; font-weight: bold; }
.grade-D { color: #f97316; font-size: 3rem; font-weight: bold; }
.grade-F { color: #ef4444; font-size: 3rem; font-weight: bold; }
.risk-high   { color: #ef4444; font-weight: bold; }
.risk-medium { color: #f97316; font-weight: bold; }
.risk-low    { color: #22c55e; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown("## 🎯 MeetSense")
st.markdown("**Bot-Free Meeting Analyzer** — Transcript quality, action items & meeting score | Inspired by Avoma's pain points")
st.divider()

# ── Sample transcripts ────────────────────────────────────────
SAMPLES = {
    "Good meeting (clear actions + decisions)": """John: Good morning everyone. Today we're reviewing the Q3 launch.
Sarah: I think we should finalize vendor selection first.
John: Agreed. We decided to go with Vendor A. Sarah will send the contract by Friday.
Tom: What about client onboarding? Who is handling that?
Sarah: Good question. Tom, can you own that?
Tom: Yes I will handle client onboarding by next week.
John: Perfect. I will send the demo invite today. Meeting adjourned.""",

    "Corrupted transcript (bot dropped mid-call)": """Alice: So as I was saying the budget um uh [inaudible] was already...
[crosstalk] going back to what we discussed...
[Speaker ?]: Right right so like the next steps... [crosstalk]
Bob: Continuing from earlier, the deadline is... [unclear]
Alice: We need to check with... [inaudible]
Bob: Okay so basically... [crosstalk] ...by next week.""",

    "No action items (bad meeting)": """Manager: So how is everyone doing? Good. Okay.
Team: Good.
Manager: Great. So um just wanted to check in. You know how things are going.
Team: Yeah things are fine basically.
Manager: Okay great. See you next week then. Good talk."""
}

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Input")
    mode = st.radio("Choose input", ["Use sample", "Paste your own"])
    if mode == "Use sample":
        choice = st.selectbox("Select sample", list(SAMPLES.keys()))
        transcript_input = SAMPLES[choice]
    else:
        transcript_input = st.text_area(
            "Paste meeting transcript",
            height=250,
            placeholder="John: Let's start...\nSarah: Sure, I'll handle..."
        )
    analyze = st.button("🔍 Analyze Meeting", use_container_width=True, type="primary")

# ── Main analysis ─────────────────────────────────────────────
if analyze and transcript_input.strip():
    with st.spinner("Analyzing transcript..."):
        clean   = clean_transcript(transcript_input)
        extract = extract_insights(clean.cleaned_text)
        score   = score_meeting(clean.cleaned_text, extract.action_items, extract.decisions)

    st.markdown(f"### 📝 Summary\n> {extract.one_line_summary}")
    st.divider()

    # ── Row 1: Quality + Score ────────────────────────────────
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 🧹 Transcript Quality")
        risk_color = {"high": "risk-high", "medium": "risk-medium", "low": "risk-low"}[clean.missing_context_risk]
        st.markdown(f"**Quality Score:** {clean.quality_score}/100")
        st.progress(int(clean.quality_score) / 100)
        st.markdown(f"**Context Risk:** <span class='{risk_color}'>{clean.missing_context_risk.upper()}</span>", unsafe_allow_html=True)
        st.markdown(f"**Words:** {clean.word_count_before} → {clean.word_count_after} (after cleanup)")
        if clean.issues_found:
            st.markdown("**Issues detected:**")
            for issue in clean.issues_found:
                st.warning(f"⚠️ {issue}")
        else:
            st.success("✅ No major issues found")

    with col2:
        st.markdown("#### 🏆 MeetScore")
        grade_class = f"grade-{score.grade}"
        st.markdown(f"<div class='{grade_class}'>{score.grade}</div>", unsafe_allow_html=True)
        st.markdown(f"**Overall: {score.overall}/100** | Est. duration: ~{score.duration_estimate_mins} min")

        fig = go.Figure(go.Bar(
            x=["Clarity", "Efficiency", "Actionability", "Engagement"],
            y=[score.clarity, score.efficiency, score.actionability, score.engagement],
            marker_color=["#6366f1", "#22c55e", "#f59e0b", "#ec4899"],
            text=[f"{v:.0f}" for v in [score.clarity, score.efficiency, score.actionability, score.engagement]],
            textposition="outside"
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f1f5f9", yaxis=dict(range=[0, 110], showgrid=False),
            margin=dict(t=20, b=10), height=220, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Row 2: Actions + Decisions ────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"#### ✅ Action Items ({len(extract.action_items)})")
        if extract.action_items:
            for item in extract.action_items:
                with st.expander(f"📌 {item.get('task', '')[:60]}..."):
                    st.markdown(f"**Owner:** {item.get('owner', 'TBD')}")
                    st.markdown(f"**Deadline:** {item.get('deadline', 'Not specified')}")
        else:
            st.error("❌ No action items found — this meeting had no clear outcomes!")

    with col4:
        st.markdown(f"#### 🗳️ Decisions ({len(extract.decisions)})")
        if extract.decisions:
            for d in extract.decisions:
                st.success(f"✓ {d}")
        else:
            st.warning("No clear decisions recorded")

        st.markdown(f"#### ❓ Open Questions ({len(extract.open_questions)})")
        if extract.open_questions:
            for q in extract.open_questions:
                st.info(f"? {q}")

    st.divider()

    # ── Talk ratio ────────────────────────────────────────────
    if score.talk_ratio:
        st.markdown("#### 🎤 Talk Ratio")
        fig2 = px.pie(
            values=list(score.talk_ratio.values()),
            names=list(score.talk_ratio.keys()),
            hole=0.4
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f1f5f9", margin=dict(t=10, b=10), height=220
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Feedback ──────────────────────────────────────────────
    st.markdown("#### 💡 Improvement Tips")
    for tip in score.feedback:
        st.info(f"💡 {tip}")

    st.divider()

    # ── Follow-up email ───────────────────────────────────────
    st.markdown("#### 📧 Auto-Generated Follow-Up Email")
    st.code(extract.follow_up_email, language="text")
    st.caption(f"Powered by: {extract.source}")

elif not transcript_input.strip() and analyze:
    st.warning("Please paste a transcript or select a sample first!")
else:
    st.info("👈 Select a sample or paste a transcript in the sidebar, then click **Analyze Meeting**")
    st.markdown("""
    **What MeetSense does:**
    - 🧹 Detects corrupted transcripts (bot drops, crosstalk, missing context)
    - ✅ Extracts action items with owners + deadlines
    - 🏆 Scores your meeting on clarity, efficiency, actionability & engagement
    - 📧 Drafts a follow-up email automatically
    
    *No meeting bot needed. Paste any transcript — works offline.*
    """)

st.markdown("---")
st.markdown("<small>MeetSense — Open source project inspired by Avoma's bot reliability challenges. Not affiliated with Avoma. | Made in Pune 🇮🇳</small>", unsafe_allow_html=True)
