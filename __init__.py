"""
KiCAD Stackup Exporter Plugin
Exports PCB stackup information to JSON format
"""

from .stackup_exporter import StackupExporterPlugin

StackupExporterPlugin().register()