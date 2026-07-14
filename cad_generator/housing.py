from __future__ import annotations

import os
import traceback

import FreeCAD as App
import FreeCADGui as Gui
import Part


PART_NUMBER = "HOUSING-001"
PART_NAME = "Bearing Housing"

PROJECT_ROOT = r"D:\LUBO\UKTC\Industrial_Digital_Twin_Platform"
OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "cad",
    PART_NUMBER,
)

# All dimensions are in millimetres.
BASE_LENGTH = 120.0
BASE_WIDTH = 60.0
BASE_HEIGHT = 16.0

PEDESTAL_LENGTH = 78.0
PEDESTAL_WIDTH = 60.0
PEDESTAL_HEIGHT = 42.0

HOUSING_OUTER_RADIUS = 42.0
HOUSING_WIDTH = 60.0

BEARING_BORE_DIAMETER = 52.0
BEARING_CENTRE_HEIGHT = 58.0

MOUNTING_HOLE_DIAMETER = 11.0
MOUNTING_HOLE_X = 50.0
MOUNTING_HOLE_Y = 18.0


def close_existing_document(document_name: str) -> None:
    """
    Close an already opened document with the same name.
    """

    if document_name in App.listDocuments():
        App.closeDocument(document_name)


def create_bearing_housing_shape():
    """
    Create the final solid geometry of the bearing housing.
    """

    base = Part.makeBox(
        BASE_LENGTH,
        BASE_WIDTH,
        BASE_HEIGHT,
        App.Vector(
            -BASE_LENGTH / 2,
            -BASE_WIDTH / 2,
            0,
        ),
    )

    pedestal = Part.makeBox(
        PEDESTAL_LENGTH,
        PEDESTAL_WIDTH,
        PEDESTAL_HEIGHT,
        App.Vector(
            -PEDESTAL_LENGTH / 2,
            -PEDESTAL_WIDTH / 2,
            BASE_HEIGHT,
        ),
    )

    outer_housing = Part.makeCylinder(
        HOUSING_OUTER_RADIUS,
        HOUSING_WIDTH,
        App.Vector(
            0,
            -HOUSING_WIDTH / 2,
            BEARING_CENTRE_HEIGHT,
        ),
        App.Vector(0, 1, 0),
    )

    shape = base.fuse(pedestal)
    shape = shape.fuse(outer_housing)

    bearing_bore = Part.makeCylinder(
        BEARING_BORE_DIAMETER / 2,
        HOUSING_WIDTH + 2,
        App.Vector(
            0,
            -(HOUSING_WIDTH / 2) - 1,
            BEARING_CENTRE_HEIGHT,
        ),
        App.Vector(0, 1, 0),
    )

    shape = shape.cut(bearing_bore)

    mounting_positions = [
        (-MOUNTING_HOLE_X, -MOUNTING_HOLE_Y),
        (-MOUNTING_HOLE_X, MOUNTING_HOLE_Y),
        (MOUNTING_HOLE_X, -MOUNTING_HOLE_Y),
        (MOUNTING_HOLE_X, MOUNTING_HOLE_Y),
    ]

    for x_position, y_position in mounting_positions:
        mounting_hole = Part.makeCylinder(
            MOUNTING_HOLE_DIAMETER / 2,
            BASE_HEIGHT + 2,
            App.Vector(
                x_position,
                y_position,
                -1,
            ),
            App.Vector(0, 0, 1),
        )

        shape = shape.cut(mounting_hole)

    return shape.removeSplitter()


def add_model_properties(model_object) -> None:
    """
    Add editable engineering information to the FreeCAD object.
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
        "BaseLength",
        "Dimensions",
    )
    model_object.BaseLength = BASE_LENGTH

    model_object.addProperty(
        "App::PropertyLength",
        "BaseWidth",
        "Dimensions",
    )
    model_object.BaseWidth = BASE_WIDTH

    model_object.addProperty(
        "App::PropertyLength",
        "BaseHeight",
        "Dimensions",
    )
    model_object.BaseHeight = BASE_HEIGHT

    model_object.addProperty(
        "App::PropertyLength",
        "BearingBoreDiameter",
        "Dimensions",
    )
    model_object.BearingBoreDiameter = BEARING_BORE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "MountingHoleDiameter",
        "Dimensions",
    )
    model_object.MountingHoleDiameter = MOUNTING_HOLE_DIAMETER


def export_files(doc, model_object, shape) -> None:
    """
    Save native FreeCAD, STEP and PNG files.
    """

    os.makedirs(OUTPUT_DIR, exist_ok=True)

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
        0.75,
        0.78,
        0.82,
    )

    model_object.ViewObject.LineColor = (
        0.15,
        0.15,
        0.15,
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


def generate_bearing_housing() -> None:
    """
    Generate the complete HOUSING-001 CAD model.
    """

    document_name = PART_NUMBER.replace("-", "_")

    close_existing_document(document_name)

    doc = App.newDocument(document_name)
    doc.Label = f"{PART_NUMBER} - {PART_NAME}"

    shape = create_bearing_housing_shape()

    model_object = doc.addObject(
        "Part::Feature",
        "BearingHousing",
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
        generate_bearing_housing()
        print("HOUSING-001 generated successfully.")

    except Exception:
        print("ERROR while generating HOUSING-001:")
        traceback.print_exc()
        raise