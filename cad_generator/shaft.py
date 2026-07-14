from __future__ import annotations

import os
import traceback

import FreeCAD as App
import FreeCADGui as Gui
import Part


# ============================================================
# SHAFT-001 — GEAR SHAFT
# All dimensions are in millimetres.
# ============================================================

PART_NUMBER = "SHAFT-001"
PART_NAME = "Gear Shaft"

PROJECT_ROOT = r"D:\LUBO\UKTC\Industrial_Digital_Twin_Platform"

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "cad",
    PART_NUMBER,
)


# ============================================================
# Main dimensions
# ============================================================

# Total length:
# 35 + 50 + 60 + 35 = 180 mm

LEFT_END_LENGTH = 35.0
LEFT_END_DIAMETER = 30.0

LEFT_BEARING_LENGTH = 50.0
LEFT_BEARING_DIAMETER = 40.0

GEAR_SEAT_LENGTH = 60.0
GEAR_SEAT_DIAMETER = 50.0

RIGHT_END_LENGTH = 35.0
RIGHT_END_DIAMETER = 30.0

TOTAL_LENGTH = (
    LEFT_END_LENGTH
    + LEFT_BEARING_LENGTH
    + GEAR_SEAT_LENGTH
    + RIGHT_END_LENGTH
)

# Keyway on the Ø50 gear seat.
KEYWAY_LENGTH = 48.0
KEYWAY_WIDTH = 14.0
KEYWAY_DEPTH = 5.0

# Small centre holes in both ends.
CENTRE_HOLE_DIAMETER = 6.0
CENTRE_HOLE_DEPTH = 8.0


def close_existing_document(document_name: str) -> None:
    """
    Close an already opened FreeCAD document with the same name.
    """

    if document_name in App.listDocuments():
        App.closeDocument(document_name)


def create_gear_shaft_shape():
    """
    Create the final solid geometry of SHAFT-001.

    The shaft axis is aligned with the X axis.
    """

    x_position = 0.0

    left_end = Part.makeCylinder(
        LEFT_END_DIAMETER / 2,
        LEFT_END_LENGTH,
        App.Vector(x_position, 0, 0),
        App.Vector(1, 0, 0),
    )

    x_position += LEFT_END_LENGTH

    left_bearing_seat = Part.makeCylinder(
        LEFT_BEARING_DIAMETER / 2,
        LEFT_BEARING_LENGTH,
        App.Vector(x_position, 0, 0),
        App.Vector(1, 0, 0),
    )

    x_position += LEFT_BEARING_LENGTH

    gear_seat_start = x_position

    gear_seat = Part.makeCylinder(
        GEAR_SEAT_DIAMETER / 2,
        GEAR_SEAT_LENGTH,
        App.Vector(x_position, 0, 0),
        App.Vector(1, 0, 0),
    )

    x_position += GEAR_SEAT_LENGTH

    right_end = Part.makeCylinder(
        RIGHT_END_DIAMETER / 2,
        RIGHT_END_LENGTH,
        App.Vector(x_position, 0, 0),
        App.Vector(1, 0, 0),
    )

    shaft = left_end.fuse(left_bearing_seat)
    shaft = shaft.fuse(gear_seat)
    shaft = shaft.fuse(right_end)

    # --------------------------------------------------------
    # Keyway in the upper part of the Ø50 gear seat
    # --------------------------------------------------------

    keyway_start_x = (
        gear_seat_start
        + (GEAR_SEAT_LENGTH - KEYWAY_LENGTH) / 2
    )

    keyway = Part.makeBox(
        KEYWAY_LENGTH,
        KEYWAY_WIDTH,
        KEYWAY_DEPTH + 1.0,
        App.Vector(
            keyway_start_x,
            -KEYWAY_WIDTH / 2,
            (GEAR_SEAT_DIAMETER / 2) - KEYWAY_DEPTH,
        ),
    )

    shaft = shaft.cut(keyway)

    # --------------------------------------------------------
    # Centre hole in the left end
    # --------------------------------------------------------

    left_centre_hole = Part.makeCylinder(
        CENTRE_HOLE_DIAMETER / 2,
        CENTRE_HOLE_DEPTH,
        App.Vector(0, 0, 0),
        App.Vector(1, 0, 0),
    )

    shaft = shaft.cut(left_centre_hole)

    # --------------------------------------------------------
    # Centre hole in the right end
    # --------------------------------------------------------

    right_centre_hole = Part.makeCylinder(
        CENTRE_HOLE_DIAMETER / 2,
        CENTRE_HOLE_DEPTH,
        App.Vector(TOTAL_LENGTH, 0, 0),
        App.Vector(-1, 0, 0),
    )

    shaft = shaft.cut(right_centre_hole)

    return shaft.removeSplitter()


