# KiCAD Stackup Exporter

A KiCAD plugin that exports PCB stackup information to JSON and generates a beautiful HTML visualization.

## Features

- Export complete PCB stackup data from KiCAD to JSON format
- Automatic HTML visualization with color-coded layers
- Captures all stackup properties:
  - Layer thicknesses (mm, mils, μm)
  - Materials and dielectric properties
  - Copper finish and layer count
  - Edge connectors, castellated pads, edge plating
  - Dielectric constants and loss tangents
- Works as both a KiCAD plugin and command-line tool
- Print-optimized HTML output for documentation

Check an example of a [generated documentation page here](https://fred314159265.github.io/kicad-stackup-exporter/example_output\CANchovy_PCB_stackup.html).

## Installation

1. Copy the `Stackup_Exporter` folder to your KiCAD scripting plugins directory:
   - **Windows**: `C:\Users\[username]\Documents\KiCAD\[version]\scripting\plugins\`
   - **Linux**: `~/.kicad/scripting/plugins/`
   - **macOS**: `~/Library/Application Support/kicad/scripting/plugins/`

2. Restart KiCAD PCB Editor

3. The plugin will appear in the **Tools → External Plugins** menu as "Stackup Exporter"

## Usage

### As a KiCAD Plugin

1. Open your PCB in KiCAD PCB Editor
2. Define your physical stackup: **File → Board Setup → Physical Stackup**
3. Save your PCB file
4. Run the plugin: **Tools → External Plugins → Stackup Exporter**
5. Choose where to save the JSON file
6. The plugin will generate both a `.json` file and an `.html` visualization

### As a Command-Line Tool

```bash
python stackup_exporter.py <input.kicad_pcb> [output.json]
```

**Example:**
```bash
python stackup_exporter.py myboard.kicad_pcb myboard_stackup.json
```

This will create:
- `myboard_stackup.json` - Stackup data in JSON format
- `myboard_stackup.html` - Interactive HTML visualization

## Output Format

The JSON output includes:
- Board thickness and copper layer count
- Copper finish specification
- Manufacturing options (edge connector, castellated pads, edge plating)
- Detailed layer information with materials and electrical properties

The HTML visualization provides:
- Color-coded stackup diagram
- Detailed layer properties
- Print-friendly formatting for documentation

## Requirements

- KiCAD 9.0 (or compatible version)
- Python 3.x for command-line usage

## License

This project is open source. Feel free to use and modify as needed.
