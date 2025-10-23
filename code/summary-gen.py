import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Load the narrative text
with open('../data/narrative.txt', 'r', encoding='utf-8') as file:
    narrative_text = file.read()

# Display information about the narrative
print(f"Narrative text loaded")
print(f"Text length: {len(narrative_text)} characters")
print(f"First 200 characters: {narrative_text[:200]}...\n")

# Load the summarization prompt template
with open('../data/prompt-summarization.txt', 'r', encoding='utf-8') as file:
    prompt_template = file.read()

# Initialize LLM
llm = ChatOpenAI(temperature=0.0, model="gpt-4o-mini")

# Create processing chain
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

print("Processing narrative for summarization...")

# Invoke the LLM chain
response = chain.invoke({"narrative_text": narrative_text})

# Print a sample of the response
print(f"Response sample (first 500 characters):\n{response[:500]}...\n")

# Save the response to a text file
output_file_path = '../output/narrative_summary.txt'
with open(output_file_path, 'w', encoding='utf-8') as file:
    file.write("=== Mozambique Political Crisis Summary ===\n\n")
    file.write(response)

print(f"Full summary saved to {output_file_path}")

# Parse and save summary in a structured format
summary_output_path = '../output/narrative_summary.json'

def parse_summary_response(response_text):
    """
    Parse the summary response to extract sentence breakdown and summary content
    """
    import re
    
    # Clean up the response text
    clean_response = response_text.strip()
    
    # Initialize output structure
    result = {
        'narrative_source': 'narrative.txt',
        'sentences': [],
        'summary': '',
        'word_count': 0,
        'character_count': 0
    }
    
    # Split response into sections using more flexible parsing
    lines = clean_response.split('\n')
    
    # Find sections
    sentence_breakdown_section = False
    summary_section = False
    current_section_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Check for section headers
        if 'Narrative Text' in line and '===' in line:
            sentence_breakdown_section = True
            summary_section = False
            current_section_lines = []
        elif 'Summary' in line and '===' in line and 'End' not in line:
            sentence_breakdown_section = False
            summary_section = True
            current_section_lines = []
        elif 'End of Summary' in line or '######################' in line:
            summary_section = False
            if current_section_lines and summary_section:
                break
        elif sentence_breakdown_section:
            # Look for numbered sentences like "1. Text" or "1) Text"
            if re.match(r'^\d+\.', line):
                current_section_lines.append(line)
        elif summary_section:
            if line and not line.startswith('==='):
                current_section_lines.append(line)
    
    # Parse sentences from narrative text section
    sentence_lines = []
    in_narrative = False
    
    for line in lines:
        line = line.strip()
        if 'Narrative Text' in line and '===' in line:
            in_narrative = True
            continue
        elif '===' in line and in_narrative:
            in_narrative = False
            break
        elif in_narrative and line:
            # Match patterns like "1. Text" or "1) Text"
            if re.match(r'^\d+\.', line):
                sentence_lines.append(line)
    
    # Extract sentences
    for sentence_line in sentence_lines:
        # Parse "1. Sentence text"
        match = re.match(r'^(\d+)\.\s*(.+)', sentence_line)
        if match:
            sentence_id = int(match.group(1))
            sentence_text = match.group(2).strip()
            result['sentences'].append({
                'id': sentence_id,
                'text': sentence_text
            })
    
    # Extract summary text
    summary_lines = []
    in_summary = False
    
    for line in lines:
        line = line.strip()
        if 'Summary' in line and '===' in line and 'End' not in line:
            in_summary = True
            continue
        elif ('End of Summary' in line or '######################' in line) and in_summary:
            break
        elif in_summary and line and not line.startswith('==='):
            summary_lines.append(line)
    
    # Join summary lines
    if summary_lines:
        summary_text = ' '.join(summary_lines).strip()
        result['summary'] = summary_text
        result['word_count'] = len(summary_text.split())
        result['character_count'] = len(summary_text)
    
    return result

# Parse the response and convert to structured format
structured_summary = parse_summary_response(response)

# Save to JSON file
with open(summary_output_path, 'w', encoding='utf-8') as f:
    json.dump(structured_summary, f, indent=2, ensure_ascii=False)

print(f"Structured summary saved to {summary_output_path}")

# Print some statistics
print(f"Summary statistics:")
print(f"- Word count: {structured_summary['word_count']}")
print(f"- Character count: {structured_summary['character_count']}")
print(f"- Original text length: {len(narrative_text)} characters")
print(f"- Compression ratio: {len(narrative_text) / structured_summary['character_count']:.2f}x")
