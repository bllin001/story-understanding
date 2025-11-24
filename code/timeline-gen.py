import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json
import re
import datetime
import time
import random
import os
import math
from tqdm.auto import tqdm, trange
import csv

# Optional exact token counting using tiktoken (fallback to char heuristic)
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except Exception:
    TIKTOKEN_AVAILABLE = False

# Pricing per model (USD per 1k tokens)
# Values are derived from per-1M-token prices provided in configuration or documentation.
# Example source prices (per 1M tokens):
#   gpt-4o-mini: input=$0.15, cache_input=$0.075, output=$0.60
# Conversion: per_1k = per_1M / 1000
PRICING = {
    'gpt-4o-mini': {
        # input per 1M = $0.15 -> per 1k = 0.15 / 1000 = 0.000150
        'input': 0.000150,
        # cached input (if/when a cache hit pricing applies) per 1M = $0.075 -> per 1k = 0.000075
        'cache_input': 0.000075,
        # output per 1M = $0.60 -> per 1k = 0.60 / 1000 = 0.000600
        'output': 0.000600,
    },
}

def count_tokens_for_model(text, model='gpt-4o-mini'):
    """Return token count for text. Use tiktoken if available, otherwise heuristic."""
    if TIKTOKEN_AVAILABLE:
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            enc = tiktoken.get_encoding('cl100k_base')
        return len(enc.encode(text))
    # fallback heuristic: ~4 chars per token
    return int(max(1, round(len(text) / 4.0)))

def _find_balanced(text, start_idx=0, open_char='{', close_char='}'):
    """Find substring starting at the first open_char at or after start_idx and return the balanced substring.
    Returns (substring, start_index, end_index) or (None, -1, -1) if not found.
    """
    i = text.find(open_char, start_idx)
    if i == -1:
        return None, -1, -1
    depth = 0
    for j in range(i, len(text)):
        if text[j] == open_char:
            depth += 1
        elif text[j] == close_char:
            depth -= 1
            if depth == 0:
                return text[i:j+1], i, j+1
    return None, -1, -1


def parse_timeline_response(response_text, metadata=None):
    """Parse the timeline response to extract timeline events and optional metadata.

    This function is robust to LLM outputs that put JSON objects or arrays inside
    markdown code blocks or inline. It will try to find the first JSON object or
    array and parse it. If the top-level object contains `PublicationDate` and
    `Events`, those are used directly.
    """
    clean_response = response_text or ""
    result = {
        'timeline': [],
        'event_count': 0
    }

    # 1) Try to extract JSON from ```json``` code block (object or array)
    json_block_match = re.search(r'```json\s*', clean_response, re.IGNORECASE)
    json_text = None
    if json_block_match:
        # Search for first balanced object or array after the code fence
        fence_end = json_block_match.end()
        # Try object first
        obj_text, s, e = _find_balanced(clean_response, fence_end, '{', '}')
        if obj_text:
            json_text = obj_text
        else:
            arr_text, s, e = _find_balanced(clean_response, fence_end, '[', ']')
            if arr_text:
                json_text = arr_text

    # 2) If not in code block, try to find the first JSON array/object anywhere
    if not json_text:
        # Try array first
        arr_text, s, e = _find_balanced(clean_response, 0, '[', ']')
        if arr_text:
            json_text = arr_text
        else:
            obj_text, s, e = _find_balanced(clean_response, 0, '{', '}')
            if obj_text:
                # Prefer objects that contain PublicationDate or Events
                if '"PublicationDate"' in obj_text or '"Events"' in obj_text:
                    json_text = obj_text

    # 3) If we still don't have JSON, try to extract between === Timeline === markers
    if not json_text and '=== Timeline ===' in clean_response:
        timeline_section = clean_response.split('=== Timeline ===', 1)[1]
        if '=== End of Timeline ===' in timeline_section:
            timeline_text = timeline_section.split('=== End of Timeline ===', 1)[0]
        else:
            timeline_text = timeline_section
        # attempt to find an array in that section
        arr_text, s, e = _find_balanced(timeline_text, 0, '[', ']')
        if arr_text:
            json_text = arr_text
        else:
            obj_text, s, e = _find_balanced(timeline_text, 0, '{', '}')
            if obj_text and ('"PublicationDate"' in obj_text or '"Events"' in obj_text):
                json_text = obj_text

    # 4) Parse discovered JSON
    if json_text:
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as e:
            # If strict parse fails, attempt a relaxed cleanup (remove trailing commas)
            try:
                cleaned = re.sub(r',\s*,', ',', json_text)
                cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
                parsed = json.loads(cleaned)
            except Exception as e2:
                print(f"JSON parsing error: {e} then cleanup failed: {e2}")
                result['timeline'] = extract_timeline_manually(clean_response)
                result['event_count'] = len(result['timeline'])
                return result

        events_list = []
        # If top-level is an object with PublicationDate and Events
        if isinstance(parsed, dict):
            if 'Events' in parsed and isinstance(parsed['Events'], list):
                events_list = parsed['Events']
            else:
                # Could be a single event-like dict
                if 'Date' in parsed:
                    events_list = [parsed]
            # Attach publication date metadata if present
            if 'PublicationDate' in parsed:
                result['PublicationDate'] = parsed.get('PublicationDate')

        elif isinstance(parsed, list):
            # If list contains event dicts (Date keys), use directly
            if parsed and all(isinstance(it, dict) and 'Date' in it for it in parsed):
                events_list = parsed
            else:
                # Collect Events arrays from wrapper objects
                for item in parsed:
                    if isinstance(item, dict) and 'Events' in item and isinstance(item['Events'], list):
                        events_list.extend(item['Events'])

        # Sort and return
        sorted_events = sort_timeline_events(events_list)
        result['timeline'] = sorted_events
        result['event_count'] = len(sorted_events)
        return result

    # Fallback: no JSON found, extract manually
    result['timeline'] = extract_timeline_manually(clean_response)
    result['event_count'] = len(result['timeline'])
    return result

