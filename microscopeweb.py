import math
import statistics

import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates


st.set_page_config(
    page_title="Microscope Tool",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 Microscope Tool")


# ---------------------------------------------------------
# SESSION MEMORY
# ---------------------------------------------------------

def initialize_state():
    defaults = {
        "active_calibration": 1.52,
        "calibration_points": [],
        "calibration_last_click": None,
        "calibration_file_id": None,
        "measurement_points": [],
        "measurements": [],
        "measurement_last_click": None,
        "measurement_file_id": None,
    }

    for name, value in defaults.items():
        if name not in st.session_state:
            st.session_state[name] = value


initialize_state()


# ---------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------

def file_id(uploaded_file):
    return uploaded_file.name, uploaded_file.size


def click_token(clicked_point):
    timestamp = clicked_point.get("unix_timestamp")

    if timestamp is not None:
        return timestamp

    return clicked_point["x"], clicked_point["y"]


def draw_dot(draw, point, fill, outline="white", radius=2.5):
    x_value, y_value = point

    draw.ellipse(
        (
            x_value - radius,
            y_value - radius,
            x_value + radius,
            y_value + radius,
        ),
        fill=fill,
        outline=outline,
        width=1,
    )


# ---------------------------------------------------------
# MODE SELECTOR
# ---------------------------------------------------------

mode = st.radio(
    "Choose mode",
    ["Measure Defect", "Calibrate Scope"],
    horizontal=True,
)

st.caption(
    f"Active calibration: "
    f"{st.session_state.active_calibration:.4f} µm/pixel"
)


# =========================================================
# CALIBRATION MODE
# =========================================================

if mode == "Calibrate Scope":
    st.header("Calibrate the Scope")

    st.write(
        "Upload a sharp picture of a calibration slide or another "
        "known distance. Click the first mark and then the second mark."
    )

    calibration_file = st.file_uploader(
        "Upload calibration image",
        type=["jpg", "jpeg", "png", "bmp"],
        key="calibration_uploader",
    )

    if calibration_file is None:
        st.info("Upload a calibration image to begin.")
        st.stop()

    calibration_image = Image.open(calibration_file).convert("RGB")
    current_calibration_file_id = file_id(calibration_file)

    if current_calibration_file_id != st.session_state.calibration_file_id:
        st.session_state.calibration_file_id = current_calibration_file_id
        st.session_state.calibration_points = []
        st.session_state.calibration_last_click = None

    marked_calibration_image = calibration_image.copy()
    calibration_draw = ImageDraw.Draw(marked_calibration_image)

    if len(st.session_state.calibration_points) >= 1:
        draw_dot(
            calibration_draw,
            st.session_state.calibration_points[0],
            fill="yellow",
            outline="black",
            radius=6,
        )

    if len(st.session_state.calibration_points) == 2:
        point_1 = st.session_state.calibration_points[0]
        point_2 = st.session_state.calibration_points[1]

        draw_dot(
            calibration_draw,
            point_1,
            fill="red",
            radius=6,
        )
        draw_dot(
            calibration_draw,
            point_2,
            fill="red",
            radius=6,
        )
        calibration_draw.line(
            (point_1[0], point_1[1], point_2[0], point_2[1]),
            fill="lime",
            width=2,
        )

    calibration_click = streamlit_image_coordinates(
        marked_calibration_image,
        key="calibration_image",
        cursor="crosshair",
    )

    if calibration_click is not None:
        new_point = (
            calibration_click["x"],
            calibration_click["y"],
        )
        new_token = click_token(calibration_click)

        if new_token != st.session_state.calibration_last_click:
            st.session_state.calibration_last_click = new_token

            if len(st.session_state.calibration_points) >= 2:
                st.session_state.calibration_points = []

            st.session_state.calibration_points.append(new_point)
            st.rerun()

    calibration_columns = st.columns(2)

    known_distance = calibration_columns[0].number_input(
        "Known distance",
        min_value=0.0001,
        value=0.1,
        step=0.1,
        format="%.4f",
        help="Example: enter 0.1 and select mm for a 0.1 mm span.",
    )

    known_unit = calibration_columns[1].selectbox(
        "Known-distance unit",
        ["mm", "µm"],
    )

    if len(st.session_state.calibration_points) == 0:
        st.info("Click the first known mark on the calibration image.")

    elif len(st.session_state.calibration_points) == 1:
        first_point = st.session_state.calibration_points[0]
        st.info(
            f"First mark saved at X={first_point[0]}, Y={first_point[1]}. "
            f"Now click the second known mark."
        )

    else:
        point_1 = st.session_state.calibration_points[0]
        point_2 = st.session_state.calibration_points[1]

        pixel_span = math.hypot(
            point_2[0] - point_1[0],
            point_2[1] - point_1[1],
        )

        if known_unit == "mm":
            known_microns = known_distance * 1000.0
        else:
            known_microns = known_distance

        calculated_calibration = known_microns / pixel_span

        st.subheader("Calibration Result")

        result_columns = st.columns(3)
        result_columns[0].metric("Measured span", f"{pixel_span:.2f} px")
        result_columns[1].metric("Known span", f"{known_microns:.2f} µm")
        result_columns[2].metric(
            "Calculated calibration",
            f"{calculated_calibration:.4f} µm/px",
        )

        st.code(
            f"{known_microns:.2f} µm ÷ {pixel_span:.2f} px "
            f"= {calculated_calibration:.4f} µm/pixel"
        )

        if st.button(
            "Use This Calibration",
            type="primary",
        ):
            st.session_state.active_calibration = calculated_calibration
            st.success(
                f"Active calibration updated to "
                f"{calculated_calibration:.4f} µm/pixel. "
                f"Switch to Measure Defect mode when ready."
            )

    if st.button("Reset Calibration Points"):
        st.session_state.calibration_points = []
        st.session_state.calibration_last_click = None
        st.rerun()

    st.stop()


# =========================================================
# MEASUREMENT MODE
# =========================================================

st.header("Measure Defect")
st.write(
    "Upload a microscope image and click two endpoints for each measurement."
)

measurement_file = st.file_uploader(
    "Upload defect image",
    type=["jpg", "jpeg", "png", "bmp"],
    key="measurement_uploader",
)

if measurement_file is None:
    st.info("Upload a defect image to begin measuring.")
    st.stop()

measurement_image = Image.open(measurement_file).convert("RGB")
current_measurement_file_id = file_id(measurement_file)

if current_measurement_file_id != st.session_state.measurement_file_id:
    st.session_state.measurement_file_id = current_measurement_file_id
    st.session_state.measurement_points = []
    st.session_state.measurements = []
    st.session_state.measurement_last_click = None

microns_per_pixel = st.number_input(
    "Active calibration in µm per pixel",
    min_value=0.0001,
    value=float(st.session_state.active_calibration),
    step=0.01,
    format="%.4f",
)

st.session_state.active_calibration = microns_per_pixel

marked_measurement_image = measurement_image.copy()
measurement_draw = ImageDraw.Draw(marked_measurement_image)

for number, measurement in enumerate(
    st.session_state.measurements,
    start=1,
):
    point_1 = measurement["point_1"]
    point_2 = measurement["point_2"]
    pixels = measurement["pixels"]
    microns = pixels * microns_per_pixel

    draw_dot(measurement_draw, point_1, fill="red")
    draw_dot(measurement_draw, point_2, fill="red")

    measurement_draw.line(
        (point_1[0], point_1[1], point_2[0], point_2[1]),
        fill="lime",
        width=2,
    )

    midpoint_x = int((point_1[0] + point_2[0]) / 2)
    midpoint_y = int((point_1[1] + point_2[1]) / 2)

    measurement_draw.text(
        (midpoint_x + 6, midpoint_y - 14),
        f"#{number}: {microns:.1f} um",
        fill="yellow",
        stroke_width=2,
        stroke_fill="black",
    )

if len(st.session_state.measurement_points) == 1:
    draw_dot(
        measurement_draw,
        st.session_state.measurement_points[0],
        fill="yellow",
        outline="black",
    )

measurement_click = streamlit_image_coordinates(
    marked_measurement_image,
    key="measurement_image",
    cursor="crosshair",
)

if measurement_click is not None:
    new_point = (
        measurement_click["x"],
        measurement_click["y"],
    )
    new_token = click_token(measurement_click)

    if new_token != st.session_state.measurement_last_click:
        st.session_state.measurement_last_click = new_token
        st.session_state.measurement_points.append(new_point)

        if len(st.session_state.measurement_points) == 2:
            point_1 = st.session_state.measurement_points[0]
            point_2 = st.session_state.measurement_points[1]

            pixels = math.hypot(
                point_2[0] - point_1[0],
                point_2[1] - point_1[1],
            )

            st.session_state.measurements.append(
                {
                    "point_1": point_1,
                    "point_2": point_2,
                    "pixels": pixels,
                }
            )

            st.session_state.measurement_points = []

        st.rerun()

if len(st.session_state.measurement_points) == 0:
    st.info("Click the first endpoint of the next measurement.")
else:
    first_point = st.session_state.measurement_points[0]
    st.info(
        f"First endpoint saved at X={first_point[0]}, Y={first_point[1]}. "
        f"Now click the second endpoint."
    )

if st.session_state.measurements:
    micron_values = [
        measurement["pixels"] * microns_per_pixel
        for measurement in st.session_state.measurements
    ]

    count = len(micron_values)
    standard_deviation = (
        statistics.stdev(micron_values)
        if count >= 2
        else 0.0
    )

    st.subheader("Sample Statistics")
    stats = st.columns(6)
    stats[0].metric("Measurements", count)
    stats[1].metric("Mean", f"{statistics.mean(micron_values):.2f} µm")
    stats[2].metric("Median", f"{statistics.median(micron_values):.2f} µm")
    stats[3].metric("Minimum", f"{min(micron_values):.2f} µm")
    stats[4].metric("Maximum", f"{max(micron_values):.2f} µm")
    stats[5].metric("Std. Dev.", f"{standard_deviation:.2f} µm")

    rows = []

    for number, measurement in enumerate(
        st.session_state.measurements,
        start=1,
    ):
        rows.append(
            {
                "Measurement": number,
                "Pixels": round(measurement["pixels"], 2),
                "Microns": round(
                    measurement["pixels"] * microns_per_pixel,
                    2,
                ),
                "Point 1": str(measurement["point_1"]),
                "Point 2": str(measurement["point_2"]),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

st.subheader("Controls")
controls = st.columns(3)

if controls[0].button("Undo Last Measurement"):
    if st.session_state.measurement_points:
        st.session_state.measurement_points = []
    elif st.session_state.measurements:
        st.session_state.measurements.pop()

    st.session_state.measurement_last_click = None
    st.rerun()

if controls[1].button("Cancel Current Point"):
    st.session_state.measurement_points = []
    st.session_state.measurement_last_click = None
    st.rerun()

if controls[2].button("Clear Everything"):
    st.session_state.measurement_points = []
    st.session_state.measurements = []
    st.session_state.measurement_last_click = None
    st.rerun()
