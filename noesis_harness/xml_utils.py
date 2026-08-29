"""noesis_harness/xml_utils.py — simple XML read/write helpers.

Patterns: LoopX XML.
Stdlib only.
"""
from __future__ import annotations
from xml.etree import ElementTree as ET

def from_string(text: str) -> ET.Element:
    return ET.fromstring(text)
def to_string(elem: ET.Element, encoding: str = "unicode") -> str:
    return ET.tostring(elem, encoding=encoding)
def find_text(elem: ET.Element, path: str, default: str = "") -> str:
    node = elem.find(path)
    return (node.text or default) if node is not None else default
def find_all(elem: ET.Element, path: str) -> list:
    return elem.findall(path)
def make_element(tag: str, text: str = None) -> ET.Element:
    e = ET.Element(tag)
    if text is not None: e.text = text
    return e
def set_text(elem: ET.Element, text: str) -> None:
    elem.text = text
def add_child(parent: ET.Element, tag: str, text: str = None) -> ET.Element:
    child = ET.SubElement(parent, tag)
    if text is not None: child.text = text
    return child
def remove_children(parent: ET.Element) -> None:
    parent.clear()