def sort_timeline_events(events):
    """
    Sort timeline events by date, handling various date formats
    """
    def parse_date_for_sorting(date_str):
        """
        Convert date string to a sortable format
        """
        # Handle year-only dates (e.g., "1975")
        if re.match(r'^\d{4}$', date_str):
            return datetime.datetime(int(date_str), 1, 1)
        
        # Handle YYYY/Month/DD format
        try:
            # Try various date formats
            for fmt in ['%Y/%m/%d', '%Y/%B/%d', '%Y/%b/%d', '%Y-%m-%d', '%Y-%B-%d', '%Y-%b-%d']:
                try:
                    return datetime.datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
            # Handle relative dates (put at end for now)
            if any(word in date_str.lower() for word in ['friday', 'monday', 'recent', 'late']):
                return datetime.datetime(2024, 10, 18)  # Approximate date for relative references
                
            # If can't parse, use a default date
            return datetime.datetime(2024, 1, 1)
            
        except:
            return datetime.datetime(2024, 1, 1)
    
    # Sort events by parsed date
    try:
        sorted_events = sorted(events, key=lambda x: parse_date_for_sorting(x.get('Date', '')))
        return sorted_events
    except:
        # If sorting fails, return original order
        return events

def extract_timeline_manually(timeline_text):
    """
    Manually extract timeline events from text if JSON parsing fails
    """
    events = []
    
    # Split by common delimiters and look for structured patterns
    lines = timeline_text.split('\n')
    current_event = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for date patterns
        date_match = re.search(r'"Date":\s*"([^"]+)"', line)
        if date_match:
            current_event['Date'] = date_match.group(1)
        
        # Look for text patterns
        text_match = re.search(r'"Text":\s*"([^"]+)"', line)
        if text_match:
            current_event['Text'] = text_match.group(1)
        
        # Look for source patterns
        source_match = re.search(r'"Source":\s*"([^"]+)"', line)
        if source_match:
            current_event['Source'] = source_match.group(1)
            
        # If we have all three components, add the event
        if len(current_event) == 3:
            events.append(current_event.copy())
            current_event = {}
    
    return events

