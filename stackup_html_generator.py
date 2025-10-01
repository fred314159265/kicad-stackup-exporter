"""
KiCAD Stackup HTML Generator
Generates an interactive HTML visualization of PCB stackup data
"""

import json
import sys
import os


def prettify_layer_name(layer_name):
    """
    Convert KiCAD layer names to more readable, standardized names

    Args:
        layer_name: Original layer name from KiCAD

    Returns:
        str: Prettified layer name
    """
    name_map = {
        "F.SilkS": "Top Silkscreen",
        "B.SilkS": "Bottom Silkscreen",
        "F.Mask": "Top Soldermask",
        "B.Mask": "Bottom Soldermask",
        "F.Paste": "Top Solder Paste",
        "B.Paste": "Bottom Solder Paste",
        "F.Cu": "Top Copper",
        "B.Cu": "Bottom Copper",
        "F.Adhes": "Top Adhesive",
        "B.Adhes": "Bottom Adhesive",
        "F.CrtYd": "Top Courtyard",
        "B.CrtYd": "Bottom Courtyard",
        "F.Fab": "Top Fabrication",
        "B.Fab": "Bottom Fabrication",
        "Edge.Cuts": "Board Outline",
        "Margin": "Margin",
        "Dwgs.User": "User Drawings",
        "Cmts.User": "User Comments",
    }

    # Check direct mapping first
    if layer_name in name_map:
        return name_map[layer_name]

    # Handle inner copper layers (In1.Cu, In2.Cu, etc.)
    if ".Cu" in layer_name and layer_name.startswith("In"):
        layer_num = layer_name.replace("In", "").replace(".Cu", "")
        return f"Inner Copper Layer {layer_num}"

    # Handle dielectric layers
    if "dielectric" in layer_name.lower():
        import re
        match = re.search(r'(\d+)', layer_name)
        if match:
            return f"Dielectric {match.group(1)}"

    # Return original if no mapping found
    return layer_name


