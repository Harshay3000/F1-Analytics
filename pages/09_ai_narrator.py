# ============================================================
# pages/09_ai_narrator.py — AI Race Narrator (Groq)
# ============================================================

import streamlit as st
import os
from utils.data_loader import build_race_summary_dict, build_tyre_degradation_model

st.set_page_config(page_title='AI Narrator · F1', layout='wide')

# ── Guards ────────────────────────────────────────────────────
if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

if not st.session_state.get('loaded_race'):
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

session     = st.session_state['session_obj']
laps        = st.session_state['laps_df']
loaded_year = st.session_state['loaded_year']
loaded_race = st.session_state['loaded_race']
event_name  = session.event.get('EventName', loaded_race)

# ── Header ────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='color:white;font-size:1.6rem;font-weight:800;margin-bottom:4px'>
  🤖 AI Race Narrator
</h1>
<p style='color:#555577;margin-bottom:4px'>
  AI reads the race data and writes a human-quality narrative —
  report, strategy breakdown, or Driver of the Day argument.
</p>
<div style='display:inline-block;background:#0f3460;border:1px solid #1e4a80;
            border-radius:6px;padding:5px 14px;margin-bottom:20px;font-size:13px'>
  📍 Analysing: <b style='color:white'>{loaded_year} {event_name}</b>
</div>
""", unsafe_allow_html=True)

# ── Load API key ──────────────────────────────────────────────
def load_api_key():
    # 1. Try .env file
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '.env'
        )
        load_dotenv(env_path)
    except ImportError:
        pass

    # 2. Environment variable (set by .env or Railway secrets)
    key = os.environ.get('GROQ_API_KEY')
    if key:
        return key

    # 3. Streamlit secrets (fallback)
    try:
        key = st.secrets.get('GROQ_API_KEY')
        if key:
            return key
    except Exception:
        pass

    return None

api_key = load_api_key()

if api_key:
    st.success('✅ Groq API key loaded automatically')
else:
    st.markdown("""
    <div style='background:#16213e;border:1px solid #e63946;border-radius:10px;
                padding:16px;margin-bottom:16px'>
      <div style='color:#e63946;font-weight:600;margin-bottom:8px'>🔑 API Key not found</div>
      <div style='color:#aaaacc;font-size:13px;line-height:1.8'>
        Add this line to your <b style='color:white'>.env</b> file in the project root:<br>
        <code style='background:#0f0f1a;padding:4px 8px;border-radius:4px;color:#57c785'>
          GROQ_API_KEY=gsk_your-key-here</code><br><br>
        Get a free key at
        <a href='https://console.groq.com' target='_blank' style='color:#4a90d9'>
          console.groq.com</a> then restart the app.
      </div>
    </div>
    """, unsafe_allow_html=True)
    manual_key = st.text_input(
        'Or paste your Groq API key here (session only)',
        type='password', placeholder='gsk_...',
    )
    if manual_key:
        api_key = manual_key

if not api_key:
    st.stop()

# ── Model selector ────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("#### 🤖 Groq Model")
    groq_model = st.selectbox(
        'Model',
        options = [
            'openai/gpt-oss-120b',
            'openai/gpt-oss-20b',
            'qwen/qwen3.6-27b',
        ],
        index = 0,
        help  = (
            'gpt-oss-120b — best quality, recommended\n'
            'gpt-oss-20b  — faster, higher rate limits\n'
            'qwen3.6-27b  — good alternative'
        ),
    )
    st.markdown("""
    <div style='background:#16213e;border:1px solid #1e1e3a;border-radius:8px;
                padding:10px;font-size:11px;color:#555577;margin-top:8px'>
      Free tier limits (approx):<br>
      • 30 requests / minute<br>
      • 6,000 tokens / minute<br>
      • 500,000 tokens / day
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Build race summary ────────────────────────────────────────
with st.spinner('Extracting race data...'):
    try:
        deg_result = build_tyre_degradation_model(laps, session)
    except Exception:
        deg_result = None
    try:
        race_summary = build_race_summary_dict(laps, session, deg_result)
    except Exception as e:
        st.error(f'Could not extract race data: {e}')
        st.stop()

