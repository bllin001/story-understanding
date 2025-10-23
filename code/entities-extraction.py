import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import re
import json

# Load environment variables
load_dotenv()

data = pd.read_json('../data/Mozambique_articles_gnews.json')

# Display information about the dataset
print(f"Total number of articles: {len(data)}")
print(f"First article title: {data.iloc[0]['data']['title']}")
print(f"First article content sample: {data.iloc[0]['data']['content'][:150]}...\n")

# Load the entity extraction prompt template
with open('../data/prompt-entity.txt', 'r') as file:
    prompt_template = file.read()

# Initialize LLM
llm = ChatOpenAI(temperature=0.0, model="gpt-4o-mini")

# Create processing chain
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

# Process the first article as a test
article_content = data.iloc[0]['data']['content']
article_title = data.iloc[0]['data']['title']
print(f"Processing article: {article_title}")

# Invoke the LLM chain
response = chain.invoke({"input_text": article_content})

# Print a sample of the response
print(f"Response sample (first 500 characters):\n{response[:500]}...\n")

# Save the response to a file
output_file_path = '../output/entities_article_0.txt'
with open(output_file_path, 'w') as file:
    file.write(f"Article Title: {article_title}\n\n")
    file.write(response)

print(f"Full response saved to {output_file_path}")

# Save entities and relations in a structured format
entities_output_path = '../output/entities_article_0.json'

# Parse entities and relationships from the response
def parse_response(response_text):
    # Define the replacements for delimiters in the response
    tuple_delimiter = '{tuple_delimiter}'
    record_delimiter = '{{record_delimiter}}'
    completion_delimiter = '{completion_delimiter}'
    
    # Clean up the response text
    clean_response = response_text.replace(completion_delimiter, '').strip()
    
    # Split by record delimiter if present, otherwise split by newlines
    if record_delimiter in clean_response:
        records = clean_response.split(record_delimiter)
    else:
        # Filter out empty lines and strip whitespace
        records = [line.strip() for line in clean_response.split('\n') if line.strip()]
    
    entities = []
    relationships = []
    
    # Process each record
    for record in records:
        # Skip empty records
        if not record.strip():
            continue
        
        # Check if this is an entity or relationship
        if record.startswith('("entity"'):
            # Extract entity components using regex
            pattern = r'\("entity"{0}(.*?){0}(.*?){0}(.*?)\)'.format(re.escape(tuple_delimiter))
            match = re.search(pattern, record)
            
            if match:
                entity_name = match.group(1)
                entity_type = match.group(2)
                entity_description = match.group(3)
                
                entities.append({
                    'name': entity_name,
                    'type': entity_type,
                    'description': entity_description
                })
        
        elif record.startswith('("relationship"'):
            # Extract relationship components using regex
            pattern = r'\("relationship"{0}(.*?){0}(.*?){0}(.*?){0}(.*?){0}(\d+)\)'.format(re.escape(tuple_delimiter))
            match = re.search(pattern, record)
            
            if match:
                source_entity = match.group(1)
                target_entity = match.group(2)
                mechanism = match.group(3)
                relationship_description = match.group(4)
                relationship_strength = int(match.group(5))
                
                relationships.append({
                    'source': source_entity,
                    'target': target_entity,
                    'mechanism': mechanism,
                    'description': relationship_description,
                    'strength': relationship_strength
                })
    
    return {
        'entities': entities,
        'relationships': relationships
    }

# Parse the response and convert to structured format
structured_data = parse_response(response)

# Save to JSON file
with open(entities_output_path, 'w', encoding='utf-8') as f:
    json.dump(structured_data, f, indent=2, ensure_ascii=False)

print(f"Structured data saved to {entities_output_path}")

# Print some statistics
print(f"Extracted {len(structured_data['entities'])} entities and {len(structured_data['relationships'])} relationships")