def invoke_with_backoff(chain_callable, payload, max_retries=5, base_delay=1.0):
    """Invoke the chain with exponential backoff and jitter."""
    for attempt in range(1, max_retries + 1):
        try:
            return chain_callable(payload)
        except Exception as e:
            if attempt == max_retries:
                print(f"Final attempt failed: {e}")
                raise
            sleep_time = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(f"Invoke failed (attempt {attempt}/{max_retries}): {e}. Backing off {sleep_time:.1f}s")
            # Show a tqdm countdown for the sleep time (seconds)
            int_sec = int(math.floor(sleep_time))
            frac = sleep_time - int_sec
            if int_sec > 0:
                for _ in trange(int_sec, desc="backoff", leave=False):
                    time.sleep(1)
            if frac > 0:
                time.sleep(frac)

collection_name = "mozambique" # Can be drc, mozambique, sudan OR burundi

input_path = f"../data/collections/{collection_name}_articles_formatted.txt"

new_count = 0
save_every = 5
# Cost estimation settings (override with env var COST_PER_1K)
# Default cost per 1k tokens (USD) - change to match your billing rates
COST_PER_1K = float(os.getenv('COST_PER_1K', '0.03'))

# Records for reproducibility: per-article timings and estimated costs
cost_records = []
last_cost_index = 0

# Load environment variables
load_dotenv()

# Load the narrative text
with open(input_path, 'r', encoding='utf-8') as file:
    narrative_text = file.read()

# Display information about the narrative
print(f"Narrative text loaded")
print(f"Text length: {len(narrative_text)} characters")
print(f"First 200 characters: {narrative_text[:200]}...\n")

# Load the timeline prompt template
with open('../prompt/prompt-timeline.txt', 'r', encoding='utf-8') as file:
    prompt_template = file.read()

# Initialize LLM with token limit for concise timeline
llm = ChatOpenAI(temperature=0.0, model="gpt-4o-mini")

# Create processing chain
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

print("Processing narrative for timeline extraction...")

# Split the narrative into separate articles using the separator
articles = [a.strip() for a in re.split(r'\n={3,}\n', narrative_text) if a.strip()]

# Output paths (timelines folder)
raw_output_path = f'../output/timelines/{collection_name}/gpt-4o-mini/{collection_name}_narrative_timeline.txt'
timeline_output_path = f'../output/timelines/{collection_name}/gpt-4o-mini/{collection_name}_narrative_timeline.json'
os.makedirs(os.path.dirname(raw_output_path), exist_ok=True)

# Path for costs file (used for appends)
costs_path = os.path.join(os.path.dirname(timeline_output_path), f"{collection_name}_costs.txt")
costs_csv_path = os.path.join(os.path.dirname(timeline_output_path), f"{collection_name}_costs.csv")

# Load existing structured output (checkpoint) if present so we can skip processed articles
if os.path.exists(timeline_output_path):
    try:
        with open(timeline_output_path, 'r', encoding='utf-8') as f:
            existing_structured = json.load(f)
    except Exception:
        existing_structured = []
else:
    existing_structured = []

# Load existing raw text (so we don't duplicate when appending)
existing_raw_text = ''
if os.path.exists(raw_output_path):
    try:
        with open(raw_output_path, 'r', encoding='utf-8') as f:
            existing_raw_text = f.read()
    except Exception:
        existing_raw_text = ''

# Build set of processed article keys (title, PublicationDate)
processed_keys = set()
for item in existing_structured:
    key = (item.get('title'), item.get('PublicationDate'))
    processed_keys.add(key)

# Prepare output containers
all_structured = list(existing_structured)
new_texts = []



