# ============================
# 📌 TIMELINE GENERATOR (Vertex AI - Gemini 2.0 Flash)
# ============================

import os, re, json, time, datetime, random, csv
from tqdm.notebook import tqdm
from vertexai import init
from vertexai.generative_models import GenerativeModel

# ============================
# ⚙️ CONFIG
# ============================
PROJECT_ID = "instr-cs795-fall25-hqin-1"   # ← TU PROYECTO
LOCATION   = "us-central1"
MODEL_NAME = "gemini-2.0-flash"
COLLECTION = "mozambique"  # cambia entre drc, burundi, sudan, mozambique

DATA_PATH   = f"./data/collections/{COLLECTION}_articles_formatted.txt"
PROMPT_PATH = "./prompt/prompt-timeline.txt"

OUT_TXT  = f"./output/timelines/{COLLECTION}/{MODEL_NAME}/{COLLECTION}_timeline_raw.txt"
OUT_JSON = f"./output/timelines/{COLLECTION}/{MODEL_NAME}/{COLLECTION}_timeline.json"

# ============================
# 🚀 INIT MODEL
# ============================
init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel(MODEL_NAME)

# ============================
# 📌 LOAD PROMPT
# ============================
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    BASE_PROMPT = f.read()

def build_prompt(text, pub_date):
    return (BASE_PROMPT
            .replace("{narrative_text}", text)
            .replace("{PublicationDate}", pub_date))

# ============================
# 🔁 SAFE MODEL INVOKER
# ============================
def ask_gemini(prompt, retries=5):
    for attempt in range(retries):
        try:
            res = model.generate_content(prompt, generation_config={
                "temperature": 0.0,
                "max_output_tokens": 4096
            })
            return res.text
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("❌ MAX RETRIES REACHED")

# ============================
# 🔎 JSON PARSER (ROBUST)
# ============================
def parse_json(output):
    try:
        return json.loads(output)
    except:
        block = re.search(r"```json\s*([\s\S]*?)```", output)
        if block:
            try: return json.loads(block.group(1))
            except: pass
        # fallback remove backticks
        try: return json.loads(output.strip("` \n"))
        except:
            print("❌ BAD JSON OUTPUT:\n", output[:300])
            return {}

# ============================
# 🧠 PROCESS ONE ARTICLE
# ============================
def process_article(article, pub_date, metadata):
    prompt = build_prompt(article, pub_date)
    response = ask_gemini(prompt)
    parsed = parse_json(response)

    # Normalize parsed JSON object
    if isinstance(parsed, list) and len(parsed)==1:
        parsed = parsed[0]

    # Attach metadata (like timeline-gen.py)
    parsed["title"]          = metadata.get("title","")
    parsed["url"]            = metadata.get("url","")
    parsed["source"]         = metadata.get("source","")
    parsed["section"]        = metadata.get("section","")
    parsed["PublicationDate"]= pub_date
    return parsed, response

# ============================
# 📄 LOAD COLLECTION
# ============================
with open(DATA_PATH, "r", encoding="utf-8") as f:
    text_all = f.read()

articles = [a.strip() for a in re.split(r"\n={3,}\n", text_all) if a.strip()]

# ============================
# 📦 LOAD EXISTING CHECKPOINTS
# ============================
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

if os.path.exists(OUT_JSON):
    try: structured_all = json.load(open(OUT_JSON, "r"))
    except: structured_all = []
else:
    structured_all = []

if os.path.exists(OUT_TXT):
    existing_raw = open(OUT_TXT,"r").read()
else:
    existing_raw = ""

done = set((x.get("title"), x.get("PublicationDate")) for x in structured_all)

# ============================
# 🚧 RUN EXTRACTION
# ============================
new_structured = []
raw_to_append  = []

for idx, art in enumerate(tqdm(articles, desc=f"📰 Extracting from {COLLECTION}"), start=1):

    title  = re.search(r"^Title:\s*(.*)", art, re.M)
    title  = title.group(1).strip() if title else f"Article {idx}"

    pub    = re.search(r"^Publication Date:\s*(.+)", art, re.M)
    pub    = pub.group(1).strip() if pub else "Unknown"
    pub_iso= re.search(r"\d{4}-\d{2}-\d{2}", pub)
    pub    = pub_iso.group(0) if pub_iso else pub  # extract ISO

    key = (title, pub)
    if key in done:
        print(f"⏭️ Already processed: {title}")
        continue

    meta = {
        "title": title,
        "url": re.search(r"^URL:\s*(.*)", art, re.M).group(1).strip() if re.search(r"^URL:", art, re.M) else "",
        "source": re.search(r"^Source:\s*(.*)", art, re.M).group(1).strip() if re.search(r"^Source:", art, re.M) else "",
        "section": re.search(r"^Section:\s*(.*)", art, re.M).group(1).strip() if re.search(r"^Section:", art, re.M) else "",
    }

    result, raw = process_article(art, pub, meta)
    raw_to_append.append(f"\n=== {title} ===\n{raw}\n")
    new_structured.append(result)
    structured_all.append(result)

    # checkpoint save every 3
    if len(new_structured) % 3 == 0:
        open(OUT_TXT,"a").write("\n".join(raw_to_append))
        json.dump(structured_all, open(OUT_JSON,"w"), indent=2, ensure_ascii=False)
        raw_to_append = []
        print("💾 Checkpoint Saved")

# ============ FINAL SAVE ============
if raw_to_append:
    open(OUT_TXT,"a").write("\n".join(raw_to_append))

json.dump(structured_all, open(OUT_JSON,"w"), indent=2, ensure_ascii=False)
print("\n🎉 DONE! Timeline saved at:\n📌", OUT_JSON)