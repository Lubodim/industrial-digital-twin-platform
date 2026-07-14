from __future__ import annotations

import os
import traceback

import FreeCAD as App
import FreeCADGui as Gui
import Part


# ============================================================
# BRACKET-001 — MOUNTING BRACKET
# All dimensions are in millimetres.
# ============================================================

PART_NUMBER = "BRACKET-001"
PART_NAME = "Mounting Bracket"

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

# Основна плоча.
# X е посоката по дължината — от стената към предния ръб.
# Y е посоката по ширината.
# Z е височината.
BASE_LENGTH = 120.0
BASE_WIDTH = 80.0
BASE_THICKNESS = 12.0

# Вертикална стена.
WALL_WIDTH = 80.0
WALL_HEIGHT = 70.0
WALL_THICKNESS = 12.0


# ============================================================
# Holes in the horizontal base
# ============================================================

BASE_HOLE_DIAMETER = 10.0

# ПРЕДНИ ДВА ОТВОРА:
# Положителната X координата е към предния край на основата.
#
# Основата е от X = -60 до X = +60.
# X = +45 означава 15 mm от предния ръб до центъра.
FRONT_BASE_HOLE_X = 45.0

# ЗАДНИ ДВА ОТВОРА:
# Вертикалната стена е при задния ръб:
# приблизително от X = -60 до X = -48.
#
# Преди центровете бяха на X = -45 и отворите застъпваха
# стената/сгъвката.
#
# Сега ги преместваме напред до X = -25.
# За още по-голямо преместване напред увеличи стойността,
# например:
#   -20.0
#   -15.0
#    -10.0
REAR_BASE_HOLE_X = -25.0

# Разстояние на отворите вляво и вдясно от централната ос Y = 0.
# При Y = ±25 и ширина 80 mm остават 15 mm до страничния ръб.
BASE_HOLE_Y = 25.0


# ============================================================
# Holes in the vertical wall
# ============================================================

WALL_HOLE_DIAMETER = 12.0

# Центрове на двата малки отвора в стената:
# Y = -22 и Y = +22.
WALL_HOLE_Y = 28.0

# Височина на центровете над долната повърхност.
WALL_HOLE_Z = 42.0

# Централен олекотяващ отвор.
LIGHTENING_HOLE_DIAMETER = 32.0
LIGHTENING_HOLE_Z = 38.0


def close_existing_document(document_name: str) -> None:
    """
    Close an already opened FreeCAD document with the same name.
    """

    if document_name in App.listDocuments():
        App.closeDocument(document_name)


