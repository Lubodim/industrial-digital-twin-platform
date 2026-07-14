from __future__ import annotations

import math
import os
import traceback

import FreeCAD as App
import FreeCADGui as Gui
import Part


# ============================================================
# FLANGE-001 — INDUSTRIAL FLANGE
# All dimensions are in millimetres.
# ============================================================

PART_NUMBER = "FLANGE-001"
PART_NAME = "Industrial Flange"

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

OUTER_DIAMETER = 180.0
THICKNESS = 20.0

CENTRAL_BORE_DIAMETER = 80.0

BOLT_CIRCLE_DIAMETER = 140.0
BOLT_HOLE_DIAMETER = 14.0
BOLT_HOLE_COUNT = 8


def close_existing_document(document_name: str) -> None:
    """
    Close an already opened FreeCAD document with the same name.
    """

    if document_name in App.listDocuments():
        App.closeDocument(document_name)


def create_flange_shape():
    """
    Create the final solid geometry of FLANGE-001.
    """

    outer_radius = OUTER_DIAMETER / 2
    central_bore_radius = CENTRAL_BORE_DIAMETER / 2
    bolt_circle_radius = BOLT_CIRCLE_DIAMETER / 2
    bolt_hole_radius = BOLT_HOLE_DIAMETER / 2

    flange = Part.makeCylinder(
        outer_radius,
        THICKNESS,
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
    )

    central_bore = Part.makeCylinder(
        central_bore_radius,
        THICKNESS + 2,
        App.Vector(0, 0, -1),
        App.Vector(0, 0, 1),
    )

    flange = flange.cut(central_bore)

    angle_step = 360.0 / BOLT_HOLE_COUNT

    for index in range(BOLT_HOLE_COUNT):
        angle_degrees = index * angle_step
        angle_radians = math.radians(angle_degrees)

        x_position = bolt_circle_radius * math.cos(angle_radians)
        y_position = bolt_circle_radius * math.sin(angle_radians)

        bolt_hole = Part.makeCylinder(
            bolt_hole_radius,
            THICKNESS + 2,
            App.Vector(
                x_position,
                y_position,
                -1,
            ),
            App.Vector(0, 0, 1),
        )

        flange = flange.cut(bolt_hole)

    return flange.removeSplitter()


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
        "OuterDiameter",
        "Dimensions",
    )
    model_object.OuterDiameter = OUTER_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "Thickness",
        "Dimensions",
    )
    model_object.Thickness = THICKNESS

    model_object.addProperty(
        "App::PropertyLength",
        "CentralBoreDiameter",
        "Dimensions",
    )
    model_object.CentralBoreDiameter = CENTRAL_BORE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "BoltCircleDiameter",
        "Dimensions",
    )
    model_object.BoltCircleDiameter = BOLT_CIRCLE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "BoltHoleDiameter",
        "Dimensions",
    )
    model_object.BoltHoleDiameter = BOLT_HOLE_DIAMETER

    model_object.addProperty(
        "App::PropertyInteger",
        "BoltHoleCount",
        "Dimensions",
    )
    model_object.BoltHoleCount = BOLT_HOLE_COUNT


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
        0.72,
        0.74,
        0.77,
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


def generate_flange() -> None:
    """
    Generate the complete FLANGE-001 CAD model.
    """

    document_name = PART_NUMBER.replace("-", "_")

    close_existing_document(document_name)

    doc = App.newDocument(document_name)
    doc.Label = f"{PART_NUMBER} - {PART_NAME}"

    shape = create_flange_shape()

    model_object = doc.addObject(
        "Part::Feature",
        "IndustrialFlange",
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
        generate_flange()
        print("FLANGE-001 generated successfully.")

    except Exception:
        print("ERROR while generating FLANGE-001:")
        traceback.print_exc()
        raise