with st.expander('📊  Race data sent to AI (click to inspect)'):
    st.json(race_summary)

st.divider()

# ── Controls ──────────────────────────────────────────────────
st.markdown("#### ✍️ Generate narrative")
col1, col2 = st.columns([2, 1])

with col1:
    narrative_type = st.selectbox('Narrative style', [
        'Race Report',
        'Strategy Analysis',
        'Driver of the Day',
        'Custom Question',
    ])
with col2:
    tone = st.selectbox('Tone', ['Journalist', 'Technical', 'Enthusiast'])

custom_question = ''
if narrative_type == 'Custom Question':
    custom_question = st.text_area(
        'Your question',
        placeholder='e.g. "Why did Verstappen pit early?" or "Who managed tyres best?"',
        height=80,
    )

# ── Prompt builder ────────────────────────────────────────────
def build_prompt(summary, style, tone, custom_q=''):
    tone_map = {
        'Journalist' : 'Write like an F1 journalist for a quality sports publication. Clear, engaging prose. Use correct F1 terminology.',
        'Technical'  : 'Write like an F1 race engineer. Focus on numbers, lap time deltas, tyre degradation rates, and strategic decisions.',
        'Enthusiast' : 'Write like a passionate F1 fan with deep knowledge. Enthusiastic, opinionated, and engaging.',
    }
    results_text = '\n'.join([
        f"  P{r['position']}: {r['name']} ({r['team']})"
        for r in summary.get('results', [])
    ])
    strat_text = '\n'.join([
        f"  {s['driver']} {s['name']}: {s['strategy']} (P{s['finish']})"
        for s in summary.get('tyre_strategies', [])[:10]
    ])
    lead_text = '\n'.join([
        f"  Lap {lc['lap']}: {lc['name']} takes lead"
        for lc in summary.get('lead_changes', [])
    ]) or '  No lead changes recorded'
    fl      = summary.get('fastest_lap', {})
    fl_str  = f"{fl.get('name','?')} — {fl.get('time','?')} on lap {fl.get('lap','?')}"
    deg_str = ', '.join([f"{c}: {r}ms/lap" for c, r in
                         summary.get('deg_rates', {}).items()]) or 'N/A'
    gained  = ', '.join([f"{g['name']} (+{g['gained']} places)"
                         for g in summary.get('positions_gained', [])[:3]]) or 'N/A'

    race_block = f"""
RACE: {summary.get('event_name','')} {summary.get('year','')}
CIRCUIT: {summary.get('location','')}
TOTAL LAPS: {summary.get('total_laps','?')}
TOP 10: {results_text}
FASTEST LAP: {fl_str}
LEAD CHANGES: {lead_text}
TYRE STRATEGIES: {strat_text}
DEGRADATION RATES: {deg_str}
POSITION GAINERS: {gained}
"""
    task_map = {
        'Race Report': (
            "Write a race report of 450-550 words covering:\n"
            "- Opening: result and headline story\n"
            "- How the race unfolded (key moments)\n"
            "- The decisive strategic moment\n"
            "- Notable performances beyond the podium\n"
            "- Closing: championship implications\n"
            "Write in flowing paragraphs, no bullet points."
        ),
        'Strategy Analysis': (
            "Write a technical strategy analysis of 400-500 words:\n"
            "- Starting compound choices\n"
            "- Key pit windows and who got them right\n"
            "- Undercut or overcut attempts\n"
            "- How degradation rates influenced calls\n"
            "- Best and worst strategy with lap references\n"
            "Write in paragraphs."
        ),
        'Driver of the Day': (
            "Write a 350-450 word Driver of the Day argument:\n"
            "- Name your choice in the opening sentence\n"
            "- Argument using data (pace, positions gained, tyre mgmt)\n"
            "- Acknowledge the strongest counter-argument\n"
            "- Conclude why your choice stands\n"
            "Reference actual lap numbers."
        ),
        'Custom Question': (
            f'Answer this question in 200-350 words:\n\n"{custom_q}"\n\n'
            "Be specific and reference the race data. Say so if data is insufficient."
        ),
    }
    return (
        f"You are an expert Formula 1 analyst and writer.\n"
        f"{tone_map.get(tone,'')}\n\n"
        f"Race data:\n{race_block}\n\n"
        f"Task:\n{task_map.get(style, task_map['Race Report'])}\n\n"
        f"Only use facts from the data. Do not invent events not in the data."
    )

