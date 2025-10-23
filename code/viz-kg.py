# Visualize knowledge graph entities that are saved in the json file in a web browser.
import json
import os
import sys
import re
import argparse
import webbrowser
import html
from pathlib import Path
from pyvis.network import Network
import networkx as nx

# Load data directly from files
def load_data():
    """Load narrative and entities data from files"""
    try:
        # Load narrative text
        with open('../data/narrative.txt', 'r', encoding='utf-8') as f:
            narrative_text = f.read()
        
        # Load entities and relationships
        with open('../data/entities_article_0.json', 'r', encoding='utf-8') as f:
            entities_data = json.load(f)
        
        return narrative_text, entities_data
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        return None, None
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None

def create_knowledge_graph(data):
    """
    Create a networkx graph from entities and relationships data
    
    Args:
        data: Dictionary containing 'entities' and 'relationships' lists
    
    Returns:
        A networkx graph object
    """
    G = nx.DiGraph()
    
    # Entity type color mapping
    color_map = {
        'actor': '#4287f5',    # blue
        'factor': '#f542a1',   # pink
        'event': '#42f569'     # green
    }
    
    # Add entities as nodes
    for entity in data['entities']:
        G.add_node(
            entity['name'],
            title=entity['description'],
            group=entity['type'],
            color=color_map.get(entity['type'], '#97C2FC')
        )
    
    # Add relationships as edges
    for rel in data['relationships']:
        G.add_edge(
            rel['source'],
            rel['target'],
            title=f"{rel['mechanism']}: {rel['description']} (Strength: {rel['strength']})",
            label=rel['mechanism'],
            value=rel['strength'],
            arrows='to'
        )
    
    return G

def highlight_text(text, entities, relationships):
    """
    Highlight entities and relationships in the original text
    
    Args:
        text: Original narrative text
        entities: List of entity dictionaries
        relationships: List of relationship dictionaries
        
    Returns:
        HTML string with highlighted entities and relationships
    """
    # Escape HTML special characters
    highlighted_text = html.escape(text)
    
    # Sort entities by length of name (descending) to avoid partial matches
    sorted_entities = sorted(entities, key=lambda x: len(x['name']), reverse=True)
    
    # Replace entity mentions with highlighted spans
    entity_colors = {
        'actor': '#4287f5',    # blue
        'factor': '#f542a1',   # pink
        'event': '#42f569'     # green
    }
    
    # Dictionary to track replaced entities to avoid tooltips in tooltips
    replaced_positions = {}
    
    for entity in sorted_entities:
        entity_name = entity['name']
        entity_type = entity['type']
        color = entity_colors.get(entity_type, '#97C2FC')
        
        # Create the replacement with a colored background and tooltip
        # Shorten the description for the tooltip to prevent overflowing
        short_desc = entity['description']
        if len(short_desc) > 100:
            short_desc = short_desc[:97] + "..."
        
        # Use regex to find whole word matches with word boundaries
        pattern = re.compile(r'\b' + re.escape(entity_name) + r'\b', re.IGNORECASE)
        
        # Find all matches in the text
        matches = list(pattern.finditer(highlighted_text))
        
        # Process matches in reverse order to not mess up string indices
        for match in reversed(matches):
            # Check if this position overlaps with any previously replaced entity
            start, end = match.span()
            overlap = False
            for pos_start, pos_end in replaced_positions.items():
                if (start <= pos_end and end >= pos_start):
                    overlap = True
                    break
                    
            if not overlap:
                # Add position to our tracking dictionary
                replaced_positions[start] = end
                
                # Create the replacement with a colored background and tooltip
                entity_text = highlighted_text[start:end]
                replacement = f'<span class="entity-highlight" style="background-color: {color}30; border-bottom: 2px solid {color}; cursor: pointer;" data-entity-type="{entity_type}" data-entity-id="{entity_name}" title="{html.escape(short_desc)}">{entity_text}</span>'
                
                # Replace this specific occurrence
                highlighted_text = highlighted_text[:start] + replacement + highlighted_text[end:]
    
    # Convert newlines to HTML breaks and wrap paragraphs
    paragraphs = highlighted_text.split('\n\n')
    formatted_paragraphs = []
    for paragraph in paragraphs:
        if paragraph.strip():  # Only add non-empty paragraphs
            formatted_paragraphs.append(f'<p>{paragraph.strip()}</p>')
    
    highlighted_text = '\n'.join(formatted_paragraphs)
    
    return highlighted_text

