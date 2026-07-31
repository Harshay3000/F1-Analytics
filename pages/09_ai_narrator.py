#09_ai_narrator.py — AI Race Narrator (Groq)
import streamlit as st
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

# ── API key ───────────────────────────────────────────────────
st.markdown("#### 🔑 Groq API Key")

api_key = None
try:
    api_key = st.secrets.get('GROQ_API_KEY', None)
except Exception:
    pass

if api_key:
    st.success('Groq API key loaded from Streamlit secrets ✓')
else:
    with st.expander('How to get a free Groq API key', expanded=True):
        st.markdown("""
**Step 1** — Go to [console.groq.com](https://console.groq.com) and sign up (free)

**Step 2** — Go to **API Keys** → **Create API Key** → copy it

**Step 3 — Local setup:** Create `.streamlit/secrets.toml` in your project folder:
```toml
GROQ_API_KEY = "gsk_your-key-here"
```

**Step 4 — Streamlit Cloud:** App Settings → Secrets → paste the same line

**Or paste directly below** (not saved anywhere):
        """)
    api_key_input = st.text_input(
        'Groq API Key',
        type        = 'password',
        placeholder = 'gsk_...',
        help        = 'Your key is only used for this session and never stored.',
    )
    if api_key_input:
        api_key = api_key_input

if not api_key:
    st.info('Enter your Groq API key above to enable the narrator.')
    st.stop()