# ── Generate ──────────────────────────────────────────────────
gen_disabled = (narrative_type == 'Custom Question'
                and not custom_question.strip())

if st.button('🚀  Generate', type='primary',
             use_container_width=True, disabled=gen_disabled):
    prompt = build_prompt(race_summary, narrative_type, tone, custom_question)
    try:
        from groq import Groq
        client    = Groq(api_key=api_key)
        box       = st.empty()
        full_text = ''

        with client.chat.completions.create(
            model       = groq_model,
            messages    = [{'role': 'user', 'content': prompt}],
            max_tokens  = 1024,
            temperature = 0.7,
            stream      = True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ''
                full_text += delta
                box.markdown(f"""
<div style='background:#16213e;border:1px solid #1e1e3a;border-radius:12px;
            padding:28px;line-height:1.9;color:#ddddee;font-size:15px'>
{full_text}▌</div>""", unsafe_allow_html=True)

        box.markdown(f"""
<div style='background:#16213e;border:1px solid #1e1e3a;border-radius:12px;
            padding:28px;line-height:1.9;color:#ddddee;font-size:15px'>
{full_text}</div>""", unsafe_allow_html=True)

        st.session_state['last_narrative']       = full_text
        st.session_state['last_narrative_type']  = narrative_type
        st.session_state['last_narrative_model'] = groq_model

        st.markdown("<br>", unsafe_allow_html=True)
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button('⬇️  Download narrative', full_text,
                f'f1_{loaded_year}_{loaded_race}_{narrative_type}.txt',
                'text/plain')
        with dl2:
            st.download_button('📋  Download prompt', prompt,
                'prompt.txt', 'text/plain')

    except ImportError:
        st.error('Run: `pip install groq`')
    except Exception as e:
        err = str(e)
        if 'auth' in err.lower() or '401' in err:
            st.error('❌ Invalid API key. Check your .env file.')
        elif 'rate' in err.lower() or '429' in err:
            st.error('⏳ Rate limited — wait 30s and retry, or switch to gpt-oss-20b.')
        elif 'decommissioned' in err.lower() or 'deprecated' in err.lower():
            st.error('⚠️ This model has been deprecated. Switch to gpt-oss-120b in the sidebar.')
        else:
            st.error(f'Error: {err}')

elif st.session_state.get('last_narrative'):
    st.markdown(f"""
<p style='color:#555577;font-size:12px;margin-bottom:12px'>
  Last: {st.session_state.get('last_narrative_type','')} ·
  {st.session_state.get('last_narrative_model','')} —
  click Generate for a new one.
</p>
<div style='background:#16213e;border:1px solid #1e1e3a;border-radius:12px;
            padding:28px;line-height:1.9;color:#ddddee;font-size:15px'>
{st.session_state['last_narrative']}
</div>""", unsafe_allow_html=True)

st.divider()

with st.expander('🤖  How the AI narrator works'):
    st.markdown("""
    **Pipeline:** Race data extracted → injected into structured prompt →
    sent to GPT-OSS 120B via Groq → streams back live token by token.

    **Models available:**
    - `openai/gpt-oss-120b` — best quality, Groq's recommended flagship (replaces llama-3.3-70b)
    - `openai/gpt-oss-20b` — faster with higher rate limits (replaces llama-3.1-8b)
    - `qwen/qwen3.6-27b` — good alternative with vision support

    **API key loading order:**
    1. `.env` file in project root
    2. Shell / Railway environment variable
    3. Streamlit secrets
    4. Manual paste fallback

    **Resume talking point:**
    *"Integrated GPT-OSS 120B via Groq API to auto-generate natural language
    race summaries from structured telemetry data using prompt engineering
    to control narrative style, tone, and factual grounding."*
    """)