def generate_html(stackup_data, output_html_path):
    """
    Generate an HTML visualization of the stackup data

    Args:
        stackup_data: Dictionary containing stackup information
        output_html_path: Path to save the HTML file
    """

    board_name = stackup_data.get("board_name", "Unknown")
    export_date = stackup_data.get("export_date", "Unknown")
    board_thickness = stackup_data.get("board_thickness_mm", 0)
    copper_count = stackup_data.get("copper_layer_count", 0)
    copper_finish = stackup_data.get("copper_finish", "N/A")
    dielectric_constraints = stackup_data.get("dielectric_constraints")
    edge_connector = stackup_data.get("edge_connector")
    castellated_pads = stackup_data.get("castellated_pads")
    edge_plating = stackup_data.get("edge_plating")
    layers = stackup_data.get("layers", [])

    # Calculate proportional heights for visualization
    total_thickness = sum(
        layer.get("thickness", {}).get("mm", 0)
        for layer in layers if "thickness" in layer
    )

    # Generate layer HTML blocks
    layers_html = ""
    for idx, layer in enumerate(layers):
        layer_name = prettify_layer_name(layer.get("layer_name", f"Layer {idx}"))
        layer_type = layer.get("type", "unknown")
        thickness_data = layer.get("thickness", {})
        thickness_mm = thickness_data.get("mm", 0)
        thickness_mils = thickness_data.get("mils", 0)
        thickness_um = thickness_data.get("um", 0)
        material = layer.get("material", "")
        color = layer.get("color", "")
        epsilon_r = layer.get("epsilon_r", "")
        loss_tangent = layer.get("loss_tangent", "")

        # Calculate proportional height for visualization (min 8px, max based on thickness)
        if total_thickness > 0 and thickness_mm > 0:
            # Use logarithmic scale for better visualization of thin layers
            height_px = max(8, min(120, 8 + (thickness_mm / total_thickness) * 180))
        else:
            height_px = 8

        # Determine layer color for visualization
        bg_color = "#888"

        # Check if layer has a color specified
        layer_color = layer.get("color", "")
        color_matched = False

        if layer_color:
            # Handle color codes (starting with #)
            if layer_color.startswith("#"):
                # Remove alpha channel if present (8-digit hex like #1E1A80D4)
                if len(layer_color) == 9:
                    bg_color = layer_color[:7]  # Take first 7 chars (#RRGGBB)
                else:
                    bg_color = layer_color
                color_matched = True
            # Handle named colors (for silkscreen and soldermask)
            elif layer_color.lower() == "purple":
                bg_color = "#800080"
                color_matched = True
            elif layer_color.lower() == "green":
                bg_color = "#2d5016"  # Dark green for soldermask
                color_matched = True
            elif layer_color.lower() == "red":
                bg_color = "#8B0000"
                color_matched = True
            elif layer_color.lower() == "blue":
                bg_color = "#0000CD"
                color_matched = True
            elif layer_color.lower() == "black":
                bg_color = "#1a1a1a"
                color_matched = True
            elif layer_color.lower() == "white":
                bg_color = "#f0f0f0"
                color_matched = True
            elif layer_color.lower() == "yellow":
                bg_color = "#FFD700"
                color_matched = True
            # Handle material-based color names (for dielectrics)
            elif "ptfe" in layer_color.lower() or "teflon" in layer_color.lower():
                bg_color = "#f5f5f0"  # Almost perfect white (PTFE natural)
                color_matched = True
            elif "polyimide" in layer_color.lower() or "kapton" in layer_color.lower():
                bg_color = "#cc7722"  # Darkish orange (Polyimide)
                color_matched = True
            elif "phenolic" in layer_color.lower():
                bg_color = "#8b4513"  # Reddish brown (Phenolic natural)
                color_matched = True
            elif "alumin" in layer_color.lower() or "metal" in layer_color.lower():
                bg_color = "#b0b0b0"  # Aluminum looking silver/grey
                color_matched = True
            elif "fr4" in layer_color.lower() or "fr-4" in layer_color.lower():
                bg_color = "#d4c5a0"  # FR4 fiberglass looking color (beige/tan)
                color_matched = True

        # Fall back to defaults if no color matched or not specified
        if not color_matched:
            if "copper" in layer_type.lower() or "cu" in layer_name.lower():
                bg_color = "#d4af37"  # Gold
            elif "dielectric" in layer_type.lower() or "core" in layer_type.lower() or "prepreg" in layer_type.lower():
                # Determine dielectric color based on material
                material_lower = material.lower() if material else ""

                if "ptfe" in material_lower or "teflon" in material_lower:
                    bg_color = "#f5f5f0"  # Almost perfect white (PTFE natural)
                elif "polyimide" in material_lower or "kapton" in material_lower:
                    bg_color = "#cc7722"  # Darkish orange (Polyimide)
                elif "phenolic" in material_lower:
                    bg_color = "#8b4513"  # Reddish brown (Phenolic natural)
                elif "alumin" in material_lower or "metal" in material_lower:
                    bg_color = "#b0b0b0"  # Aluminum looking silver/grey
                elif "fr4" in material_lower or "fr-4" in material_lower or not material:
                    bg_color = "#d4c5a0"  # FR4 fiberglass looking color (beige/tan)
                else:
                    # Custom or unspecified - use FR4 default
                    bg_color = "#d4c5a0"  # FR4 fiberglass looking color
            elif "mask" in layer_type.lower():
                bg_color = "#2d5016"  # Dark green (default soldermask)
            elif "silk" in layer_type.lower():
                bg_color = "#f0f0f0"  # White (default silkscreen)
            elif "paste" in layer_type.lower():
                bg_color = "#c0c0c0"  # Silver

        thickness_text = ""
        if thickness_mm > 0:
            thickness_text = f"{thickness_mm} mm ({thickness_mils} mils)"

        # Build details HTML
        details_html = ""
        # Determine if this is a dielectric layer
        is_dielectric = "dielectric" in layer_type.lower() or "core" in layer_type.lower() or "prepreg" in layer_type.lower()

        if material:
            details_html += f"<div><strong>Material:</strong> {material}</div>"
        # Only show color for non-dielectric layers (silkscreen, soldermask, etc.)
        if color and not is_dielectric:
            details_html += f"<div><strong>Color:</strong> {color}</div>"
        if epsilon_r:
            details_html += f"<div><strong>εᵣ:</strong> {epsilon_r}</div>"
        if loss_tangent:
            details_html += f"<div><strong>Loss Tangent:</strong> {loss_tangent}</div>"

        # Build comprehensive tooltip with all details
        tooltip_parts = [layer_name, layer_type]
        if material:
            tooltip_parts.append(f"Material: {material}")
        if thickness_text:
            tooltip_parts.append(f"Thickness: {thickness_text}")
        if epsilon_r:
            tooltip_parts.append(f"εᵣ: {epsilon_r}")
        if loss_tangent:
            tooltip_parts.append(f"Loss Tangent: {loss_tangent}")
        tooltip = " | ".join(tooltip_parts)

        # Build single line info: thickness (all), material (all), color (silkscreen/soldermask only)
        info_parts = []
        if thickness_text:
            info_parts.append(thickness_text)
        if material:
            info_parts.append(material)
        # Only show color for silkscreen and soldermask layers
        is_silkscreen = "silkscreen" in layer_type.lower() or "silk" in layer_name.lower()
        is_soldermask = "soldermask" in layer_type.lower() or "mask" in layer_name.lower()
        if color and (is_silkscreen or is_soldermask):
            info_parts.append(color)

        info_line = " | ".join(info_parts)

        # Determine info text color based on background brightness
        # Layer name stays white (has shadow), but info text needs to adapt
        def is_very_light_color(hex_color):
            """Check if a hex color is very light (needs dark text for readability)"""
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness > 200

        info_text_color = "#000000" if is_very_light_color(bg_color) else "#ffffff"

        layers_html += f"""
        <div class="layer" style="height: {height_px}px; background-color: {bg_color};" title="{tooltip}">
            <div class="layer-label">
                <span class="layer-name" style="color: #ffffff;">{layer_name}</span>
            </div>
            <div class="layer-info" style="color: {info_text_color};">
                <div class="layer-thickness">{info_line}</div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCB Stackup - {board_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
        }}

        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}

        .header-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .info-card {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}

        .info-card-label {{
            font-size: 12px;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .info-card-value {{
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }}

        .content {{
            display: flex;
            flex-wrap: wrap;
        }}

        .visualization {{
            flex: 1;
            min-width: 300px;
            padding: 30px;
            background: #f8f9fa;
        }}

        .stackup-visual {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .layer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 7.5px 15px;
            border-bottom: 1px solid rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
            min-height: 30px;
        }}

        .layer:hover {{
            transform: translateX(5px);
            box-shadow: inset 5px 0 0 rgba(255,255,255,0.3);
            z-index: 10;
        }}

        .layer-label {{
            display: flex;
            flex-direction: row;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
            z-index: 1;
        }}

        .layer-name {{
            font-weight: bold;
            font-size: 14px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            white-space: nowrap;
        }}

        .layer-type {{
            font-size: 11px;
            color: rgba(255,255,255,0.8);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }}

        .layer-info {{
            text-align: right;
            font-size: 11px;
            z-index: 1;
            white-space: nowrap;
        }}

        .layer-thickness {{
            font-weight: bold;
            margin-bottom: 5px;
            font-size: 12px;
        }}

        .layer-info div {{
            margin: 2px 0;
            opacity: 0.9;
        }}

        .layer-thin {{
            font-size: 11px;
        }}

        .layer-thin .layer-name {{
            font-size: 12px;
        }}

        .layer-thickness-compact {{
            font-size: 10px;
            font-weight: normal;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .details {{
            flex: 1;
            min-width: 350px;
            padding: 30px;
        }}

        .details h2 {{
            font-size: 22px;
            margin-bottom: 20px;
            color: #1e3c72;
        }}

        .layer-list {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}

        .layer-detail-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
        }}

        .layer-detail-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .layer-detail-name {{
            font-size: 18px;
            font-weight: bold;
            color: #1e3c72;
            margin-bottom: 8px;
        }}

        .layer-detail-type {{
            color: #667eea;
            font-size: 14px;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .layer-detail-properties {{
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 8px 15px;
            font-size: 14px;
        }}

        .property-label {{
            font-weight: 600;
            color: #555;
        }}

        .property-value {{
            color: #333;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }}

        @media (max-width: 768px) {{
            .content {{
                flex-direction: column;
            }}

            .header-info {{
                grid-template-columns: 1fr;
            }}
        }}

        /* Print styles */
        @media print {{
            @page {{
                margin: 1cm;
                size: A4 portrait;
            }}

            body {{
                background: white !important;
                padding: 0;
                margin: 0;
            }}

            .container {{
                box-shadow: none;
                border-radius: 0;
                max-width: 100%;
                margin: 0;
            }}

            .header {{
                background: #1e3c72 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                color-adjust: exact;
                page-break-after: avoid;
                padding: 20px !important;
            }}

            .header h1 {{
                font-size: 24px !important;
            }}

            .header-info {{
                grid-template-columns: repeat(3, 1fr) !important;
                gap: 10px !important;
            }}

            .info-card {{
                background: rgba(255,255,255,0.15) !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                color-adjust: exact;
                padding: 10px !important;
            }}

            .info-card-value {{
                font-size: 18px !important;
            }}

            .export-buttons {{
                display: none !important;
            }}

            .content {{
                display: block !important;
            }}

            .visualization {{
                width: 100% !important;
                padding: 15px !important;
                page-break-after: always;
                page-break-inside: avoid;
            }}

            .visualization h2 {{
                font-size: 16px !important;
                margin-bottom: 10px !important;
            }}

            .stackup-visual {{
                max-height: 70vh;
                overflow: visible;
            }}

            .layer {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                color-adjust: exact;
                border-bottom: 1px solid rgba(0,0,0,0.2) !important;
                page-break-inside: avoid;
                padding: 5px 15px !important;
                min-height: 30px !important;
            }}

            .layer-name {{
                font-size: 11px !important;
            }}

            .layer-info {{
                font-size: 9px !important;
            }}

            .layer:hover {{
                transform: none;
                box-shadow: none;
            }}

            .details {{
                width: 100% !important;
                padding: 20px !important;
                page-break-before: auto;
            }}

            .details h2 {{
                font-size: 18px !important;
                margin-bottom: 15px !important;
                page-break-after: avoid;
            }}

            .layer-detail-card {{
                page-break-inside: avoid;
                margin-bottom: 10px !important;
                padding: 10px !important;
            }}

            .layer-detail-name {{
                font-size: 14px !important;
            }}

            .layer-detail-type {{
                font-size: 12px !important;
            }}

            .layer-detail-properties {{
                font-size: 11px !important;
            }}

            .footer {{
                page-break-before: avoid;
                padding: 15px !important;
                font-size: 10px !important;
            }}
        }}

        .export-buttons {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
            justify-content: center;
        }}

        .export-btn {{
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .export-btn-secondary {{
            background: #ffffff;
            color: #667eea;
            border: 2px solid #667eea;
        }}

        .export-btn-secondary:hover {{
            background: #667eea;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{board_name}</h1>
            <div class="header-info">
                <div class="info-card">
                    <div class="info-card-label">Board Thickness</div>
                    <div class="info-card-value">{board_thickness} mm</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Copper Layers</div>
                    <div class="info-card-value">{copper_count}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Copper Finish</div>
                    <div class="info-card-value" style="font-size: 18px;">{copper_finish}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Total Layers</div>
                    <div class="info-card-value">{len(layers)}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Impedance Controlled</div>
                    <div class="info-card-value" style="font-size: 18px;">{"Yes" if dielectric_constraints else "No"}</div>
                </div>
                {f'''<div class="info-card">
                    <div class="info-card-label">Edge Connector</div>
                    <div class="info-card-value" style="font-size: 18px;">{edge_connector.capitalize()}</div>
                </div>''' if edge_connector else ''}
                <div class="info-card">
                    <div class="info-card-label">Castellated Pads</div>
                    <div class="info-card-value" style="font-size: 18px;">{"Yes" if castellated_pads else "No"}</div>
                </div>
                <div class="info-card">
                    <div class="info-card-label">Edge Plating</div>
                    <div class="info-card-value" style="font-size: 18px;">{"Yes" if edge_plating else "No"}</div>
                </div>
            </div>
        </div>

        <div class="content">
            <div class="visualization">
                <h2 style="margin-bottom: 20px; color: #1e3c72;">Stackup Visualization</h2>
                <div class="stackup-visual">
                    {layers_html}
                </div>
            </div>

            <div class="details">
                <h2>Layer Details</h2>
                <div class="layer-list">
"""

    # Add detailed layer cards
    for idx, layer in enumerate(layers):
        layer_name = prettify_layer_name(layer.get("layer_name", f"Layer {idx}"))
        layer_type = layer.get("type", "unknown")
        thickness_data = layer.get("thickness", {})
        material = layer.get("material", "")
        color = layer.get("color", "")
        epsilon_r = layer.get("epsilon_r", "")
        loss_tangent = layer.get("loss_tangent", "")

        # Determine if this is a dielectric layer
        is_dielectric = "dielectric" in layer_type.lower() or "core" in layer_type.lower() or "prepreg" in layer_type.lower()

        properties_html = ""

        if thickness_data:
            thickness_mm = thickness_data.get("mm", 0)
            thickness_mils = thickness_data.get("mils", 0)
            thickness_um = thickness_data.get("um", 0)
            if thickness_mm > 0:
                properties_html += f"""
                    <div class="property-label">Thickness:</div>
                    <div class="property-value">{thickness_mm} mm ({thickness_mils} mils / {thickness_um} μm)</div>
                """

        if material:
            properties_html += f"""
                <div class="property-label">Material:</div>
                <div class="property-value">{material}</div>
            """

        # Only show color for non-dielectric layers
        if color and not is_dielectric:
            properties_html += f"""
                <div class="property-label">Color:</div>
                <div class="property-value">{color}</div>
            """

        if epsilon_r:
            properties_html += f"""
                <div class="property-label">Dielectric Constant (εᵣ):</div>
                <div class="property-value">{epsilon_r}</div>
            """

        if loss_tangent:
            properties_html += f"""
                <div class="property-label">Loss Tangent (tan δ):</div>
                <div class="property-value">{loss_tangent}</div>
            """

        # Only show the layer type subtitle if there are actual properties AND it's not redundant
        # Skip type if it just says "copper", "Top/Bottom Silk Screen", or "Top/Bottom Solder Mask"
        redundant_types = ["copper", "top silk screen", "bottom silk screen",
                          "top solder mask", "bottom solder mask",
                          "top solder paste", "bottom solder paste"]
        is_redundant = layer_type.lower() in redundant_types
        show_type = bool(properties_html) and not is_redundant

        html_content += f"""
                    <div class="layer-detail-card">
                        <div class="layer-detail-name">{layer_name}</div>
                        {f'<div class="layer-detail-type">{layer_type}</div>' if show_type else ''}
                        <div class="layer-detail-properties">
                            {properties_html if properties_html else '<div style="grid-column: 1/-1; color: #999;">No additional properties</div>'}
                        </div>
                    </div>
        """

    html_content += f"""
                </div>
            </div>
        </div>

        <div class="footer">
            Generated on {export_date} | KiCAD Stackup Exporter
        </div>

        <div class="export-buttons">
            <button class="export-btn export-btn-secondary" onclick="window.print()">
                🖨️ Print / Save as PDF
            </button>
        </div>
    </div>
</body>
</html>
"""

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def main():
    """Command-line interface for HTML generation"""
    if len(sys.argv) < 2:
        print("KiCAD Stackup HTML Generator")
        print("\nUsage:")
        print(f"  python {os.path.basename(__file__)} <stackup.json> [output.html]")
        print("\nExample:")
        print(f"  python {os.path.basename(__file__)} board_stackup.json board_stackup.html")
        sys.exit(1)

    input_json = sys.argv[1]

    if not os.path.exists(input_json):
        print(f"Error: File not found: {input_json}")
        sys.exit(1)

    # Determine output file
    if len(sys.argv) >= 3:
        output_html = sys.argv[2]
    else:
        output_html = os.path.splitext(input_json)[0] + ".html"

    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            stackup_data = json.load(f)

        generate_html(stackup_data, output_html)
        print(f"Success! HTML visualization generated: {output_html}")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()