def create_enhanced_html(graph, output_path, title, narrative_text=None, entities=None, relationships=None):
    """
    Create an enhanced HTML file with both the graph visualization and highlighted narrative
    
    Args:
        graph: A networkx graph object
        output_path: Path to save the HTML file
        title: Title of the visualization
        narrative_text: Original narrative text (optional)
        entities: List of entity dictionaries (optional)
        relationships: List of relationship dictionaries (optional)
    """
    # Create a pyvis network for the graph part
    net = Network(height='500px', width='100%', directed=True, notebook=False)
    net.from_nx(graph)
    
    # Configure visualization options
    net.set_options('''
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {
          "enabled": true,
          "iterations": 1000
        }
      },
      "edges": {
        "color": {
          "inherit": true
        },
        "smooth": {
          "enabled": false,
          "type": "continuous"
        },
        "font": {
          "size": 12,
          "face": "Arial",
          "strokeWidth": 3,
          "strokeColor": "#ffffff"
        }
      },
      "nodes": {
        "font": {
          "size": 16,
          "face": "Arial",
          "strokeWidth": 3,
          "strokeColor": "#ffffff"
        }
      },
      "interaction": {
        "tooltipDelay": 200,
        "hover": true,
        "hideEdgesOnDrag": true
      }
    }
    ''')
    
    # Generate the graph HTML
    net.save_graph("/tmp/temp_graph.html")
    
    with open("/tmp/temp_graph.html", "r") as f:
        graph_html = f.read()
    
    # Extract just the vis-network div and script
    graph_content = re.search(r'<div id=".*?">.*?</script>', graph_html, re.DOTALL).group(0)
    
    # Create the full HTML with both graph and narrative
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            display: flex;
            flex-direction: column;
            max-width: 100%;
            margin: 0 auto;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        h1 {{
            text-align: center;
            padding: 20px;
            margin: 0;
            background-color: #4287f5;
            color: white;
        }}
        .content-wrapper {{
            display: flex;
            flex-direction: column;
            min-height: 900px;
            width: 100%;
        }}
        .narrative-container {{
            flex: 1;
            padding: 20px;
            line-height: 1.6;
            overflow-y: auto;
            min-height: 400px;
            max-height: 400px;
            width: 100%;
            box-sizing: border-box;
            border-bottom: 1px solid #eee;
        }}
        .narrative-container p {{
            margin-bottom: 15px;
        }}
        .narrative-container h2 {{
            margin-top: 0;
            margin-bottom: 20px;
            color: #333;
        }}
        .graph-container {{
            flex: 1;
            min-height: 500px;
            height: 500px;
            width: 100%;
            position: relative;
            overflow: hidden;
        }}
        .graph-container > div {{
            width: 100% !important;
            height: 100% !important;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            margin: 10px 0;
            padding: 10px;
            background-color: #f9f9f9;
            border-bottom: 1px solid #eee;
        }}
        .legend-item {{
            margin: 0 10px;
            display: flex;
            align-items: center;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            margin-right: 5px;
            border-radius: 3px;
        }}
        /* Enhanced tooltip styling */
        .entity-highlight {{
            position: relative;
            padding: 2px 4px;
            border-radius: 3px;
            display: inline;
        }}
        .entity-highlight:hover::after {{
            content: attr(title);
            position: absolute;
            left: 0;
            bottom: 100%;
            width: 250px;
            background-color: rgba(0,0,0,0.85);
            color: white;
            padding: 10px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 100;
            line-height: 1.5;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            pointer-events: none;
        }}
    </style>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css">
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background-color: #4287f5;"></div>
                <span>Actor</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #f542a1;"></div>
                <span>Factor</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #42f569;"></div>
                <span>Event</span>
            </div>
        </div>
        <div class="content-wrapper">
    """
    
    # Add the narrative section first (left side) if provided
    if narrative_text and entities and relationships:
        highlighted_text = highlight_text(narrative_text, entities, relationships)
        html_template += f"""
            <div class="narrative-container">
                <h2>Original Narrative with Highlighted Entities</h2>
                <div>{highlighted_text}</div>
            </div>
        """
    
    # Add graph container (right side)
    html_template += f"""
            <div class="graph-container">
                {graph_content}
            </div>
        """
    
    html_template += """
        </div>
    </div>
