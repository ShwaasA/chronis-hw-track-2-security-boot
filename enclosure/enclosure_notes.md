# First-Pass Enclosure Design — Track HW-2, Day 3

**Status: datasheet-dimensions-only, NOT checked against real physical fit.**

## Why this can't be built in a plain code sandbox
CAD modeling needs a CAD application (FreeCAD, Fusion 360, SolidWorks) — it's
not something you script and run headlessly the way the daemons above are.
This doc gives you the dimension inputs and a FreeCAD macro skeleton so the
actual modeling in the FreeCAD GUI goes fast, rather than starting from a
blank canvas.

## Recommended tool
**FreeCAD** (free, scriptable via Python macros, good for a first-pass
component-placement model) — download from freecad.org. Fusion 360 is fine
too if you already have a license; the dimension inputs below apply either way.

## Dimension inputs to pull from datasheets (fill in before modeling)

| Component | Datasheet | Footprint (L×W×H mm) | Notes |
|---|---|---|---|
| Radxa Zero 3W | Radxa product page | *(pull exact board dims)* | main compute board |
| ICM-42688-P | TDK InvenSense datasheet | *(pull package size)* | IMU, small QFN package |
| MAX30102 | Analog Devices datasheet | *(pull package size)* | needs clear skin contact opening |
| ATECC608B | Microchip datasheet | *(pull package size)* | security chip, no external opening needed |
| IMX219 camera module | Sony/module vendor datasheet | *(pull module depth incl. lens stack)* | needs a clear lens opening |
| DS3231-class RTC | Maxim/vendor datasheet | *(pull package size)* | small, place anywhere convenient |
| Battery | TBD once capacity is chosen | *(pull cell dimensions)* | biggest single volume driver — lock this early |

## Design constraints to model against
- **Weight distribution:** heaviest components (battery, camera module) placed
  to balance the wearable, not clustered on one edge.
- **Camera/mic opening:** must have direct, unobstructed exposure — no
  enclosure wall or PCB silkscreen in the optical/acoustic path.
- **Charging port placement:** accessible without removing the device from
  the body; keep clear of the camera opening.
- **Thermal cross-check:** compare against `power_thermal_estimate.py`
  output — if projected draw at L4/L5 implies sustained high current, flag
  whether the enclosure needs a heat-dissipating material or vents, rather
  than assuming passive cooling is sufficient.

## FreeCAD macro skeleton (run inside FreeCAD's Python console / macro editor)

```python
import FreeCAD as App
import Part

doc = App.newDocument("ChronisEnclosureV1")

# Replace these placeholder dimensions with real datasheet figures.
board_dims = (40, 25, 3)      # Radxa Zero 3W, mm — PLACEHOLDER
battery_dims = (30, 20, 6)    # PLACEHOLDER — depends on chosen cell
camera_dims = (8, 8, 5)       # PLACEHOLDER — IMX219 module + lens stack

def make_box(name, dims, position):
    box = doc.addObject("Part::Box", name)
    box.Length, box.Width, box.Height = dims
    box.Placement.Base = App.Vector(*position)
    return box

make_box("MainBoard", board_dims, (0, 0, 0))
make_box("Battery", battery_dims, (0, 0, board_dims[2] + 1))
make_box("CameraModule", camera_dims, (board_dims[0] - camera_dims[0], 0, 0))

# Outer shell — oversize the bounding box of all components, then shell it.
shell_margin = 2  # mm of wall clearance around internal components
outer_L = board_dims[0] + shell_margin * 2
outer_W = board_dims[1] + shell_margin * 2
outer_H = board_dims[2] + battery_dims[2] + shell_margin * 2

outer = doc.addObject("Part::Box", "OuterShell")
outer.Length, outer.Width, outer.Height = outer_L, outer_W, outer_H

doc.recompute()
print("Placeholder enclosure geometry created. Replace dims with real "
      "datasheet values, then manually add: camera opening cutout, "
      "charging port cutout, wall shelling (Part > Thickness).")
```

**How to use this:** open FreeCAD → Macro → Macros... → create new macro →
paste the script above → fill in real dimensions → run → continue modeling
by hand (openings, wall thickness via the Thickness tool, mounting posts)
in the FreeCAD GUI from there.

## Explicit gaps (carry into `security-boot-report.md`)
- Not checked against manufacturing tolerances or 3D-print accuracy.
- Not checked against how components physically fit together on a real PCB
  layout (this models bounding boxes only, not actual board routing).
- Thermal behavior under sustained L4/L5 load is projected, not measured.
