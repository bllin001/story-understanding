# Streamlit visualization for knowledge graph entities
import streamlit as st
import json
import streamlit.components.v1 as components
from PIL import Image
import requests
from io import BytesIO
import os
import time
from datetime import datetime

# Set page config with enhanced settings
st.set_page_config(
    page_title="News Article Storytelling",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/knowledge-graph',
        'Report a Bug': 'https://github.com/your-repo/knowledge-graph/issues',
        'About': """
        # News Article Storytelling Platform
        
        This application transforms news articles into interactive stories by extracting 
        and visualizing the key entities, events, and relationships that drive the narrative.
        
        **Storytelling Features:**
        - Narrative summarization
        - Chronological event timelines
        - Narrative Conceptualziation
        """
    }
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f8ff, #e6f3ff);
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    
    .summary-container {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        border-left: 4px solid #007bff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 2rem 0;
    }
    
    .summary-container:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    
    .metadata-item {
        background-color: #f8f9fa;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 5px;
        border-left: 3px solid #007bff;
    }
    
    .entity-header {
        font-weight: bold;
        color: #343a40;
        border-bottom: 2px solid #dee2e6;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .relationship-table {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .timeline-event {
        background-color: #f8f9fa;
        padding: 1rem;
        border-left: 4px solid #17a2b8;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
        transition: all 0.3s ease;
    }
    
    .timeline-event:hover {
        background-color: #e9ecef;
        transform: translateX(5px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .timeline-origin {
        position: relative;
    }
    
    .timeline-origin::before {
        content: '';
        position: absolute;
        left: -20px;
        top: 50%;
        transform: translateY(-50%);
        width: 10px;
        height: 10px;
        background: #dc3545;
        border-radius: 50%;
        box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.2);
    }
    
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
    
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    
    .info-tip {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
    
    .loading-spinner {
        text-align: center;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)  # Cache for 60 seconds only
def load_data():
    """Load narrative, entities, summary, and timeline data from files with enhanced error handling"""
    
    # Show loading message
    loading_placeholder = st.empty()
    loading_placeholder.markdown("""
    <div class="loading-spinner">
        <h4>🔄 Loading data...</h4>
        <p>Please wait while we fetch the latest information.</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Define file paths with better error handling
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(current_dir)  # Go up from code/ to root
        
        narrative_path = os.path.join(base_path, 'data', 'narrative.txt')
        entities_path = os.path.join(base_path, 'output', 'entities_article_0.json')
        summary_path = os.path.join(base_path, 'output', 'narrative_summary.json')
        timeline_path = os.path.join(base_path, 'output', 'narrative_timeline.json')
        
        # Check if required files exist
        missing_files = []
        for file_path, name in [
            (narrative_path, "Narrative file"),
            (entities_path, "Entities file")
        ]:
            if not os.path.exists(file_path):
                missing_files.append(f"{name} ({file_path})")
        
        if missing_files:
            loading_placeholder.empty()
            st.error(f"❌ **Missing required files:**\n" + "\n".join([f"• {file}" for file in missing_files]))
            return None, None, None, None, None
        
        # Load narrative text with enhanced metadata parsing
        with open(narrative_path, 'r', encoding='utf-8') as f:
            narrative_content = f.read()
        
        # Parse metadata from narrative with better validation
        metadata = {}
        narrative_text = narrative_content
        
        if narrative_content.startswith('---'):
            parts = narrative_content.split('---', 2)
            if len(parts) >= 3:
                metadata_section = parts[1].strip()
                narrative_text = parts[2].strip()
                
                # Parse metadata with better error handling
                for line in metadata_section.split('\n'):
                    if ':' in line and line.strip():
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and value:  # Only add non-empty key-value pairs
                            metadata[key] = value
        
        # Load entities and relationships with validation
        with open(entities_path, 'r', encoding='utf-8') as f:
            entities_data = json.load(f)
        
        # Validate entities data structure
        if not isinstance(entities_data, dict) or 'entities' not in entities_data:
            loading_placeholder.empty()
            st.error("❌ **Invalid entities data format.** Please check the entities file structure.")
            return None, None, None, None, None
        
        # Load optional summary data
        summary_data = None
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
            except json.JSONDecodeError:
                st.warning("⚠️ **Summary file exists but contains invalid JSON.** Skipping summary data.")
            except Exception as e:
                st.warning(f"⚠️ **Could not load summary data:** {str(e)}")
        
        # Load optional timeline data
        timeline_data = None
        if os.path.exists(timeline_path):
            try:
                with open(timeline_path, 'r', encoding='utf-8') as f:
                    timeline_data = json.load(f)
            except json.JSONDecodeError:
                st.warning("⚠️ **Timeline file exists but contains invalid JSON.** Skipping timeline data.")
            except Exception as e:
                st.warning(f"⚠️ **Could not load timeline data:** {str(e)}")
        
        # Clear loading message
        loading_placeholder.empty()
        
        # Show success message briefly
        success_placeholder = st.empty()
        time.sleep(5)
        success_placeholder.empty()
        
        return narrative_text, entities_data, summary_data, timeline_data, metadata
        
    except FileNotFoundError as e:
        loading_placeholder.empty()
        st.error(f"❌ **File not found:** {str(e)}")
        return None, None, None, None, None
    except json.JSONDecodeError as e:
        loading_placeholder.empty()
        st.error(f"❌ **Invalid JSON format:** {str(e)}")
        return None, None, None, None, None
    except PermissionError as e:
        loading_placeholder.empty()
        st.error(f"❌ **Permission denied:** {str(e)}")
        return None, None, None, None, None
    except Exception as e:
        loading_placeholder.empty()
        st.error(f"❌ **Unexpected error loading data:** {str(e)}")
        return None, None, None, None, None

def create_knowledge_graph(data):
    """Create a simple graph structure from entities and relationships data"""
    # We don't need networkx anymore since we're using vis.js directly
    # This function is kept for compatibility but simplified
    return data

def _get_hierarchy_level(entity, data):
    """Determine hierarchy level for better layout positioning"""
    entity_type = entity['type']
    if entity_type == 'actor':
        return 1  # Actors at center level
    elif entity_type == 'event':
        return 2  # Events around actors
    elif entity_type == 'factor':
        return 3  # Factors on the outside
    else:  # locations
        return 4  # Locations at the periphery

def create_visjs_graph(data):
    """Create an enhanced vis.js HTML visualization of the knowledge graph"""
    
    # Enhanced color mapping with better accessibility
    color_map = {
        'actor': {'background': '#4287f5', 'border': '#1e5daf', 'highlight': '#6ba3f7'},    # Blue
        'factor': {'background': '#dc3545', 'border': '#a71e2a', 'highlight': '#e3546b'},   # Red
        'event': {'background': '#28a745', 'border': '#1c7430', 'highlight': '#4cae5c'},    # Green
        'location': {'background': '#fd7e14', 'border': '#dc5c05', 'highlight': '#fd9843'}  # Orange
    }
    
    # Create nodes with enhanced styling
    nodes = []
    entity_counts = {'actor': 0, 'factor': 0, 'event': 0, 'location': 0}
    
    for i, entity in enumerate(data['entities']):
        entity_type = entity.get('type', 'unknown')
        if entity_type in entity_counts:
            entity_counts[entity_type] += 1
        
        # Create enhanced tooltip with better text wrapping and length limits
        description = entity.get('description', 'No description available')
        
        # Show full description without truncation as requested
        # Wrap long lines for better display (approximately 40 characters per line)
        def wrap_text(text, width=40):
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= width:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return '\n'.join(lines)
        
        wrapped_description = wrap_text(description)
        
        # Count connections for this entity (this determines importance)
        connection_count = sum(1 for rel in data.get('relationships', []) 
                             if rel.get('source') == entity['name'] or rel.get('target') == entity['name'])
        
        # Size nodes based ONLY on connection count (number of connections = importance)
        # More connections = more central/important = larger node
        base_size = 5   # Very small minimum size for nodes with 0 connections
        size_per_connection = 20  # Each connection adds 20 pixels (even more dramatic)
        node_size = base_size + (connection_count * size_per_connection)
        node_size = min(120, max(5, node_size))  # Keep between 5-120 pixels (much wider range)
        
        # Create type-specific emoji
        type_emoji = {'actor': '👤', 'factor': '⚙️', 'event': '📅', 'location': '📍'}.get(entity_type, '❓')
        
        # Create compact tooltip with connection count and importance
        simple_tooltip = f"{entity['name']} ({entity_type.title()})\n{wrapped_description}\nConnections: {connection_count}"
        
        nodes.append({
            'id': i,
            'label': entity['name'],
            'title': simple_tooltip,
            'color': color_map.get(entity_type, {'background': '#97C2FC', 'border': '#2B7CE9', 'highlight': '#D2E5FF'}),
            'value': node_size,  # Use ONLY value for vis.js automatic scaling
            'font': {
                'size': 16, 
                'color': '#2c3e50',
                'face': 'Roboto, Helvetica, sans-serif',
                'strokeWidth': 2,
                'strokeColor': 'white'
            },
            'borderWidth': 3,
            'shadow': {
                'enabled': True,
                'color': 'rgba(0,0,0,0.2)',
                'size': 10,
                'x': 2,
                'y': 2
            }
        })
    
    # Create node ID mapping
    name_to_id = {entity['name']: i for i, entity in enumerate(data['entities'])}
    
    # Create edges with enhanced styling
    edges = []
    relationship_counts = {}
    
    for rel in data.get('relationships', []):
        source_id = name_to_id.get(rel['source'])
        target_id = name_to_id.get(rel['target'])
        
        if source_id is not None and target_id is not None:
            mechanism = rel.get('mechanism', 'related to')
            strength = rel.get('strength', 0.5)
            
            # Count relationship types
            relationship_counts[mechanism] = relationship_counts.get(mechanism, 0) + 1
            
            # Edge width based on strength
            edge_width = max(1, min(5, int(strength * 5)))
            
            # Create enhanced edge tooltip
            description = rel.get('description', 'No description available')
            
            # Wrap long descriptions for better tooltip display
            if len(description) > 150:
                description = description[:150] + "..."
            
            # Enhanced edge tooltip with better formatting
            simple_edge_tooltip = f"Connection: {mechanism}\nFrom: {rel['source']}\nTo: {rel['target']}\nDescription: {description}\nStrength: {strength:.2f}"
            
            edges.append({
                'from': source_id,
                'to': target_id,
                'label': mechanism,
                'title': simple_edge_tooltip,
                'arrows': {'to': {'enabled': True, 'scaleFactor': 1.2}},
                'width': edge_width,
                'color': {
                    'color': '#666666',
                    'highlight': '#333333',
                    'hover': '#333333',
                    'inherit': False,
                    'opacity': 0.8
                },
                'smooth': {
                    'enabled': True,
                    'type': 'dynamic'
                },
                'font': {
                    'size': 12,
                    'color': '#2c3e50',
                    'face': 'Inter, Roboto, sans-serif',
                    'strokeWidth': 1,
                    'strokeColor': 'white'
                }
            })
    
    # Enhanced HTML with better controls and styling
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Knowledge Graph</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            html, body {{
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden; /* Prevents scrollbars inside the iframe */
            }}
            body {{
                font-family: 'Inter', 'Roboto', 'Helvetica Neue', sans-serif;
                background-color: #f8f9fa;
            }}
            
            #container {{
                width: 100%;
                height: 100%;
                position: relative;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            #mynetworkid {{
                width: 100%;
                height: 100%;
                border: none;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }}
            
            /* Enhanced tooltip styling */
            .vis-tooltip {{
                background: rgba(255, 255, 255, 0.98) !important;
                border: none !important;
                border-radius: 8px !important;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
                padding: 12px !important;
                font-family: 'Inter', 'Roboto', sans-serif !important;
                font-size: 13px !important;
                color: #2c3e50 !important;
                max-width: 400px !important;
                line-height: 1.4 !important;
                backdrop-filter: blur(10px) !important;
                -webkit-backdrop-filter: blur(10px) !important;
            }}
            
            .vis-tooltip::after {{
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: rgba(255, 255, 255, 0.98) transparent transparent transparent;
            }}
            
            #controls {{
                position: absolute;
                top: 10px;
                left: 10px;
                z-index: 1000;
                background: rgba(255,255,255,0.95);
                padding: 10px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
            }}
            
            #controls button {{
                margin: 2px;
                padding: 8px 12px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
                font-weight: bold;
                transition: all 0.3s ease;
            }}
            
            #controls button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            }}
            
            .btn-primary {{
                background: #007bff;
                color: white;
            }}
            
            .btn-secondary {{
                background: #6c757d;
                color: white;
            }}
            
            .btn-success {{
                background: #28a745;
                color: white;
            }}
            
            .btn-warning {{
                background: #ffc107;
                color: #212529;
            }}
            
            #legend {{
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: rgba(255,255,255,0.95);
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
                font-size: 12px;
                min-width: 150px;
            }}
            
            .legend-item {{
                display: flex;
                align-items: center;
                margin: 5px 0;
            }}
            
            .legend-color {{
                width: 16px;
                height: 16px;
                border-radius: 50%;
                margin-right: 8px;
                border: 2px solid #333;
            }}
            
            #stats {{
                position: absolute;
                bottom: 10px;
                left: 10px;
                z-index: 1000;
                background: rgba(255,255,255,0.95);
                padding: 10px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="controls">
                <button class="btn-primary" onclick="fitNetwork()">🔍 Fit All</button>
                <button class="btn-secondary" onclick="togglePhysics()">⚡ Physics</button>
                <button class="btn-success" onclick="resetLayout()">🔄 Reset</button>
                <button class="btn-warning" onclick="exportImage()">📸 Export</button>
            </div>
            
            <div id="legend">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50;">Node Types</h4>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #4287f5;"></div>
                    <span>Actors ({entity_counts['actor']})</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #dc3545;"></div>
                    <span>Factors ({entity_counts['factor']})</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #28a745;"></div>
                    <span>Events ({entity_counts['event']})</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #fd7e14;"></div>
                    <span>Locations ({entity_counts['location']})</span>
                </div>
            </div>
            
            <div id="stats">
                <h4 style="margin: 0 0 8px 0; color: #2c3e50;">Graph Stats</h4>
                <div><strong>Nodes:</strong> {len(nodes)}</div>
                <div><strong>Edges:</strong> {len(edges)}</div>
                <div><strong>Relationships:</strong> {len(relationship_counts)}</div>
            </div>
            
            <div id="mynetworkid"></div>
        </div>

        <script type="text/javascript">
            var nodes = new vis.DataSet({json.dumps(nodes)});
            var edges = new vis.DataSet({json.dumps(edges)});
            var data = {{nodes: nodes, edges: edges}};
            
            var options = {{
                physics: {{
                    enabled: true,
                    stabilization: {{iterations: 100}},
                    barnesHut: {{
                        gravitationalConstant: -3000,
                        centralGravity: 0.3,
                        springLength: 95,
                        springConstant: 0.04,
                        damping: 0.09,
                        avoidOverlap: 0.5
                    }}
                }},
                interaction: {{
                    hover: true,
                    hoverConnectedEdges: true,
                    selectConnectedEdges: false,
                    tooltipDelay: 200,
                    hideEdgesOnDrag: false,
                    hideNodesOnDrag: false,
                    multiselect: true,
                    navigationButtons: true,
                    keyboard: {{
                        enabled: true,
                        speed: {{x: 10, y: 10, zoom: 0.02}},
                        bindToWindow: false
                    }}
                }},
                nodes: {{
                    borderWidth: 2,
                    shadow: true,
                    font: {{
                        size: 16,
                        face: 'Inter, Roboto, sans-serif'
                    }},
                    scaling: {{
                        min: 10,
                        max: 50,
                        label: {{
                            enabled: false
                        }}
                    }},
                    chosen: false
                }},
                edges: {{
                    shadow: true,
                    smooth: {{
                        enabled: true,
                        type: 'dynamic'
                    }},
                    font: {{
                        size: 12,
                        face: 'Inter, Roboto, sans-serif'
                    }}
                }},
                layout: {{
                    improvedLayout: true,
                    randomSeed: 42
                }}
            }};
            
            var network = new vis.Network(document.getElementById('mynetworkid'), data, options);
            
            var physicsEnabled = true;
            
            function togglePhysics() {{
                physicsEnabled = !physicsEnabled;
                network.setOptions({{physics: {{enabled: physicsEnabled}}}});
                document.querySelector('button[onclick="togglePhysics()"]').innerText = 
                    physicsEnabled ? '⚡ Physics' : '⏸️ Static';
            }}
            
            function fitNetwork() {{
                network.fit({{
                    animation: {{
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }}
                }});
            }}
            
            function resetLayout() {{
                network.setData(data);
                network.redraw();
                setTimeout(() => fitNetwork(), 500);
            }}
            
            function exportImage() {{
                var canvas = network.canvas.frame.canvas;
                var link = document.createElement('a');
                link.download = 'knowledge-graph.png';
                link.href = canvas.toDataURL();
                link.click();
            }}
            
            // Auto-stabilize and fit on load
            network.once('stabilizationIterationsDone', function() {{
                setTimeout(() => {{
                    network.setOptions({{physics: {{enabled: false}}}});
                    physicsEnabled = false;
                    document.querySelector('button[onclick="togglePhysics()"]').innerText = '⏸️ Static';
                }}, 1000);
            }});
            
            // Handle node selection
            network.on('selectNode', function(params) {{
                if (params.nodes.length > 0) {{
                    var nodeId = params.nodes[0];
                    var node = nodes.get(nodeId);
                    console.log('Selected node:', node.label);
                }}
            }});
            
            // Handle edge selection
            network.on('selectEdge', function(params) {{
                if (params.edges.length > 0) {{
                    var edgeId = params.edges[0];
                    var edge = edges.get(edgeId);
                    console.log('Selected edge:', edge.label);
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content

def main():
    """Enhanced main Streamlit app with improved UI and error handling"""
    
    # Page header with enhanced styling
    st.markdown("""
    <div class="main-header">
        📰 News Article Storytelling Platform
        <br><small>Uncover the Stories Behind the Headlines</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data with progress indicator
    with st.spinner("🔄 Loading and processing data..."):
        narrative_text, entities_data, summary_data, timeline_data, metadata = load_data()
    
    if narrative_text is None or entities_data is None:
        st.markdown("""
        <div class="error-message">
            <h3>❌ Data Loading Failed</h3>
            <p>Unable to load the required data files. Please ensure:</p>
            <ul>
                <li>The narrative.txt file exists in the data/ directory</li>
                <li>The entities_article_0.json file exists in the output/ directory</li>
                <li>All files have proper read permissions</li>
            </ul>
            <p><strong>Need help?</strong> Check the file paths and run the entity extraction script first.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Success indicator with safe data access
    entities_count = len(entities_data.get('entities', [])) if isinstance(entities_data, dict) else 0
    relationships_count = len(entities_data.get('relationships', [])) if isinstance(entities_data, dict) else 0
    
    # Show success message that auto-disappears
    success_placeholder = st.empty()
    success_placeholder.markdown(f"""
    <div class="info-tip">
        ✅ <strong>Story loaded successfully!</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # Simple approach: sleep briefly and clear (without threading)
    time.sleep(1)
    success_placeholder.empty()
    
    # Enhanced sidebar with better organization
    with st.sidebar:
        st.markdown("### 📊 Story Dashboard")
        
        # Key metrics with enhanced styling
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="👥 Entities",
                value=entities_count,
                help="Key people, organizations, and places in this story"
            )
        with col2:
            st.metric(
                label="🔗 Connections", 
                value=relationships_count,
                help="Relationships and interactions between story elements"
            )
        
        if summary_data:
            col3, col4 = st.columns(2)
            with col3:
                st.metric(
                    label="📝 Story Length",
                    value=summary_data.get('word_count', 0),
                    help="Word count in the article summary"
                )
            with col4:
                if timeline_data and isinstance(timeline_data, dict):
                    event_count = timeline_data.get('event_count', 0)
                    if 'timeline' in timeline_data and isinstance(timeline_data['timeline'], list):
                        event_count = len(timeline_data['timeline'])
                    st.metric(
                        label="⏰ Key Events",
                        value=event_count,
                        help="Number of timeline events extracted"
                    )
                else:
                    st.metric(
                        label="⏰ Key Events",
                        value=0,
                        help="Timeline data not available"
                    )
        
        st.markdown("---")
        
        # Character type breakdown with enhanced visualization
        st.markdown("### 👥 Entities Types")
        entity_types = {}
        
        # Safely process entities
        entities_list = entities_data.get('entities', []) if isinstance(entities_data, dict) else []
        if not entities_list:
            st.warning("No entity data available for narrative conceptualization analysis.")
        else:
            for entity in entities_list:
                if isinstance(entity, dict) and 'type' in entity:
                    entity_type = entity['type']
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # Create a visual breakdown
        if entity_types:
            for entity_type, count in sorted(entity_types.items()):
                color_map = {
                    'actor': '🔵', 'factor': '🔴', 
                    'event': '🟢', 'location': '🟠'
                }
                icon = color_map.get(entity_type, '⚪')
                percentage = (count / len(entities_list)) * 100
                
                st.markdown(f"""
                <div class="metric-container">
                    {icon} <strong>{entity_type.title()}</strong>: {count} ({percentage:.1f}%)
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Story relationship analysis
        st.markdown("### 🔗 Story Connections")
        relationship_types = {}
        
        # Safely process relationships
        relationships_list = entities_data.get('relationships', []) if isinstance(entities_data, dict) else []
        if not relationships_list:
            st.info("No relationship data available for connection analysis.")
        else:
            for rel in relationships_list:
                if isinstance(rel, dict):
                    mechanism = rel.get('mechanism', 'unknown')
                    relationship_types[mechanism] = relationship_types.get(mechanism, 0) + 1
        
        # Show top relationship types
        if relationship_types:
            top_relationships = sorted(relationship_types.items(), key=lambda x: x[1], reverse=True)[:5]
            for mechanism, count in top_relationships:
                st.markdown(f"• **{mechanism}**: {count}")
            
            if len(relationship_types) > 5:
                with st.expander(f"View all {len(relationship_types)} story connection types"):
                    for mechanism, count in sorted(relationship_types.items()):
                        st.write(f"• {mechanism}: {count}")
    
    # Story Summary Section
    st.markdown("---")
    
    if summary_data:
        # Story Card with enhanced visual design
        if metadata:
            # Get all the data we need
            title = metadata.get('Title', 'No Title')
            source = metadata.get('Source', 'Unknown Source')
            section = metadata.get('Section', 'Unknown Section')
            pub_date = metadata.get('Publication Date', 'Unknown Date')[:10] if metadata.get('Publication Date') else 'Unknown Date'
            url = metadata.get('URL', '')
            image_url = metadata.get('Image', '')
            summary_text = summary_data.get('summary', 'No summary available')
            
            # Create the complete story card as one HTML block using st.components.v1.html for proper rendering
            story_card_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        font-family: 'Arial', sans-serif;
                        background: transparent;
                        min-height: 100vh;
                        box-sizing: border-box;
                    }}
                    .story-card {{
                        background: linear-gradient(145deg, #ffffff, #f8f9fa); 
                        border-radius: 16px; 
                        box-shadow: 0 8px 32px rgba(0,0,0,0.12); 
                        padding: 20px; 
                        margin: 5px 0; 
                        border: 1px solid #e3e6ea;
                        position: relative; 
                        overflow: hidden;
                        min-height: 320px;
                        box-sizing: border-box;
                    }}
                    .story-card::before {{
                        content: '';
                        position: absolute; 
                        top: 0; 
                        left: 0; 
                        width: 100%; 
                        height: 4px; 
                        background: linear-gradient(90deg, #007bff, #0056b3, #007bff);
                    }}
                    .card-content {{
                        display: flex; 
                        gap: 20px; 
                        align-items: flex-start;
                        min-height: 300px;
                    }}
                    .image-column {{
                        flex: 1; 
                        min-width: 0;
                        max-width: 300px;
                    }}
                    .image-container {{
                        position: relative; 
                        border-radius: 12px; 
                        overflow: hidden; 
                        box-shadow: 0 6px 20px rgba(0,0,0,0.15); 
                        border: 3px solid #ffffff;
                        margin-bottom: 10px;
                    }}
                    .article-image {{
                        width: 100%; 
                        height: auto; 
                        max-height: 250px;
                        object-fit: cover; 
                        transition: transform 0.3s ease;
                    }}
                    .placeholder-image {{
                        width: 100%; 
                        height: 200px; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        background: linear-gradient(135deg, #667eea, #764ba2); 
                        border-radius: 12px; 
                        border: 3px solid #ffffff; 
                        position: relative;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.15); 
                        margin-bottom: 10px;
                    }}
                    .placeholder-content {{
                        text-align: center; 
                        color: white;
                    }}
                    .content-column {{
                        flex: 2; 
                        min-width: 0;
                        display: flex;
                        flex-direction: column;
                        justify-content: space-between;
                    }}
                    .article-title {{
                        margin: 0 0 15px 0; 
                        color: #1a1a1a; 
                        line-height: 1.2; 
                        font-weight: 800; 
                        font-size: 1.5rem; 
                        font-family: 'Georgia', serif;
                        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    }}
                    .metadata {{
                        font-size: 12px; 
                        line-height: 1.4; 
                        margin: 12px 0; 
                        padding: 8px 12px; 
                        background: #f8f9fa; 
                        border-radius: 6px; 
                        border-left: 3px solid #007bff;
                    }}
                    .summary {{
                        line-height: 1.6; 
                        font-size: 14px; 
                        color: #495057; 
                        text-align: justify; 
                        margin: 12px 0; 
                        padding: 12px; 
                        background: #ffffff; 
                        border-radius: 6px; 
                        border-left: 3px solid #28a745; 
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        flex-grow: 1;
                    }}
                    .button-container {{
                        text-align: right; 
                        margin-top: 12px;
                        flex-shrink: 0;
                    }}
                    .read-more-btn {{
                        display: inline-flex; 
                        align-items: center; 
                        gap: 6px;
                        padding: 8px 16px; 
                        background: linear-gradient(135deg, #007bff, #0056b3); 
                        color: white; 
                        text-decoration: none; 
                        border-radius: 20px; 
                        font-weight: 600; 
                        font-size: 11px; 
                        white-space: nowrap;
                        box-shadow: 0 3px 10px rgba(0,123,255,0.3);
                        transition: all 0.3s ease; 
                        border: none;
                        text-transform: uppercase; 
                        letter-spacing: 0.5px;
                    }}
                    .read-more-btn:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 5px 15px rgba(0,123,255,0.4);
                    }}
                    
                    /* Responsive design for smaller screens */
                    @media (max-width: 768px) {{
                        .card-content {{
                            flex-direction: column;
                            gap: 15px;
                        }}
                        .image-column {{
                            max-width: 100%;
                        }}
                        .article-title {{
                            font-size: 1.3rem;
                        }}
                        .summary {{
                            font-size: 13px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="story-card">
                    <div class="card-content">
                        <!-- Image Column -->
                        <div class="image-column">
                            {f'''
                            <div class="image-container">
                                <img src="{image_url}" class="article-image" alt="Article Image">
                            </div>
                            ''' if image_url else '''
                            <div class="placeholder-image">
                                <div class="placeholder-content">
                                    <div style="font-size: 40px; margin-bottom: 8px;">📰</div>
                                    <div style="font-size: 12px; font-weight: 500; opacity: 0.9;">NEWS STORY</div>
                                </div>
                                <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; 
                                            background: linear-gradient(45deg, rgba(255,255,255,0.1), transparent);"></div>
                            </div>
                            '''}
                        </div>
                        
                        <!-- Content Column -->
                        <div class="content-column">
                            <!-- Title -->
                            <h1 class="article-title">{title}</h1>
                            
                            <!-- Metadata -->
                            <div class="metadata">
                                <strong style="color: #495057;">🏢 Source:</strong> <span style="color: #6c757d;">{source}</span> • 
                                <strong style="color: #495057;">📂 Section:</strong> <span style="color: #6c757d;">{section}</span> • 
                                <strong style="color: #495057;">📅 Published:</strong> <span style="color: #6c757d;">{pub_date}</span>
                            </div>
                            
                            <!-- Summary -->
                            <div class="summary">{summary_text}</div>
                            
                            <!-- Button -->
                            {f'''
                            <div class="button-container">
                                <a href="{url}" target="_blank" class="read-more-btn">
                                    <span style="font-size: 13px;">📖</span>
                                    <span>Read Full Article</span>
                                </a>
                            </div>
                            ''' if url else ''}
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Use st.components.v1.html for proper HTML rendering with optimized height
            components.html(story_card_html, height=400)

    else:
        st.info("No summary data available to display.")
    
    st.markdown("---")
    
    # Story exploration navigation
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0 1.5rem 0; position: relative;">
        <div style="position: absolute; top: 50%; left: 0; right: 0; height: 1px; 
                    background: linear-gradient(90deg, transparent, #dee2e6, transparent);"></div>
        <h2 style="background: #f8f9fa; padding: 0 20px; margin: 0; font-size: 1.5rem; 
                   font-weight: 700; color: #2c3e50; display: inline-block; position: relative;
                   border-radius: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            📊 Explore the Story
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation with enhanced styling
    view_option = st.radio(
        "Choose your exploration view:",
        ["⏰ Story Timeline", "🕸️ Narrative Conceptualization"],
        horizontal=True,
        key="view_selector",
        help="Select how you want to explore this story"
    )
    
    if view_option == "⏰ Story Timeline":
        
        if timeline_data and timeline_data.get('timeline'):
            # Get publication date as origin point
            publication_date = None
            if metadata and 'Publication Date' in metadata:
                publication_date = metadata['Publication Date'][:10]  # Extract date part
            
            # Timeline statistics
            st.markdown(f"""
            <div class="info-tip">
                📈 <strong>Story Progression:</strong> {timeline_data.get('event_count', 0)} key events that shaped this narrative
                {f'<br>🎯 <strong>Origin Point:</strong> Article published on {publication_date}' if publication_date else ''}
            </div>
            """, unsafe_allow_html=True)
            
            # Add color legend
            st.markdown("""
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <h4 style="margin: 0 0 0.5rem 0; color: #2c3e50; font-size: 1rem;">📋 Timeline Legend</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 1rem; font-size: 0.9rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="width: 16px; height: 16px; background: #6c757d; border-radius: 3px;"></div>
                        <span>⏮️ Before (Past events)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="width: 16px; height: 16px; background: #dc3545; border-radius: 3px;"></div>
                        <span>📰 Origin (Publication date)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="width: 16px; height: 16px; background: #28a745; border-radius: 3px;"></div>
                        <span>⏭️ After (Future events)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="width: 16px; height: 16px; background: #17a2b8; border-radius: 3px;"></div>
                        <span>📍 During (Same date events)</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Sort timeline events by date
            sorted_events = sorted(timeline_data['timeline'], key=lambda x: x.get('Date', ''))
            
            # Create a combined timeline with origin point inserted at the right position
            timeline_items = []
            
            # Add all events to timeline
            for event in sorted_events:
                timeline_items.append({
                    'type': 'event',
                    'data': event,
                    'date': event.get('Date', 'Unknown Date')
                })
            
            # Add origin point if we have publication date
            if publication_date:
                # Convert publication date to same format as events (YYYY/MM/DD)
                pub_date_formatted = publication_date.replace('-', '/')
                timeline_items.append({
                    'type': 'origin',
                    'data': {
                        'Date': pub_date_formatted,
                        'Title': 'Article Publication Origin',
                        'Text': 'This is the anchor point when the story was reported. Events flow from this moment.'
                    },
                    'date': pub_date_formatted
                })
            
            # Sort all timeline items by date
            timeline_items.sort(key=lambda x: x['date'])
            
            # Display timeline items in chronological order
            for i, item in enumerate(timeline_items):
                if item['type'] == 'origin':
                    # Display origin point (no indentation) - only date and title
                    st.markdown(f"""
                    <div class="timeline-origin" style="margin: 1rem 0;">
                        <div style="display: flex; align-items: center; gap: 1rem; padding: 1rem; 
                                    background: linear-gradient(135deg, #fff5f5, #ffe6e6); 
                                    border-left: 4px solid #dc3545; border-radius: 8px;
                                    box-shadow: 0 2px 8px rgba(220, 53, 69, 0.2);">
                            <div style="background: #dc3545; color: white; padding: 0.5rem 1rem; 
                                        border-radius: 20px; font-weight: bold; min-width: 120px; text-align: center;">
                                {item['data']['Date']}
                            </div>
                            <div style="flex: 1;">
                                <h4 style="margin: 0; color: #dc3545; font-weight: 700; font-size: 1.1rem;">
                                    📰 {item['data']['Title']}
                                </h4>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add expander for origin details
                    with st.expander("📖 View Details", expanded=False):
                        st.markdown(f"**Description:**")
                        st.markdown(f"{item['data']['Text']}")
                        
                        st.markdown(f"**Timeline Position:** Origin/Anchor point")
                        
                        st.markdown(f"**Source:** Article publication date")
                else:
                    # Display event (indented to the right)
                    event = item['data']
                    event_date = event.get('Date', 'Unknown Date')
                    
                    # Determine event color and icon based on timeline position
                    date_color = "#17a2b8"  # Default blue for "during"
                    timeline_position = "during"
                    position_icon = "📍"
                    
                    if publication_date and event_date != 'Unknown Date':
                        try:
                            # Parse dates for comparison
                            event_dt = datetime.strptime(event_date, '%Y/%m/%d')
                            pub_dt = datetime.strptime(publication_date, '%Y-%m-%d')
                            
                            if event_dt < pub_dt:
                                timeline_position = "before"
                                date_color = "#6c757d"  # Gray for before events
                                position_icon = "⏮️"
                            elif event_dt > pub_dt:
                                timeline_position = "after"
                                date_color = "#28a745"  # Green for after events
                                position_icon = "⏭️"
                            else:
                                timeline_position = "during"
                                date_color = "#17a2b8"  # Blue for during events
                                position_icon = "📍"
                        except:
                            pass
                    
                    # Add indentation to show events flow from origin (2rem indent)
                    event_container = st.container()
                    with event_container:
                        # Create indented columns for consistent layout
                        col_spacer, col_content = st.columns([0.125, 0.875])  # Match the 2rem indent
                        
                        with col_content:
                            # Show only date and title prominently, with details in expander
                            st.markdown(f"""
                            <div class="timeline-event" style="margin: 1rem 0;">
                                <div style="display: flex; align-items: center; gap: 1rem; padding: 1rem; 
                                            background: #f8f9fa; border-radius: 8px; border-left: 4px solid {date_color};
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                    <div style="background: {date_color}; color: white; padding: 0.5rem 1rem; 
                                                border-radius: 20px; font-weight: bold; min-width: 120px; text-align: center;">
                                        {event_date}
                                    </div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0; color: #2c3e50; font-size: 1.1rem;">
                                            {position_icon} {event.get('Title', 'Untitled Event')}
                                        </h4>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # All details in an expandable section
                            with st.expander("📖 View Details", expanded=False):
                                st.markdown(f"**Event Description:**")
                                st.markdown(f"{event.get('Text', 'No description available')}")
                                
                                st.markdown(f"**Timeline Position:** {timeline_position.title()} event")
                                
                                st.markdown(f"**Source:**")
                                st.markdown(f"*\"{event.get('Source', 'No source available')}\"*")
                
                # Add spacing between items except for the last one
                if i < len(timeline_items) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="error-message">
                ⚠️ <strong>Timeline data not available.</strong> 
                Please run the timeline generation script to extract the chronological story events.
                <br><br>
                <em>This feature reveals how the story unfolds over time, showing the sequence of events that drive the narrative forward.</em>
            </div>
            """, unsafe_allow_html=True)
    
    elif view_option == "🕸️ Narrative Conceptualization":
        
        st.markdown("""
        <div class="info-tip">
            💡 <strong>Interactive Story Map:</strong> 
            • Explore entities relationships • Zoom and pan to navigate • Hover for entities details 
            • Use the controls to customize your view
        </div>
        """, unsafe_allow_html=True)
        
        # Create and display the enhanced vis.js graph
        with st.spinner("🔄 Mapping entity relationships..."):
            html_content = create_visjs_graph(entities_data)
        
        # Display the interactive graph using HTML component
        components.html(html_content, height=900)
        
        # # Enhanced character details section
        # st.markdown("---")
        # st.markdown("""
        # <div style="margin: 1.5rem 0 1rem 0;">
        #     <h3 style="color: #2c3e50; margin: 0; font-size: 1.3rem; font-weight: 600;">
        #         📋 Entities Profiles & Story Elements
        #     </h3>
        # </div>
        # """, unsafe_allow_html=True)
        
        # # Character type tabs for better organization
        # character_tabs = st.tabs(["👥 Actors", "🎯 Factors", "🎬 Events", "🗺️ Locations"])
        
        # character_types = {
        #     'actor': ('👥 Actors', 'Main actorss, organizations, and influential figures'),
        #     'factor': ('🎯 Factors', 'Underlying causes and motivating factors'),
        #     'event': ('🎬 Events', 'Significant happenings and turning points'),
        #     'location': ('🗺️ Locations', 'Important places where the story unfolds')
        # }
        
        # for idx, (entity_type, (title, description)) in enumerate(character_types.items()):
        #     with character_tabs[idx]:
        #         entities_of_type = [e for e in entities_data['entities'] if e['type'] == entity_type]
                
        #         if entities_of_type:
        #             st.markdown(f"**{description}** ({len(entities_of_type)} total)")
        #             st.markdown("---")
                    
        #             # Create columns for better layout
        #             cols = st.columns(2)
        #             for i, entity in enumerate(entities_of_type):
        #                 with cols[i % 2]:
        #                     with st.expander(f"**{entity['name']}**", expanded=False):
        #                         st.markdown(f"**Role:** {entity['type'].title()}")
        #                         st.markdown(f"**Story Impact:** {entity.get('description', 'No description available')}")
                                
        #                         # Show related connections
        #                         related_rels = [
        #                             rel for rel in entities_data['relationships'] 
        #                             if rel['source'] == entity['name'] or rel['target'] == entity['name']
        #                         ]
                                
        #                         if related_rels:
        #                             st.markdown("**Story Connections:**")
        #                             for rel in related_rels[:3]:  # Show top 3 relationships
        #                                 if rel['source'] == entity['name']:
        #                                     st.markdown(f"→ {rel['mechanism']} → **{rel['target']}**")
        #                                 else:
        #                                     st.markdown(f"**{rel['source']}** → {rel['mechanism']} → ")
                                    
        #                             if len(related_rels) > 3:
        #                                 st.markdown(f"*... and {len(related_rels) - 3} more connections*")
        #         else:
        #             st.info(f"No {entity_type}s found in this story.")
        
        # # Enhanced story connections analysis
        # st.markdown("---")
        # st.markdown("""
        # <div style="margin: 1.5rem 0 1rem 0;">
        #     <h3 style="color: #2c3e50; margin: 0; font-size: 1.3rem; font-weight: 600;">
        #         🔗 Story Network Analysis
        #     </h3>
        # </div>
        # """, unsafe_allow_html=True)
        
        # # Story connection statistics
        # if entities_data['relationships']:
        #     col1, col2, col3 = st.columns(3)
            
        #     with col1:
        #         st.metric("Total Connections", len(entities_data['relationships']))
            
        #     with col2:
        #         unique_mechanisms = len(set(rel['mechanism'] for rel in entities_data['relationships']))
        #         st.metric("Connection Types", unique_mechanisms)
            
        #     with col3:
        #         avg_strength = sum(rel.get('strength', 0.5) for rel in entities_data['relationships']) / len(entities_data['relationships'])
        #         st.metric("Avg. Story Impact", f"{avg_strength:.2f}")
            
        #     st.markdown("---")
            
        #     # Enhanced story connections table with filtering
        #     st.markdown("**🔍 Explore Story Connections:**")
            
        #     # Filter options
        #     col_filter1, col_filter2 = st.columns(2)
        #     with col_filter1:
        #         mechanism_filter = st.selectbox(
        #             "Filter by connection type:",
        #             ["All"] + sorted(list(set(rel['mechanism'] for rel in entities_data['relationships'])))
        #         )
            
        #     with col_filter2:
        #         strength_filter = st.slider("Minimum story impact:", 0.0, 1.0, 0.0, 0.1)
            
        #     # Filter and display connections
        #     filtered_relationships = []
        #     for rel in entities_data['relationships']:
        #         if (mechanism_filter == "All" or rel['mechanism'] == mechanism_filter) and \
        #            rel.get('strength', 0.5) >= strength_filter:
        #             filtered_relationships.append({
        #                 'From': rel['source'],
        #                 'Connection': rel['mechanism'],
        #                 'To': rel['target'],
        #                 'Impact': f"{rel.get('strength', 0.5):.2f}",
        #                 'Story Role': rel.get('description', 'No description')[:100] + "..." if len(rel.get('description', '')) > 100 else rel.get('description', 'No description')
        #             })
            
        #     if filtered_relationships:
        #         st.dataframe(
        #             filtered_relationships, 
        #             use_container_width=True,
        #             height=300
        #         )
        #         st.caption(f"Showing {len(filtered_relationships)} of {len(entities_data['relationships'])} total story connections")
        #     else:
        #         st.info("No story connections match the current filters. Try adjusting the criteria.")
        # else:
        #     st.warning("No story connection data available.")

if __name__ == "__main__":
    main()