</body>
</html>
    """
    
    # Write the complete HTML to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"Enhanced visualization saved to {output_path}")
    
    # Open the visualization in the default web browser
    webbrowser.open(f"file://{os.path.abspath(output_path)}")

def visualize_knowledge_graph(graph, output_path, title="Knowledge Graph Visualization", narrative_text=None, entities=None, relationships=None):
    """
    Create an interactive HTML visualization of the knowledge graph
    
    Args:
        graph: A networkx graph object
        output_path: Path to save the HTML file
        title: Title of the visualization
        narrative_text: Original narrative text (optional)
        entities: List of entity dictionaries (optional)
        relationships: List of relationship dictionaries (optional)
    """
    if narrative_text and entities and relationships:
        create_enhanced_html(graph, output_path, title, narrative_text, entities, relationships)
    else:
        # Create a basic pyvis network visualization
        net = Network(height='800px', width='100%', directed=True, notebook=False)
        net.from_nx(graph)
        
        # Configure visualization options
        net.set_options('''
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
              "enabled": true,
              "iterations": 1000
            }
          },
          "edges": {
            "color": {
              "inherit": true
            },
            "smooth": {
              "enabled": false,
              "type": "continuous"
            }
          },
          "interaction": {
            "tooltipDelay": 200,
            "hover": true,
            "hideEdgesOnDrag": true
          }
        }
        ''')
        
        # Save the visualization
        net.save_graph(str(output_path))
        print(f"Basic visualization saved to {output_path}")
        
        # Open the visualization in the default web browser
        webbrowser.open(f"file://{os.path.abspath(output_path)}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Visualize knowledge graph from JSON file")
    parser.add_argument(
        "input_file", 
        type=Path, 
        help="Path to JSON file containing entities and relationships"
    )
    parser.add_argument(
        "-o", "--output", 
        type=Path, 
        help="Path to save the HTML visualization", 
        default=None
    )
    parser.add_argument(
        "-n", "--narrative", 
        type=Path, 
        help="Path to text file containing the original narrative",
        default=None
    )
    parser.add_argument(
        "--raw-text", 
        type=str, 
        help="Raw narrative text to highlight entities and relationships",
        default=None
    )
    return parser.parse_args()

def main():
    """Main function to run the script"""
    # Load data directly from files
    narrative_text, data = load_data()
    
    if narrative_text is None or data is None:
        print("Failed to load data. Exiting.")
        return
    
    # Set output path
    output_path = Path('../data/mozambique_kg_visualization.html')
    
    # Create and visualize the graph
    graph = create_knowledge_graph(data)
    
    # Create visualization with narrative
    visualize_knowledge_graph(
        graph, 
        output_path, 
        title="Mozambique Political Knowledge Graph",
        narrative_text=narrative_text,
        entities=data['entities'],
        relationships=data['relationships']
    )

if __name__ == "__main__":
    main()
