"""KiCad project files for the b3_matched board: b3_matched.kicad_sch (SMA connector -> antenna, GND on the shield) and b3_matched.kicad_pro.
KiCad 7+ format, written by hand and NOT opened in KiCad here: open it, run ERC, assign the connector footprint (Connector_Coaxial library, an SMA edge-launch that
matches your part's datasheet), then Tools > Update PCB from Schematic.
Usage: python scripts/export_kicad_sch.py <out_dir> [name]"""
import json
import sys
import uuid
from pathlib import Path


def sch(name):
    u = lambda: str(uuid.uuid4())
    eff = "(effects (font (size 1.27 1.27)))"
    def prop(k, v, x, y, hide=False):
        return f'(property "{k}" "{v}" (at {x} {y} 0) (effects (font (size 1.27 1.27)){" hide" if hide else ""}))'
    lib = f'''(lib_symbols
    (symbol "Device:Antenna" (pin_names (offset 1.016) hide) (in_bom yes) (on_board yes)
      {prop("Reference", "AE", -2.54, 3.81)} {prop("Value", "Antenna", -2.54, 1.27)} {prop("Footprint", "", 0, 0, True)} {prop("Datasheet", "~", 0, 0, True)}
      (symbol "Antenna_0_1" (polyline (pts (xy 0 2.54) (xy 0 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 2.54) (xy 0 0) (xy -1.27 2.54)) (stroke (width 0.254) (type default)) (fill (type none))))
      (symbol "Antenna_1_1" (pin input line (at 5.08 0 180) (length 5.08) (name "A" {eff}) (number "1" {eff}))))
    (symbol "Connector:Conn_Coaxial" (pin_names (offset 1.016) hide) (in_bom yes) (on_board yes)
      {prop("Reference", "J", 0, 3.81)} {prop("Value", "Conn_Coaxial", 0, 1.27)} {prop("Footprint", "", 0, 0, True)} {prop("Datasheet", "~", 0, 0, True)}
      (symbol "Conn_Coaxial_0_1" (arc (start -1.778 -0.508) (mid 0.2311 -1.7952) (end 1.778 0) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 0) (xy -0.508 0)) (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 -2.54) (xy 0 -1.778)) (stroke (width 0) (type default)) (fill (type none)))
        (circle (center 0 0) (radius 0.508) (stroke (width 0.2032) (type default)) (fill (type none))))
      (symbol "Conn_Coaxial_1_1" (pin passive line (at -5.08 0 0) (length 2.54) (name "In" {eff}) (number "1" {eff}))
        (pin passive line (at 0 -5.08 90) (length 2.54) (name "Ext" {eff}) (number "2" {eff})))))'''
    j, ae = (86.36, 50.8), (50.8, 50.8)
    body = f'''
  (symbol (lib_id "Connector:Conn_Coaxial") (at {j[0]} {j[1]} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {u()})
    (property "Reference" "J1" (at {j[0]} {j[1] - 5.08} 0) {eff}) (property "Value" "SMA edge-launch" (at {j[0]} {j[1] - 2.54} 0) {eff})
    (property "Footprint" "" (at {j[0]} {j[1]} 0) (effects (font (size 1.27 1.27)) hide)) (property "Datasheet" "~" (at {j[0]} {j[1]} 0) (effects (font (size 1.27 1.27)) hide))
    (pin "1" (uuid {u()})) (pin "2" (uuid {u()})))
  (symbol (lib_id "Device:Antenna") (at {ae[0]} {ae[1]} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {u()})
    (property "Reference" "AE1" (at {ae[0]} {ae[1] - 5.08} 0) {eff}) (property "Value" "Meander FR4 B3 (printed on the board)" (at {ae[0]} {ae[1] - 2.54} 0) {eff})
    (property "Footprint" "" (at {ae[0]} {ae[1]} 0) (effects (font (size 1.27 1.27)) hide)) (property "Datasheet" "~" (at {ae[0]} {ae[1]} 0) (effects (font (size 1.27 1.27)) hide))
    (pin "1" (uuid {u()})))
  (wire (pts (xy {ae[0] + 5.08} {ae[1]}) (xy {j[0] - 5.08} {j[1]})) (stroke (width 0) (type default)) (uuid {u()}))
  (global_label "GND" (shape input) (at {j[0]} {j[1] + 5.08} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid {u()}) (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide)))
  (text "Printed antenna: LTE B3 (1.71-1.88 GHz), meander on FR4 1.6 mm. 50 ohm strip 3.06 mm from J1 to the matching sections. Ground plane = the B.Cu copper."
    (at 40.64 76.2 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {u()}))'''
    return f'(kicad_sch (version 20230121) (generator "antenna-agent") (uuid {u()}) (paper "A4")\n  {lib}\n{body}\n  (sheet_instances (path "/" (page "1"))))\n'


def main(out, name="b3_matched"):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    t = sch(name); assert t.count("(") == t.count(")")
    (out / f"{name}.kicad_sch").write_text(t)
    (out / f"{name}.kicad_pro").write_text(json.dumps({"meta": {"filename": f"{name}.kicad_pro", "version": 1}}, indent=2) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
