from __future__ import annotations

import os
import traceback

import FreeCAD as App
import FreeCADGui as Gui
import Part


# ============================================================
# DEMO-001 — FIXTURE SUPPORT BLOCK
# All dimensions are in millimetres.
# ============================================================

PART_NUMBER = "DEMO-001"
PART_NAME = "Fixture Support Block"

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

BLOCK_LENGTH = 110.0
BLOCK_WIDTH = 80.0
BLOCK_HEIGHT = 45.0

CENTRAL_BORE_DIAMETER = 34.0

MOUNTING_HOLE_DIAMETER = 10.0
MOUNTING_HOLE_X = 42.0
MOUNTING_HOLE_Y = 27.0

TOP_SLOT_LENGTH = 54.0
TOP_SLOT_WIDTH = 18.0
TOP_SLOT_DEPTH = 12.0

SIDE_POCKET_LENGTH = 28.0
SIDE_POCKET_HEIGHT = 18.0
SIDE_POCKET_DEPTH = 10.0

SIDE_POCKET_X = 0.0
SIDE_POCKET_Z = 14.0


def close_existing_document(document_name: str) -> None:
    """
    Close an already opened FreeCAD document with the same name.
    """

    if document_name in App.listDocuments():
        App.closeDocument(document_name)


def create_fixture_support_shape():
    """
    Create the final solid geometry of DEMO-001.
    """

    # ========================================================
    # 1. Main rectangular block
    # ========================================================

    shape = Part.makeBox(
        BLOCK_LENGTH,
        BLOCK_WIDTH,
        BLOCK_HEIGHT,
        App.Vector(
            -BLOCK_LENGTH / 2,
            -BLOCK_WIDTH / 2,
            0,
        ),
    )

    # ========================================================
    # 2. Central through bore
    # ========================================================
    #
    # Axis is along Y, so the bore passes through the block
    # from front to rear.
    # ========================================================

    central_bore = Part.makeCylinder(
        CENTRAL_BORE_DIAMETER / 2,
        BLOCK_WIDTH + 2,
        App.Vector(
            0,
            -(BLOCK_WIDTH / 2) - 1,
            BLOCK_HEIGHT / 2,
        ),
        App.Vector(0, 1, 0),
    )

    shape = shape.cut(central_bore)

    # ========================================================
    # 3. Four vertical mounting holes
    # ========================================================

    mounting_hole_positions = [
        (-MOUNTING_HOLE_X, -MOUNTING_HOLE_Y),
        (-MOUNTING_HOLE_X, MOUNTING_HOLE_Y),
        (MOUNTING_HOLE_X, -MOUNTING_HOLE_Y),
        (MOUNTING_HOLE_X, MOUNTING_HOLE_Y),
    ]

    for x_position, y_position in mounting_hole_positions:
        mounting_hole = Part.makeCylinder(
            MOUNTING_HOLE_DIAMETER / 2,
            BLOCK_HEIGHT + 2,
            App.Vector(
                x_position,
                y_position,
                -1,
            ),
            App.Vector(0, 0, 1),
        )

        shape = shape.cut(mounting_hole)

    # ========================================================
    # 4. Top slot
    # ========================================================

    top_slot = Part.makeBox(
        TOP_SLOT_LENGTH,
        TOP_SLOT_WIDTH,
        TOP_SLOT_DEPTH,
        App.Vector(
            -TOP_SLOT_LENGTH / 2,
            -TOP_SLOT_WIDTH / 2,
            BLOCK_HEIGHT - TOP_SLOT_DEPTH,
        ),
    )

    shape = shape.cut(top_slot)

    # ========================================================
    # 5. Left side pocket
    # ========================================================

    left_side_pocket = Part.makeBox(
        SIDE_POCKET_LENGTH,
        SIDE_POCKET_DEPTH + 1,
        SIDE_POCKET_HEIGHT,
        App.Vector(
            -SIDE_POCKET_LENGTH / 2,
            -(BLOCK_WIDTH / 2) - 1,
            SIDE_POCKET_Z,
        ),
    )

    shape = shape.cut(left_side_pocket)

    # ========================================================
    # 6. Right side pocket
    # ========================================================

    right_side_pocket = Part.makeBox(
        SIDE_POCKET_LENGTH,
        SIDE_POCKET_DEPTH + 1,
        SIDE_POCKET_HEIGHT,
        App.Vector(
            -SIDE_POCKET_LENGTH / 2,
            (BLOCK_WIDTH / 2) - SIDE_POCKET_DEPTH,
            SIDE_POCKET_Z,
        ),
    )

    shape = shape.cut(right_side_pocket)

    return shape.removeSplitter()


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
        "BlockLength",
        "Dimensions",
    )
    model_object.BlockLength = BLOCK_LENGTH

    model_object.addProperty(
        "App::PropertyLength",
        "BlockWidth",
        "Dimensions",
    )
    model_object.BlockWidth = BLOCK_WIDTH

    model_object.addProperty(
        "App::PropertyLength",
        "BlockHeight",
        "Dimensions",
    )
    model_object.BlockHeight = BLOCK_HEIGHT

    model_object.addProperty(
        "App::PropertyLength",
        "CentralBoreDiameter",
        "Dimensions",
    )
    model_object.CentralBoreDiameter = CENTRAL_BORE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "MountingHoleDiameter",
        "Dimensions",
    )
    model_object.MountingHoleDiameter = MOUNTING_HOLE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "TopSlotLength",
        "Dimensions",
    )
    model_object.TopSlotLength = TOP_SLOT_LENGTH

    model_object.addProperty(
        "App::PropertyLength",
        "TopSlotWidth",
        "Dimensions",
    )
    model_object.TopSlotWidth = TOP_SLOT_WIDTH

    model_object.addProperty(
        "App::PropertyLength",
        "TopSlotDepth",
        "Dimensions",
    )
    model_object.TopSlotDepth = TOP_SLOT_DEPTH


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
        0.78,
        0.76,
        0.68,
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


def generate_fixture_support_block() -> None:
    """
    Generate the complete DEMO-001 CAD model.
    """

    document_name = PART_NUMBER.replace("-", "_")

    close_existing_document(document_name)

    doc = App.newDocument(document_name)
    doc.Label = f"{PART_NUMBER} - {PART_NAME}"

    shape = create_fixture_support_shape()

    model_object = doc.addObject(
        "Part::Feature",
        "FixtureSupportBlock",
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
        generate_fixture_support_block()
        print("DEMO-001 generated successfully.")

    except Exception:
        print("ERROR while generating DEMO-001:")
        traceback.print_exc()
        raise

