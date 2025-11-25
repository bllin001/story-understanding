import json
import pandas as pd
import os

# ============================
# 📌 FILE PATHS
# ============================
FILE_GEMINI = "../output/timelines/mozambique/gemini-2.0-flash/mozambique_narrative_timeline.json"
FILE_GPT    = "../output/timelines/mozambique/gpt-4o-mini/mozambique_narrative_timeline.json"
OUT_EXCEL   = "../output/timelines/mozambique/evaluation_timeline.xlsx"

# ============================
# 📌 SAFE LOADER
# ============================
def safe_load(path, model_name):
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ JSON read error for {path}: {e}")
        return []

    rows = []
    for article in data:
        for ev in article.get("timeline", []):
            rows.append({
                
                # --- Article Metadata ---
                "Article_Title": article.get("title", ""),
                "PublicationDate": article.get("PublicationDate", ""),
                "URL": article.get("url", ""),
                "Source": article.get("source", ""),
                "Section": article.get("section", ""),

                # --- Model Source ---
                "Model": model_name,

                # --- Extracted Event Info ---
                "Event_Title": ev.get("Title", ""),
                "Event_Description": ev.get("Text", ""),
                "Event_Date": ev.get("Date", ""),
                "Date_Context": ev.get("Context", ""),
                "EventRoot": ev.get("EventOrigin", ""),
                "EventType": ev.get("EventType", ""),
                "SourceSentence": ev.get("SourceSentence", ""),
                "Confidence": ev.get("Confidence", ""),

                # ====================================
                # 🧪 Human Evaluation (Blank Initially)
                # ====================================
                "Eval_DateCorrect (0-1)": "",
                "Eval_RootEvent (0-1)": "",
                "Eval_EventType (0-1)": "",
                "Eval_EventAmbiguity (1-3)": "",
                "Eval_Relevance (1-3)": "",

                # 🧮 Score Final (computado después)
                "EQS_Score (0-1)": "",

                # ✏️ Optional Notes by Evaluator
                "Eval_Comment": ""
        })
    return rows

# ============================
# 📌 LOAD BOTH MODELS
# ============================
gemini_rows = safe_load(FILE_GEMINI, "gemini-2.0-flash")
gpt_rows    = safe_load(FILE_GPT, "gpt-4o-mini")

# ============================
# 📌 MERGE AND SAVE
# ============================
df = pd.DataFrame(gemini_rows + gpt_rows)

# Group by Article_Title
df = df.sort_values(by=["Article_Title", "Model"])
df.to_excel(OUT_EXCEL, index=False)

print(f"📌 Evaluation matrix created:\n   {OUT_EXCEL}")
print(f"🔹 Gemini events: {len(gemini_rows)}")
print(f"🔹 GPT events:    {len(gpt_rows)}")