for idx, article in enumerate(tqdm(articles, desc="Articles", unit="article"), start=1):
    # Extract per-article metadata
    title_match = re.search(r"^Title:\s*(.+)", article, re.M)
    title = title_match.group(1).strip() if title_match else f"Article {idx}"
    url = re.search(r"^URL:\s*(.+)", article, re.M)
    url = url.group(1).strip() if url else "Unknown"
    image = re.search(r"^Image:\s*(.+)", article, re.M)
    image = image.group(1).strip() if image else "Unknown"
    source = re.search(r"^Source:\s*(.+)", article, re.M)
    source = source.group(1).strip() if source else "Unknown"
    section = re.search(r"^Section:\s*(.+)", article, re.M)
    section = section.group(1).strip() if section else "Unknown"

    pub_match = re.search(r"^Publication Date:\s*(.+)", article, re.M)
    pub_full = pub_match.group(1).strip() if pub_match else "Unknown"
    # Try to extract an ISO date (YYYY-MM-DD) from the publication date
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", pub_full)
    publication_date = iso_match.group(1) if iso_match else pub_full

    print(f"Processing article {idx}: {title} (PublicationDate: {publication_date})")

    # Skip if already processed (checkpoint exists)
    key = (title, publication_date)
    if key in processed_keys:
        print(f"Skipping article {idx}: already processed.")
        continue

    # Invoke the LLM chain for this article with backoff and measure time
    payload = {
        "narrative_text": article,
        # "PublicationDate": publication_date
    }
    start_ts = time.time()
    start_iso = datetime.datetime.utcnow().isoformat() + 'Z'
    response = invoke_with_backoff(chain.invoke, payload)
    end_ts = time.time()
    end_iso = datetime.datetime.utcnow().isoformat() + 'Z'
    duration = end_ts - start_ts

    # Save raw response for this article (collect to append later)
    new_texts.append(f"=== Article {idx}: {title} ===\n\n")
    new_texts.append(response)

    # Estimate tokens and cost using token counter (tiktoken if available)
    input_tokens = count_tokens_for_model(article, model=getattr(llm, 'model', 'gpt-4o-mini'))
    output_tokens = count_tokens_for_model(response or "", model=getattr(llm, 'model', 'gpt-4o-mini'))
    total_tokens = int(input_tokens + output_tokens)

    # Determine per-1k pricing for this model (fall back to default in PRICING)
    model_name = getattr(llm, 'model', 'gpt-4o-mini')
    pricing_info = PRICING.get(model_name, PRICING.get('gpt-4o-mini', {'input': COST_PER_1K, 'output': COST_PER_1K}))
    cost_input = (input_tokens / 1000.0) * pricing_info.get('input', COST_PER_1K)
    cost_output = (output_tokens / 1000.0) * pricing_info.get('output', COST_PER_1K)
    total_cost = cost_input + cost_output

    # Prepare metadata-first structured object so metadata appears before timeline
    structured = {
        'title': title,
        'url': url,
        'image': image,
        'source': source,
        'section': section,
        'PublicationDate': publication_date,
        'event_count': 0,
        'timeline': [],

    }

    # Parse the response into structured timeline for the article. Pass metadata so parser
    # can reference PublicationDate or other fields if needed.
    parsed = parse_timeline_response(response, metadata=structured)
    # Merge parsed timeline results back into structured (keep metadata first)
    structured['timeline'] = parsed.get('timeline', [])
    structured['event_count'] = parsed.get('event_count', 0)

    # Record cost/timing entry
    cost_records.append({
        'article_index': idx,
        'title': title,
        'PublicationDate': publication_date,
        'start_utc': start_iso,
        'end_utc': end_iso,
        'time_seconds': round(duration, 3),
        'input_tokens': int(input_tokens),
        'output_tokens': int(output_tokens),
        'total_tokens': int(total_tokens),
        'cost_input_usd': round(cost_input, 6),
        'cost_output_usd': round(cost_output, 6),
        'total_cost_usd': round(total_cost, 6),
        'model': model_name
    })

    all_structured.append(structured)
    processed_keys.add(key)
    new_count += 1

    # Checkpoint: save every `save_every` new articles
    if new_count > 0 and new_count % save_every == 0:
        try:
            # Append new_texts to raw output file (avoid overwriting existing file)
            if new_texts:
                with open(raw_output_path, 'a', encoding='utf-8') as f:
                    # ensure separation from prior content
                    f.write('\n')
                    f.write('\n'.join(new_texts))
                # update existing_raw_text so we don't duplicate on next checkpoint
                existing_raw_text += '\n'.join(new_texts)
                new_texts = []
        except Exception as e:
            print(f"Warning: failed to write raw output checkpoint: {e}")

        try:
            # Update structured JSON checkpoint (overwrite full structured file)
            with open(timeline_output_path, 'w', encoding='utf-8') as f:
                json.dump(all_structured, f, indent=2, ensure_ascii=False)
            print(f"Checkpoint saved after {new_count} new articles to {timeline_output_path}")
        except Exception as e:
            print(f"Warning: failed to write JSON checkpoint: {e}")

        # Also append interim cost entries to costs file (only new records since last write)
        try:
            # Ensure costs directory exists
            os.makedirs(os.path.dirname(costs_path), exist_ok=True)
            # If costs file does not exist or is empty, write a header
            write_header = not os.path.exists(costs_path) or os.path.getsize(costs_path) == 0
            with open(costs_path, 'a', encoding='utf-8') as cf:
                if write_header:
                    cf.write(f"Cost and timing report for {collection_name}\n")
                    cf.write(f"Generated at (first append): {datetime.datetime.utcnow().isoformat()}Z\n\n")
                # Append only new cost records that haven't been written yet
                for rec in cost_records[last_cost_index:]:
                    cf.write(f"Article {rec['article_index']}: {rec['title']}\n")
                    cf.write(f"  PublicationDate: {rec['PublicationDate']}\n")
                    cf.write(f"  Start: {rec['start_utc']}  End: {rec['end_utc']}\n")
                    cf.write(f"  Time(s): {rec.get('time_seconds', '')}  tokens(in/out/total): {rec.get('input_tokens','')}/{rec.get('output_tokens','')}/{rec.get('total_tokens','')}\n")
                    cf.write(f"  Cost: input=${rec.get('cost_input_usd','')} output=${rec.get('cost_output_usd','')} total=${rec.get('total_cost_usd','')}  model={rec.get('model','') if rec.get('model') else ''}\n\n")
                # Small batch summary
                batch_cost = sum(r.get('total_cost_usd', 0.0) for r in cost_records[last_cost_index:])
                batch_time = sum(r.get('time_seconds', 0.0) for r in cost_records[last_cost_index:])
                cf.write(f"BATCH APPEND: articles={len(cost_records[last_cost_index:])}  batch_time_s={round(batch_time,3)}  batch_total_cost_usd=${round(batch_cost,6)}\n\n")
            # Update tracker so we don't re-append the same records
            last_cost_index = len(cost_records)
            print(f"Checkpoint cost entries appended to {costs_path}")
        except Exception as e:
            print(f"Warning: failed to append cost checkpoint: {e}")

        # Also append CSV rows for posterior analysis
        try:
            write_csv_header = not os.path.exists(costs_csv_path) or os.path.getsize(costs_csv_path) == 0
            with open(costs_csv_path, 'a', newline='', encoding='utf-8') as csvf:
                writer = csv.writer(csvf)
                if write_csv_header:
                    writer.writerow(['article_index','title','PublicationDate','start_utc','end_utc','time_seconds','input_tokens','output_tokens','total_tokens','cost_input_usd','cost_output_usd','total_cost_usd','model'])
                for rec in cost_records[last_cost_index:]:
                    writer.writerow([rec['article_index'], rec['title'], rec['PublicationDate'], rec['start_utc'], rec['end_utc'], rec.get('time_seconds',''), rec.get('input_tokens',''), rec.get('output_tokens',''), rec.get('total_tokens',''), rec.get('cost_input_usd',''), rec.get('cost_output_usd',''), rec.get('total_cost_usd',''), rec.get('model','')])
        except Exception as e:
            print(f"Warning: failed to append cost CSV checkpoint: {e}")
        except Exception as e:
            print(f"Warning: failed to append cost checkpoint: {e}")

