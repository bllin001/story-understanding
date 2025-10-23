import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json
import re
import datetime

# Load environment variables
load_dotenv()

# Load the narrative text
with open('../data/narrative.txt', 'r', encoding='utf-8') as file:
    narrative_text = file.read()

# Display information about the narrative
print(f"Narrative text loaded")
print(f"Text length: {len(narrative_text)} characters")
print(f"First 200 characters: {narrative_text[:200]}...\n")

# Load the timeline prompt template
with open('../data/prompt-timeline.txt', 'r', encoding='utf-8') as file:
    prompt_template = file.read()

# Initialize LLM with token limit for concise timeline
llm = ChatOpenAI(temperature=0.0, model="gpt-4o-mini")

# Create processing chain
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

print("Processing narrative for timeline extraction...")

# Invoke the LLM chain
response = chain.invoke({"narrative_text": narrative_text})

# Print a sample of the response
print(f"Response sample (first 500 characters):\n{response[:500]}...\n")

# Save the response to a text file
output_file_path = '../output/narrative_timeline.txt'
with open(output_file_path, 'w', encoding='utf-8') as file:
    file.write("=== Mozambique Political Crisis Timeline ===\n\n")
    file.write(response)

print(f"Full timeline response saved to {output_file_path}")

# Parse and save timeline in a structured format
timeline_output_path = '../output/narrative_timeline.json'

def parse_timeline_response(response_text):
    """
    Parse the timeline response to extract timeline events
    """
    # Clean up the response text
    clean_response = response_text.strip()
    
    # Initialize output structure
    result = {
        'narrative_source': 'narrative.txt',
        'timeline': [],
        'event_count': 0
    }
    
    # Find JSON content - handle both markdown code blocks and direct JSON
    timeline_json = ""
    
    # Look for JSON within markdown code blocks first
    json_code_block_match = re.search(r'```json\s*(\[.*?\])\s*```', clean_response, re.DOTALL)
    if json_code_block_match:
        timeline_json = json_code_block_match.group(1)
    else:
        # Look for timeline section between === Timeline === markers
        if '=== Timeline ===' in clean_response:
            timeline_section = clean_response.split('=== Timeline ===')[1]
            if '=== End of Timeline ===' in timeline_section:
                timeline_text = timeline_section.split('=== End of Timeline ===')[0].strip()
            else:
                timeline_text = timeline_section.strip()
            
            # Look for JSON array pattern
            json_match = re.search(r'\[(.*?)\]', timeline_text, re.DOTALL)
            if json_match:
                timeline_json = '[' + json_match.group(1) + ']'
    
    # Parse the JSON timeline
    if timeline_json:
        try:
            timeline_events = json.loads(timeline_json)
            
            # Sort events by date
            sorted_events = sort_timeline_events(timeline_events)
            
            result['timeline'] = sorted_events
            result['event_count'] = len(sorted_events)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Fallback to manual extraction
            result['timeline'] = extract_timeline_manually(clean_response)
            result['event_count'] = len(result['timeline'])
    else:
        # Fallback to manual extraction
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

# Parse the response and convert to structured format
structured_timeline = parse_timeline_response(response)

# Save to JSON file
with open(timeline_output_path, 'w', encoding='utf-8') as f:
    json.dump(structured_timeline, f, indent=2, ensure_ascii=False)

print(f"Structured timeline saved to {timeline_output_path}")

# Print some statistics
print(f"Timeline statistics:")
print(f"- Total events extracted: {structured_timeline['event_count']}")
print(f"- Original text length: {len(narrative_text)} characters")

# Print timeline events for verification
if structured_timeline['timeline']:
    print(f"\nExtracted timeline events:")
    for i, event in enumerate(structured_timeline['timeline'], 1):
        print(f"{i}. {event.get('Date', 'Unknown Date')}: {event.get('Text', 'No description')[:100]}...")
else:
    print("\nNo timeline events were successfully extracted. Check the response format.")
