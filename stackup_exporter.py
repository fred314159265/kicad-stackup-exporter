"""
KiCAD Stackup Exporter Plugin
Exports PCB stackup information to JSON format by parsing the .kicad_pcb file directly
"""

import json
import os
import re
import sys
from datetime import datetime

# Import HTML generator
try:
    from .stackup_html_generator import generate_html
except (ImportError, ValueError):
    # Try without relative import (for CLI mode)
    try:
        from stackup_html_generator import generate_html
    except ImportError:
        generate_html = None

try:
    import pcbnew
    import wx
    KICAD_MODE = True
except ImportError:
    KICAD_MODE = False


def parse_stackup_from_file(pcb_file_path):
    """
    Parse stackup information directly from .kicad_pcb file

    Args:
        pcb_file_path: Path to the .kicad_pcb file

    Returns:
        dict: Stackup information structured as JSON-serializable dictionary
    """
    with open(pcb_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract board thickness from general section
    board_thickness = None
    thickness_match = re.search(r'\(general\s+\(thickness\s+([\d.]+)\)', content, re.DOTALL)
    if thickness_match:
        board_thickness = float(thickness_match.group(1))

    # Find the stackup section
    stackup_match = re.search(r'\(stackup\s+(.*?)\n\t\t\((?:copper_finish|pad_to_mask_clearance)', content, re.DOTALL)

    if not stackup_match:
        return None

    stackup_text = stackup_match.group(1)

    # Parse layers
    layers = []
    layer_pattern = r'\(layer\s+"([^"]+)"\s+(.*?)\n\t\t\t\)'

    for match in re.finditer(layer_pattern, stackup_text, re.DOTALL):
        layer_name = match.group(1)
        layer_content = match.group(2)

        layer_info = {
            "layer_name": layer_name
        }

        # Extract layer type
        type_match = re.search(r'\(type\s+"([^"]+)"\)', layer_content)
        if type_match:
            layer_info["type"] = type_match.group(1)

        # Extract thickness
        thickness_match = re.search(r'\(thickness\s+([\d.]+)\)', layer_content)
        if thickness_match:
            thickness_mm = float(thickness_match.group(1))
            layer_info["thickness"] = {
                "mm": thickness_mm,
                "mils": round(thickness_mm / 0.0254, 2),
                "um": round(thickness_mm * 1000, 2)
            }

        # Extract material
        material_match = re.search(r'\(material\s+"([^"]+)"\)', layer_content)
        material_value = material_match.group(1) if material_match else None
        if material_value:
            layer_info["material"] = material_value

        # Extract color - keep all color values from the PCB file
        color_match = re.search(r'\(color\s+"([^"]+)"\)', layer_content)
        if color_match:
            layer_info["color"] = color_match.group(1)

        # Extract epsilon_r (dielectric constant)
        epsilon_match = re.search(r'\(epsilon_r\s+([\d.]+)\)', layer_content)
        if epsilon_match:
            layer_info["epsilon_r"] = float(epsilon_match.group(1))

        # Extract loss_tangent
        loss_tangent_match = re.search(r'\(loss_tangent\s+([\d.]+)\)', layer_content)
        if loss_tangent_match:
            layer_info["loss_tangent"] = float(loss_tangent_match.group(1))

        # Skip solder paste layers
        layer_type = layer_info.get("type", "").lower()
        if "solder paste" not in layer_type:
            layers.append(layer_info)

    # Extract copper finish
    copper_finish = None
    finish_match = re.search(r'\(copper_finish\s+"([^"]+)"\)', stackup_text)
    if finish_match:
        copper_finish = finish_match.group(1)

    # Extract dielectric constraints
    dielectric_constraints = None
    constraints_match = re.search(r'\(dielectric_constraints\s+(yes|no)\)', stackup_text)
    if constraints_match:
        dielectric_constraints = constraints_match.group(1) == "yes"

    # Extract edge connector type
    edge_connector = None
    edge_connector_match = re.search(r'\(edge_connector\s+(\w+)\)', stackup_text)
    if edge_connector_match:
        edge_connector = edge_connector_match.group(1)

    # Extract castellated pads
    castellated_pads = None
    castellated_match = re.search(r'\(castellated_pads\s+(yes|no)\)', stackup_text)
    if castellated_match:
        castellated_pads = castellated_match.group(1) == "yes"

    # Extract edge plating
    edge_plating = None
    edge_plating_match = re.search(r'\(edge_plating\s+(yes|no)\)', stackup_text)
    if edge_plating_match:
        edge_plating = edge_plating_match.group(1) == "yes"

    # Count copper layers
    copper_layer_count = sum(1 for layer in layers if layer.get("type") == "copper")

    # Calculate total thickness from stackup layers
    total_thickness_from_layers = sum(
        layer.get("thickness", {}).get("mm", 0)
        for layer in layers
        if "thickness" in layer
    )

    stackup_data = {
        "board_name": os.path.basename(pcb_file_path),
        "export_date": datetime.now().isoformat(),
        "board_thickness_mm": board_thickness,
        "total_stackup_thickness_mm": round(total_thickness_from_layers, 4) if total_thickness_from_layers > 0 else None,
        "copper_layer_count": copper_layer_count,
        "copper_finish": copper_finish,
        "dielectric_constraints": dielectric_constraints,
        "edge_connector": edge_connector,
        "castellated_pads": castellated_pads,
        "edge_plating": edge_plating,
        "layers": layers
    }

    return stackup_data


if KICAD_MODE:
    class StackupExporterPlugin(pcbnew.ActionPlugin):
        """
        Plugin to export PCB stackup information to JSON
        """

        def defaults(self):
            """
            Define plugin metadata
            """
            self.name = "Stackup Exporter"
            self.category = "Manufacturing"
            self.description = "Export PCB stackup information to JSON file"
            self.show_toolbar_button = True
            self.icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")

        def Run(self):
            """
            Main plugin execution
            """
            board = pcbnew.GetBoard()

            if not board:
                wx.MessageBox("No PCB loaded!", "Error", wx.OK | wx.ICON_ERROR)
                return

            board_filename = board.GetFileName()

            if not board_filename or not os.path.exists(board_filename):
                wx.MessageBox("PCB file not saved! Please save the PCB file first.", "Error", wx.OK | wx.ICON_ERROR)
                return

            # Parse the PCB file directly
            try:
                stackup_data = parse_stackup_from_file(board_filename)
            except Exception as e:
                wx.MessageBox(f"Error parsing PCB file:\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)
                return

            if not stackup_data:
                wx.MessageBox(
                    "No stackup information found in PCB file!\n\n"
                    "Please define the physical stackup in:\n"
                    "File → Board Setup → Physical Stackup",
                    "Error",
                    wx.OK | wx.ICON_ERROR
                )
                return

            # Show save dialog
            default_filename = os.path.splitext(board_filename)[0] + "_stackup.json"

            with wx.FileDialog(
                None,
                "Save Stackup JSON",
                defaultDir=os.path.dirname(board_filename),
                defaultFile=os.path.basename(default_filename),
                wildcard="JSON files (*.json)|*.json",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            ) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return

                pathname = fileDialog.GetPath()

                try:
                    # Save JSON file
                    with open(pathname, 'w', encoding='utf-8') as f:
                        json.dump(stackup_data, f, indent=2)

                    # Generate HTML visualization
                    html_path = os.path.splitext(pathname)[0] + ".html"
                    if generate_html:
                        try:
                            generate_html(stackup_data, html_path)
                            wx.MessageBox(
                                f"Stackup exported successfully!\n\nJSON: {pathname}\nHTML: {html_path}",
                                "Success",
                                wx.OK | wx.ICON_INFORMATION
                            )
                        except Exception as html_error:
                            wx.MessageBox(
                                f"JSON exported successfully to:\n{pathname}\n\nHTML generation failed:\n{str(html_error)}",
                                "Partial Success",
                                wx.OK | wx.ICON_WARNING
                            )
                    else:
                        wx.MessageBox(f"Stackup exported successfully to:\n{pathname}", "Success", wx.OK | wx.ICON_INFORMATION)

                except Exception as e:
                    wx.MessageBox(f"Error saving file:\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)


# CLI mode
def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("KiCAD Stackup Exporter")
        print("\nUsage:")
        print(f"  python {os.path.basename(__file__)} <input.kicad_pcb> [output.json]")
        print("\nExample:")
        print(f"  python {os.path.basename(__file__)} myboard.kicad_pcb myboard_stackup.json")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    # Determine output file
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = os.path.splitext(input_file)[0] + "_stackup.json"

    try:
        print(f"Parsing stackup from: {input_file}")
        stackup_data = parse_stackup_from_file(input_file)

        if not stackup_data:
            print("Error: No stackup information found in PCB file!")
            print("Please define the physical stackup in KiCAD: File → Board Setup → Physical Stackup")
            sys.exit(1)

        # Save JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stackup_data, f, indent=2)

        print(f"Success! Stackup exported to: {output_file}")

        # Generate HTML
        html_file = os.path.splitext(output_file)[0] + ".html"
        if generate_html:
            try:
                generate_html(stackup_data, html_file)
                print(f"HTML visualization generated: {html_file}")
            except Exception as html_error:
                print(f"Warning: HTML generation failed: {html_error}")

        print(f"\nFound {len(stackup_data['layers'])} layers:")
        for layer in stackup_data['layers']:
            thickness_str = f" ({layer['thickness']['mm']}mm)" if 'thickness' in layer else ""
            print(f"  - {layer['layer_name']}: {layer.get('type', 'unknown')}{thickness_str}")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()