# Finalize raw text output (append any remaining new_texts)
try:
    if new_texts:
        with open(raw_output_path, 'a', encoding='utf-8') as file:
            file.write('\n')
            file.write('\n'.join(new_texts))
    print(f"Full timeline responses appended to {raw_output_path}")
except Exception as e:
    print(f"Warning: failed to append final raw output: {e}")

# Save combined structured JSON (list of article timelines)
try:
    with open(timeline_output_path, 'w', encoding='utf-8') as f:
        json.dump(all_structured, f, indent=2, ensure_ascii=False)
    print(f"Structured timeline(s) saved to {timeline_output_path}")
except Exception as e:
    print(f"Warning: failed to write final JSON output: {e}")

# Write final cost/timing append (only append new cost records since last checkpoint)
try:
    # Ensure costs directory exists
    os.makedirs(os.path.dirname(costs_path), exist_ok=True)
    write_header = not os.path.exists(costs_path) or os.path.getsize(costs_path) == 0
    with open(costs_path, 'a', encoding='utf-8') as cf:
        if write_header:
            cf.write(f"Cost and timing report for {collection_name}\n")
            cf.write(f"Generated at (first append): {datetime.datetime.utcnow().isoformat()}Z\n\n")
        # Append any remaining new cost records
        for rec in cost_records[last_cost_index:]:
            cf.write(f"Article {rec['article_index']}: {rec['title']}\n")
            cf.write(f"  PublicationDate: {rec['PublicationDate']}\n")
            cf.write(f"  Start: {rec['start_utc']}  End: {rec['end_utc']}\n")
            cf.write(f"  Time(s): {rec.get('time_seconds','')}  tokens(in/out/total): {rec.get('input_tokens','')}/{rec.get('output_tokens','')}/{rec.get('total_tokens','')}\n")
            cf.write(f"  Cost: input=${rec.get('cost_input_usd','')} output=${rec.get('cost_output_usd','')} total=${rec.get('total_cost_usd','')}  model={rec.get('model','') if rec.get('model') else ''}\n\n")
        # Batch summary for appended records
        batch_cost = sum(r.get('total_cost_usd', 0.0) for r in cost_records[last_cost_index:])
        batch_time = sum(r.get('time_seconds', 0.0) for r in cost_records[last_cost_index:])
        cf.write(f"FINAL APPEND: articles={len(cost_records[last_cost_index:])}  batch_time_s={round(batch_time,3)}  batch_total_cost_usd=${round(batch_cost,6)}\n\n")
    print(f"Final cost entries appended to {costs_path}")