def create_mounting_bracket_shape():
    """
    Create the final solid geometry of BRACKET-001.
    """

    # ========================================================
    # 1. Horizontal base plate
    # ========================================================

    base = Part.makeBox(
        BASE_LENGTH,
        BASE_WIDTH,
        BASE_THICKNESS,
        App.Vector(
            -BASE_LENGTH / 2,
            -BASE_WIDTH / 2,
            0,
        ),
    )

    # ========================================================
    # 2. Vertical wall
    # ========================================================
    #
    # Стената започва от задния край на основата:
    # X = -BASE_LENGTH / 2 = -60 mm.
    #
    # При дебелина 12 mm тя заема:
    # X = -60 до X = -48 mm.
    # ========================================================

    wall = Part.makeBox(
        WALL_THICKNESS,
        WALL_WIDTH,
        WALL_HEIGHT,
        App.Vector(
            -BASE_LENGTH / 2,
            -WALL_WIDTH / 2,
            BASE_THICKNESS,
        ),
    )

    bracket = base.fuse(wall)

    # ========================================================
    # 3. Four holes in the horizontal base
    # ========================================================
    #
    # ТУК СЕ ОПРЕДЕЛЯ МЕСТОПОЛОЖЕНИЕТО НА ЧЕТИРИТЕ ОТВОРА.
    #
    # Всеки запис е:
    #
    #     (X координата, Y координата)
    #
    # FRONT_BASE_HOLE_X управлява предните два отвора.
    # REAR_BASE_HOLE_X управлява задните два отвора.
    # BASE_HOLE_Y управлява разположението по ширината.
    # ========================================================

    base_hole_positions = [
        # Заден ляв отвор — преместен напред от сгъвката.
        (REAR_BASE_HOLE_X, -BASE_HOLE_Y),

        # Заден десен отвор — преместен напред от сгъвката.
        (REAR_BASE_HOLE_X, BASE_HOLE_Y),

        # Преден ляв отвор.
        (FRONT_BASE_HOLE_X, -BASE_HOLE_Y),

        # Преден десен отвор.
        (FRONT_BASE_HOLE_X, BASE_HOLE_Y),
    ]

    for x_position, y_position in base_hole_positions:
        hole = Part.makeCylinder(
            BASE_HOLE_DIAMETER / 2,
            BASE_THICKNESS + 2,
            App.Vector(
                x_position,
                y_position,
                -1,
            ),
            App.Vector(0, 0, 1),
        )

        bracket = bracket.cut(hole)

    # ========================================================
    # 4. Two small holes in the vertical wall
    # ========================================================
    #
    # Оста им е по X, защото преминават през дебелината
    # на вертикалната стена.
    # ========================================================

    wall_hole_positions = [
        -WALL_HOLE_Y,
        WALL_HOLE_Y,
    ]

    for y_position in wall_hole_positions:
        hole = Part.makeCylinder(
            WALL_HOLE_DIAMETER / 2,
            WALL_THICKNESS + 2,
            App.Vector(
                (-BASE_LENGTH / 2) - 1,
                y_position,
                WALL_HOLE_Z,
            ),
            App.Vector(1, 0, 0),
        )

        bracket = bracket.cut(hole)

    # ========================================================
    # 5. Central lightening hole in the vertical wall
    # ========================================================

    lightening_hole = Part.makeCylinder(
        LIGHTENING_HOLE_DIAMETER / 2,
        WALL_THICKNESS + 2,
        App.Vector(
            (-BASE_LENGTH / 2) - 1,
            0,
            LIGHTENING_HOLE_Z,
        ),
        App.Vector(1, 0, 0),
    )

    bracket = bracket.cut(lightening_hole)

    return bracket.removeSplitter()


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
        "BaseThickness",
        "Dimensions",
    )
    model_object.BaseThickness = BASE_THICKNESS

    model_object.addProperty(
        "App::PropertyLength",
        "WallHeight",
        "Dimensions",
    )
    model_object.WallHeight = WALL_HEIGHT

    model_object.addProperty(
        "App::PropertyLength",
        "WallThickness",
        "Dimensions",
    )
    model_object.WallThickness = WALL_THICKNESS

    model_object.addProperty(
        "App::PropertyLength",
        "BaseHoleDiameter",
        "Dimensions",
    )
    model_object.BaseHoleDiameter = BASE_HOLE_DIAMETER

    # Добавяме координатите като свойства, за да се виждат
    # във FreeCAD Property View.
    model_object.addProperty(
        "App::PropertyLength",
        "FrontBaseHoleX",
        "Hole positions",
    )
    model_object.FrontBaseHoleX = FRONT_BASE_HOLE_X

    model_object.addProperty(
        "App::PropertyLength",
        "RearBaseHoleX",
        "Hole positions",
    )
    model_object.RearBaseHoleX = REAR_BASE_HOLE_X

    model_object.addProperty(
        "App::PropertyLength",
        "BaseHoleY",
        "Hole positions",
    )
    model_object.BaseHoleY = BASE_HOLE_Y

    model_object.addProperty(
        "App::PropertyLength",
        "WallHoleDiameter",
        "Dimensions",
    )
    model_object.WallHoleDiameter = WALL_HOLE_DIAMETER

    model_object.addProperty(
        "App::PropertyLength",
        "LighteningHoleDiameter",
        "Dimensions",
    )
    model_object.LighteningHoleDiameter = LIGHTENING_HOLE_DIAMETER


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
        0.75,
        0.78,
        0.82,
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


def generate_mounting_bracket() -> None:
    """
    Generate the complete BRACKET-001 CAD model.
    """

    document_name = PART_NUMBER.replace("-", "_")

    close_existing_document(document_name)

    doc = App.newDocument(document_name)
    doc.Label = f"{PART_NUMBER} - {PART_NAME}"

    shape = create_mounting_bracket_shape()

    model_object = doc.addObject(
        "Part::Feature",
        "MountingBracket",
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
        generate_mounting_bracket()
        print("BRACKET-001 generated successfully.")

    except Exception:
        print("ERROR while generating BRACKET-001:")
        traceback.print_exc()
        raise