def add_model_properties(model_object) -> None:
    """
    Add identification and principal dimensions to the CAD object.
    """

    model_object.addProperty(
        "App::PropertyString",
        "PartNumber",
        "Identification",
    )
    model_object.PartNumber = PART_NUMBER

    model_object.addProperty(
        "App::PropertyString",
        "PartName",
        "Identification",
    )
    model_object.PartName = PART_NAME

    model_object.addProperty(
        "App::PropertyLength",
        "TotalLength",
        "Dimensions",
    )
    model_object.TotalLength = TOTAL_LENGTH

    model_object.addProperty(
        "App::PropertyLength",
        "GearSeatDiameter",
        "Dimensions",
    )
    model_object.GearSeatDiameter = GEAR_SEAT_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "BearingSeatDiameter",
        "Dimensions",
    )
    model_object.BearingSeatDiameter = LEFT_BEARING_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "EndDiameter",
        "Dimensions",
    )
    model_object.EndDiameter = LEFT_END_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "KeywayWidth",
        "Dimensions",
    )
    model_object.KeywayWidth = KEYWAY_WIDTH

    model_object.addProperty(
        "App::PropertyLength",
        "KeywayDepth",
        "Dimensions",
    )
    model_object.KeywayDepth = KEYWAY_DEPTH


def export_files(doc, model_object, shape) -> None:
    """
    Save FCStd, STEP and PNG files.
    """

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True,
    )

    fcstd_path = os.path.join(
        OUTPUT_DIR,
        f"{PART_NUMBER}.FCStd",
    )

    step_path = os.path.join(
        OUTPUT_DIR,
        f"{PART_NUMBER}.step",
    )

    png_path = os.path.join(
        OUTPUT_DIR,
        f"{PART_NUMBER}.png",
    )

    doc.saveAs(fcstd_path)

    Part.export(
        [model_object],
        step_path,
    )

    model_object.ViewObject.ShapeColor = (
        0.68,
        0.70,
        0.73,
    )

    model_object.ViewObject.LineColor = (
        0.12,
        0.12,
        0.12,
    )

    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()

    Gui.activeDocument().activeView().saveImage(
        png_path,
        1600,
        1200,
        "Current",
    )

    volume_mm3 = shape.Volume
    volume_m3 = volume_mm3 / 1_000_000_000.0

    print("=" * 70)
    print(f"PART: {PART_NUMBER} - {PART_NAME}")
    print(f"CAD volume: {volume_mm3:.3f} mm3")
    print(f"CAD volume: {volume_m3:.9f} m3")
    print("Created files:")
    print(fcstd_path)
    print(step_path)
    print(png_path)
    print("=" * 70)


def generate_gear_shaft() -> None:
    """
    Generate the complete SHAFT-001 CAD model.
    """

    document_name = PART_NUMBER.replace("-", "_")

    close_existing_document(document_name)

    doc = App.newDocument(document_name)
    doc.Label = f"{PART_NUMBER} - {PART_NAME}"

    shape = create_gear_shaft_shape()

    model_object = doc.addObject(
        "Part::Feature",
        "GearShaft",
    )

    model_object.Label = f"{PART_NUMBER} - {PART_NAME}"
    model_object.Shape = shape

    add_model_properties(model_object)

    doc.recompute()

    export_files(
        doc,
        model_object,
        shape,
    )


if __name__ == "__main__":
    try:
        generate_gear_shaft()
        print("SHAFT-001 generated successfully.")

    except Exception:
        print("ERROR while generating SHAFT-001:")
        traceback.print_exc()
        raise