except Exception as e:
    print(f"Warning: failed to append final cost file: {e}")

# Also append final CSV rows for posterior analysis
try:
    write_csv_header = not os.path.exists(costs_csv_path) or os.path.getsize(costs_csv_path) == 0
    with open(costs_csv_path, 'a', newline='', encoding='utf-8') as csvf:
        writer = csv.writer(csvf)
        if write_csv_header:
            writer.writerow(['article_index','title','PublicationDate','start_utc','end_utc','time_seconds','input_tokens','output_tokens','total_tokens','cost_input_usd','cost_output_usd','total_cost_usd','model'])
        for rec in cost_records[last_cost_index:]:
            writer.writerow([rec['article_index'], rec['title'], rec['PublicationDate'], rec['start_utc'], rec['end_utc'], rec.get('time_seconds',''), rec.get('input_tokens',''), rec.get('output_tokens',''), rec.get('total_tokens',''), rec.get('cost_input_usd',''), rec.get('cost_output_usd',''), rec.get('total_cost_usd',''), rec.get('model','')])
    print(f"Final cost CSV appended to {costs_csv_path}")
except Exception as e:
    print(f"Warning: failed to append final cost CSV: {e}")
except Exception as e:
    print(f"Warning: failed to append final cost file: {e}")

# Aggregate statistics
total_events = sum(item.get('event_count', 0) for item in all_structured)
print(f"Timeline statistics:")
print(f"- Total articles processed: {len(all_structured)}")
print(f"- Total events extracted: {total_events}")
print(f"- Original text length: {len(narrative_text)} characters")

# Print per-article verification
for idx, item in enumerate(all_structured, start=1):
    print(f"\nArticle {idx}: {item.get('title', 'Unknown')} — events: {item.get('event_count', 0)}")
    if item.get('timeline'):
        for i, event in enumerate(item['timeline'], 1):
            print(f"  {i}. {event.get('Date', 'Unknown Date')}: {event.get('Text', 'No description')[:100]}...")
    else:
        print("  No events extracted for this article.")