# ── Model selector ────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("#### 🤖 Groq Model")
    groq_model = st.selectbox(
        'Model',
        options = [
            'llama-3.3-70b-versatile',
            'llama-3.1-8b-instant',
            'mixtral-8x7b-32768',
            'gemma2-9b-it',
        ],
        index = 0,
        help  = (
            'llama-3.3-70b — best quality, generous limits\n'
            'llama-3.1-8b  — fastest, highest rate limits\n'
            'mixtral-8x7b  — good balance\n'
            'gemma2-9b     — alternative option'
        ),
    )
    st.markdown(f"""
    <div style='background:#16213e;border:1px solid #1e1e3a;
                border-radius:8px;padding:10px;font-size:11px;
                color:#555577;margin-top:8px'>
      Free tier limits (approx):<br>
      • 30 requests/minute<br>
      • 6,000 tokens/minute<br>
      • 500,000 tokens/day
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

# ── Narrative controls ────────────────────────────────────────
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
        'Your question about this race',
        placeholder = (
            'e.g. "Why did Verstappen pit early?" '
            'or "Who had the best tyre management?"'
        ),
        height = 80,
    )

# ── Prompt builder ────────────────────────────────────────────
def build_prompt(summary, style, tone, custom_q=''):
    tone_map = {
        'Journalist' : 'Write like an F1 journalist for a quality sports publication. Clear, engaging prose for a general sports audience. Use correct F1 terminology.',
        'Technical'  : 'Write like an F1 race engineer. Focus on numbers, lap time deltas, tyre degradation rates, and strategic decision points. Audience understands F1 deeply.',
        'Enthusiast' : 'Write like a passionate F1 fan with deep knowledge. Enthusiastic, opinionated, and engaging. Celebrate great drives and critique strategic mistakes.',
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

TOP 10 RESULTS:
{results_text}

FASTEST LAP: {fl_str}

LEAD CHANGES:
{lead_text}

TYRE STRATEGIES (top 10):
{strat_text}

TYRE DEGRADATION RATES: {deg_str}
BIGGEST POSITION GAINERS: {gained}
"""

    task_map = {
        'Race Report': (
            "Write a race report of 450-550 words covering:\n"
            "- Opening: the result and headline story\n"
            "- How the race unfolded (key moments only)\n"
            "- The decisive strategic moment\n"
            "- Notable performances beyond the podium\n"
            "- Closing: championship or storyline implications\n"
            "Write in flowing paragraphs, no bullet points."
        ),
        'Strategy Analysis': (
            "Write a technical strategy analysis of 400-500 words:\n"
            "- Starting compound choices and why\n"
            "- Key pit windows and who got them right\n"
            "- Any undercut or overcut attempts\n"
            "- How degradation rates influenced calls\n"
            "- Best and worst strategy team with lap references\n"
            "Use specific lap numbers. Write in paragraphs."
        ),
        'Driver of the Day': (
            "Write a 350-450 word analytical Driver of the Day argument:\n"
            "- Name your choice in the opening sentence\n"
            "- Structured argument using the data (pace, positions gained, tyre mgmt)\n"
            "- Acknowledge the strongest counter-argument\n"
            "- Conclude why your choice stands\n"
            "Reference actual lap numbers and positions."
        ),
        'Custom Question': (
            f"Answer this question about the race in 200-350 words:\n\n"
            f'"{custom_q}"\n\n'
            "Be specific and reference the race data. "
            "If data is insufficient, say so clearly."
        ),
    }

    return f"""You are an expert Formula 1 analyst and writer.
{tone_map.get(tone, '')}

Here is the structured race data:
{race_block}

Your task:
{task_map.get(style, task_map['Race Report'])}

Only use facts from the data above. Do not invent lap times, positions,
or events not present in the data. If something is unclear, acknowledge it.
"""

# ── Generate ──────────────────────────────────────────────────
gen_disabled = (narrative_type == 'Custom Question'
                and not custom_question.strip())

if st.button('🚀  Generate', type='primary',
             use_container_width=True, disabled=gen_disabled):

    if narrative_type == 'Custom Question' and not custom_question.strip():
        st.warning('Please enter a question first.')
    else:
        prompt = build_prompt(race_summary, narrative_type,
                              tone, custom_question)
        try:
            from groq import Groq
            client    = Groq(api_key=api_key)
            box       = st.empty()
            full_text = ''

            # Stream response word by word
            with client.chat.completions.create(
                model    = groq_model,
                messages = [{'role': 'user', 'content': prompt}],
                max_tokens  = 1024,
                temperature = 0.7,
                stream      = True,
            ) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ''
                    full_text += delta
                    box.markdown(f"""
<div style='background:#16213e;border:1px solid #1e1e3a;
            border-radius:12px;padding:28px;line-height:1.9;
            color:#ddddee;font-size:15px'>{full_text}▌</div>
""", unsafe_allow_html=True)

            # Final render without blinking cursor
            box.markdown(f"""
<div style='background:#16213e;border:1px solid #1e1e3a;
            border-radius:12px;padding:28px;line-height:1.9;
            color:#ddddee;font-size:15px'>{full_text}</div>
""", unsafe_allow_html=True)

            # Persist across reruns
            st.session_state['last_narrative']      = full_text
            st.session_state['last_narrative_type'] = narrative_type
            st.session_state['last_narrative_model']= groq_model

            # Download
            st.markdown("<br>", unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    '⬇️  Download narrative', full_text,
                    f'f1_{loaded_year}_{loaded_race}_{narrative_type}.txt',
                    'text/plain',
                )
            with dl2:
                st.download_button(
                    '📋  Download prompt', prompt,
                    'prompt.txt', 'text/plain',
                )

        except ImportError:
            st.error('Run: `pip install groq`')
        except Exception as e:
            err = str(e)
            if 'auth' in err.lower() or 'api_key' in err.lower() or '401' in err:
                st.error('❌ Invalid API key. Get one free at [console.groq.com](https://console.groq.com)')
            elif 'rate' in err.lower() or '429' in err:
                st.error('⏳ Rate limited — wait 30 seconds and try again, or switch to llama-3.1-8b-instant in the sidebar.')
            elif 'model' in err.lower():
                st.error(f'Model error — try a different model in the sidebar. Details: {err}')
            else:
                st.error(f'Error: {err}')

# Show previous if page reruns
elif st.session_state.get('last_narrative'):
    model_used = st.session_state.get('last_narrative_model', '')
    st.markdown(f"""
<p style='color:#555577;font-size:12px;margin-bottom:12px'>
  Last generated: {st.session_state.get('last_narrative_type','')}
  {f'· Model: {model_used}' if model_used else ''}
  — click Generate to create a new one.
</p>
<div style='background:#16213e;border:1px solid #1e1e3a;border-radius:12px;
            padding:28px;line-height:1.9;color:#ddddee;font-size:15px'>
{st.session_state['last_narrative']}
</div>""", unsafe_allow_html=True)

st.divider()

with st.expander('🤖  How the AI narrator works'):
    st.markdown("""
    #### Pipeline

    **Step 1 — Data extraction**
    Structured facts are pulled from the race: top 10 results, pit stop
    laps and compounds, lead changes, fastest lap, positions gained,
    and tyre degradation rates from the ML model on Page 7.

    **Step 2 — Prompt engineering**
    Facts are injected into a structured prompt specifying narrative
    style, tone, word count, and constraints (don't invent facts).

    **Step 3 — Groq API call**
    Sent to the selected Llama/Mixtral model via Groq's API.
    Response streams back token by token — you see it appear live.

    **Step 4 — Display & download**
    Rendered in a styled card. Persists in session state across
    page navigation. Downloadable as a text file.

    #### Why Groq?

    | | Groq | OpenAI |
    |---|---|---|
    | Free tier | ✅ Yes | ❌ No |
    | Speed | ⚡ Very fast (LPU) | Normal |
    | Rate limits | 30 req/min | Pay-per-use |
    | Models | Llama 3, Mixtral | GPT-4, GPT-3.5 |

    #### Resume talking point
    *"Integrated Groq's LLM API to auto-generate natural language race
    summaries from structured telemetry data, using prompt engineering
    to control narrative style, tone, and factual grounding."*
    """)
