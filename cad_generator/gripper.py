from __future__ import annotations

import os
import traceback

import FreeCAD as App
import FreeCADGui as Gui
import Part


# ============================================================
# GRIPPER-001 — ROBOT GRIPPER FINGER
# All dimensions are in millimetres.
# ============================================================

PART_NUMBER = "GRIPPER-001"
PART_NAME = "Robot Gripper Finger"

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

TOTAL_LENGTH = 140.0
BODY_WIDTH = 30.0
BODY_HEIGHT = 22.0

# Задна монтажна зона.
MOUNTING_SECTION_LENGTH = 45.0

# Предна работна челюст.
JAW_LENGTH = 35.0
JAW_WIDTH = 20.0
JAW_HEIGHT = 14.0

# Стъпка между основното тяло и работната челюст.
JAW_VERTICAL_OFFSET = 4.0

# Два монтажни отвора.
MOUNTING_HOLE_DIAMETER = 8.0
MOUNTING_HOLE_X_1 = 15.0
MOUNTING_HOLE_X_2 = 33.0

# Отворите са центрирани по ширината.
MOUNTING_HOLE_Y = BODY_WIDTH / 2

# Надлъжен олекотяващ канал.
SLOT_LENGTH = 55.0
SLOT_WIDTH = 12.0
SLOT_DEPTH = 12.0
SLOT_START_X = 55.0

# Напречен отвор близо до челюстта.
CROSS_HOLE_DIAMETER = 6.0
CROSS_HOLE_X = 112.0
CROSS_HOLE_Z = 11.0


def close_existing_document(document_name: str) -> None:
    """
    Close an already opened FreeCAD document with the same name.
    """

    if document_name in App.listDocuments():
        App.closeDocument(document_name)


def create_gripper_finger_shape():
    """
    Create the final solid geometry of GRIPPER-001.
    """

    # ========================================================
    # 1. Main rectangular body
    # ========================================================

    body = Part.makeBox(
        TOTAL_LENGTH,
        BODY_WIDTH,
        BODY_HEIGHT,
        App.Vector(
            0,
            -BODY_WIDTH / 2,
            0,
        ),
    )

    # ========================================================
    # 2. Reduced front jaw
    # ========================================================
    #
    # Премахваме материал от горната и страничните части
    # на предния край, за да оформим по-тясна челюст.
    # ========================================================

    jaw_start_x = TOTAL_LENGTH - JAW_LENGTH

    upper_cut = Part.makeBox(
        JAW_LENGTH + 1,
        BODY_WIDTH + 2,
        BODY_HEIGHT - JAW_HEIGHT,
        App.Vector(
            jaw_start_x,
            -(BODY_WIDTH / 2) - 1,
            JAW_HEIGHT + JAW_VERTICAL_OFFSET,
        ),
    )

    shape = body.cut(upper_cut)

    left_side_cut = Part.makeBox(
        JAW_LENGTH + 1,
        (BODY_WIDTH - JAW_WIDTH) / 2,
        BODY_HEIGHT + 2,
        App.Vector(
            jaw_start_x,
            -BODY_WIDTH / 2,
            -1,
        ),
    )

    right_side_cut = Part.makeBox(
        JAW_LENGTH + 1,
        (BODY_WIDTH - JAW_WIDTH) / 2,
        BODY_HEIGHT + 2,
        App.Vector(
            jaw_start_x,
            JAW_WIDTH / 2,
            -1,
        ),
    )

    shape = shape.cut(left_side_cut)
    shape = shape.cut(right_side_cut)

    # ========================================================
    # 3. Two mounting holes in the rear section
    # ========================================================
    #
    # Оста на отворите е по Z.
    # ========================================================

    mounting_hole_positions = [
        MOUNTING_HOLE_X_1,
        MOUNTING_HOLE_X_2,
    ]

    for x_position in mounting_hole_positions:
        mounting_hole = Part.makeCylinder(
            MOUNTING_HOLE_DIAMETER / 2,
            BODY_HEIGHT + 2,
            App.Vector(
                x_position,
                0,
                -1,
            ),
            App.Vector(0, 0, 1),
        )

        shape = shape.cut(mounting_hole)

    # ========================================================
    # 4. Longitudinal lightening slot
    # ========================================================

    slot = Part.makeBox(
        SLOT_LENGTH,
        SLOT_WIDTH,
        SLOT_DEPTH,
        App.Vector(
            SLOT_START_X,
            -SLOT_WIDTH / 2,
            BODY_HEIGHT - SLOT_DEPTH,
        ),
    )

    shape = shape.cut(slot)

    # ========================================================
    # 5. Cross hole near the front jaw
    # ========================================================
    #
    # Оста е по Y, тоест отворът преминава през ширината.
    # ========================================================

    cross_hole = Part.makeCylinder(
        CROSS_HOLE_DIAMETER / 2,
        BODY_WIDTH + 2,
        App.Vector(
            CROSS_HOLE_X,
            -(BODY_WIDTH / 2) - 1,
            CROSS_HOLE_Z,
        ),
        App.Vector(0, 1, 0),
    )

    shape = shape.cut(cross_hole)

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
        "TotalLength",
        "Dimensions",
    )
    model_object.TotalLength = TOTAL_LENGTH

    model_object.addProperty(
        "App::PropertyLength",
        "BodyWidth",
        "Dimensions",
    )
    model_object.BodyWidth = BODY_WIDTH

    model_object.addProperty(
        "App::PropertyLength",
        "BodyHeight",
        "Dimensions",
    )
    model_object.BodyHeight = BODY_HEIGHT

    model_object.addProperty(
        "App::PropertyLength",
        "JawLength",
        "Dimensions",
    )
    model_object.JawLength = JAW_LENGTH

    model_object.addProperty(
        "App::PropertyLength",
        "JawWidth",
        "Dimensions",
    )
    model_object.JawWidth = JAW_WIDTH

    model_object.addProperty(
        "App::PropertyLength",
        "JawHeight",
        "Dimensions",
    )
    model_object.JawHeight = JAW_HEIGHT

    model_object.addProperty(
        "App::PropertyLength",
        "MountingHoleDiameter",
        "Dimensions",
    )
    model_object.MountingHoleDiameter = MOUNTING_HOLE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "CrossHoleDiameter",
        "Dimensions",
    )
    model_object.CrossHoleDiameter = CROSS_HOLE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "SlotLength",
        "Dimensions",
    )
    model_object.SlotLength = SLOT_LENGTH

    model_object.addProperty(
        "App::PropertyLength",
        "SlotWidth",
        "Dimensions",
    )
    model_object.SlotWidth = SLOT_WIDTH


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
        0.64,
        0.67,
        0.72,
    )

    model_object.ViewObject.LineColor = (
        0.10,
        0.10,
        0.10,
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


def generate_robot_gripper_finger() -> None:
    """
    Generate the complete GRIPPER-001 CAD model.
    """

    document_name = PART_NUMBER.replace("-", "_")

    close_existing_document(document_name)

    doc = App.newDocument(document_name)
    doc.Label = f"{PART_NUMBER} - {PART_NAME}"

    shape = create_gripper_finger_shape()

    model_object = doc.addObject(
        "Part::Feature",
        "RobotGripperFinger",
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
        generate_robot_gripper_finger()
        print("GRIPPER-001 generated successfully.")

    except Exception:
        print("ERROR while generating GRIPPER-001:")
        traceback.print_exc()
        raise
