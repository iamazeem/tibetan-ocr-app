import os
from typing import Optional

import cv2
import json
import math
import logging
import numpy as np
from uuid import uuid1
from PIL import Image, ImageOps
import numpy.typing as npt
from BudaOCR.Data import ScreenData, BBox, Line, LineData, LineDetectionConfig, LayoutDetectionConfig
from PySide6.QtWidgets import QApplication


page_classes = {
                "background" : "0, 0, 0",
                "image": "45, 255, 0",
                "line": "255, 100, 0",
                "margin": "255, 0, 0",
                "caption": "255, 100, 243"
            }


def get_screen_center(app: QApplication, start_size_ratio: float = 0.8) -> ScreenData:
    screen = app.primaryScreen()
    #print('Screen: %s' % screen.name())
    size = screen.size()
    #print('Size: %d x %d' % (size.width(), size.height()))
    rect = screen.availableGeometry()
    #print('Available: %d x %d' % (rect.width(), rect.height()))

    max_width = rect.width()
    max_height = rect.height()

    start_width = int(rect.width() * start_size_ratio)
    start_height = int(rect.height() * start_size_ratio)

    start_pos_x = (max_width - start_width) // 2
    start_pos_y = (max_height - start_height) // 2

    screen_data = ScreenData(
        max_width=max_width,
        max_height=max_height,
        start_width=start_width,
        start_height=start_height,
        start_x=start_pos_x,
        start_y=start_pos_y,
    )

    return screen_data

def get_filename(file_path: str) -> str:
    name_segments = os.path.basename(file_path).split(".")[:-1]
    name = "".join(f"{x}." for x in name_segments)
    return name.rstrip(".")


def generate_guid(clock_seq: int):
    return uuid1(clock_seq=clock_seq)


def read_theme_file(file_path: str) -> dict | None:
    if os.path.isfile(file_path):
        with open(file_path, "r") as f:
            content = json.load(f)

        return content
    else:
        logging.error(f"Theme File {file_path} does not exist")
        return None


def resize_to_height(image, target_height: int):
    scale_ratio = target_height / image.shape[0]
    image = cv2.resize(
        image,
        (int(image.shape[1] * scale_ratio), target_height),
        interpolation=cv2.INTER_LINEAR,
    )
    return image, scale_ratio


def resize_to_width(image, target_width: int = 2048):
    scale_ratio = target_width / image.shape[1]
    image = cv2.resize(
        image,
        (target_width, int(image.shape[0] * scale_ratio)),
        interpolation=cv2.INTER_LINEAR,
    )
    return image, scale_ratio

def calculate_steps(image: npt.NDArray, patch_size: int = 512) -> tuple[int, int]:
    x_steps = image.shape[1] / patch_size
    y_steps = image.shape[0] / patch_size

    x_steps = math.ceil(x_steps)
    y_steps = math.ceil(y_steps)

    return x_steps, y_steps


def calculate_paddings(
    image: npt.NDArray, x_steps: int, y_steps: int, patch_size: int = 512
) -> tuple[int, int]:
    max_x = x_steps * patch_size
    max_y = y_steps * patch_size
    pad_x = max_x - image.shape[1]
    pad_y = max_y - image.shape[0]

    return pad_x, pad_y


def pad_image(
    image: npt.NDArray, pad_x: int, pad_y: int, pad_value: int = 0
) -> npt.NDArray:
    padded_img = np.pad(
        image,
        pad_width=((0, pad_y), (0, pad_x), (0, 0)),
        mode="constant",
        constant_values=pad_value,
    )

    return padded_img


def pad_image2(
    img: np.array, patch_size: int = 64, is_mask=False, pad_value: int = 255
) -> tuple[np.array, tuple[int, int]]:
    x_pad = (math.ceil(img.shape[1] / patch_size) * patch_size) - img.shape[1]
    y_pad = (math.ceil(img.shape[0] / patch_size) * patch_size) - img.shape[0]

    if is_mask:
        pad_y = np.zeros(shape=(y_pad, img.shape[1], 3), dtype=np.uint8)
        pad_x = np.zeros(shape=(img.shape[0] + y_pad, x_pad, 3), dtype=np.uint8)
    else:
        pad_y = np.ones(shape=(y_pad, img.shape[1], 3), dtype=np.uint8)
        pad_x = np.ones(shape=(img.shape[0] + y_pad, x_pad, 3), dtype=np.uint8)
        pad_y *= pad_value
        pad_x *= pad_value

    img = np.vstack((img, pad_y))
    img = np.hstack((img, pad_x))

    return img, (x_pad, y_pad)


def patch_image(img: np.array, patch_size: int = 64) -> tuple[list[np.array], int]:
    """
    A simple slicing function.
    Expects input_image.shape[0] and image.shape[1] % patch_size = 0
    """

    y_steps = img.shape[0] // patch_size
    x_steps = img.shape[1] // patch_size

    patches = []

    for y_step in range(0, y_steps):
        for x_step in range(0, x_steps):
            x_start = x_step * patch_size
            x_end = (x_step * patch_size) + patch_size

            crop_patch = img[
                y_step * patch_size: (y_step * patch_size) + patch_size, x_start:x_end
            ]
            patches.append(crop_patch)

    return patches, y_steps


def generate_patches(
    image: npt.NDArray, x_steps: int, y_steps: int, patch_size: int = 512
) -> list[npt.NDArray]:
    patches = []

    for y_idx in range(y_steps):
        for x_idx in range(x_steps):
            if x_idx < x_steps:
                start_y = y_idx * patch_size
                end_y = y_idx * patch_size + patch_size
                start_x = x_idx * patch_size
                end_x = x_idx * patch_size + patch_size
                img_patch = image[start_y:end_y, start_x:end_x]

                if img_patch.shape[0] != 0 and img_patch.shape[1] != 0:
                    if img_patch.shape[1] < patch_size:
                        pad_width = patch_size - img_patch.shape[1]
                        patch = np.zeros(
                            shape=(img_patch.shape[0], pad_width, 3), dtype=np.uint8
                        )
                        img_patch = np.hstack([img_patch, patch])
                        img_patch = cv2.resize(img_patch, (patch_size, patch_size))
                        img_patch = img_patch.astype(np.uint8)
                        patches.append(img_patch)
                    else:
                        img_patch = cv2.resize(img_patch, (patch_size, patch_size))
                        patches.append(img_patch)

    return patches


def unpatch_image(image, pred_patches: list) -> np.array:
    patch_size = pred_patches[0].shape[1]

    x_step = math.ceil(image.shape[1] / patch_size)

    list_chunked = [
        pred_patches[i : i + x_step] for i in range(0, len(pred_patches), x_step)
    ]

    final_out = np.zeros(shape=(1, patch_size * x_step))

    for y_idx in range(0, len(list_chunked)):
        x_stack = list_chunked[y_idx][0]

        for x_idx in range(1, len(list_chunked[y_idx])):
            patch_stack = np.hstack((x_stack, list_chunked[y_idx][x_idx]))
            x_stack = patch_stack

        final_out = np.vstack((final_out, x_stack))

    final_out = final_out[1:, :]
    final_out *= 255

    return final_out

def get_contours(image: npt.NDArray) -> list:
    contours, _ = cv2.findContours(image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    return contours

def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def get_text_area(
    image: np.array, prediction: np.array
) -> tuple[np.array, BBox] | tuple[None, None, None]:
    dil_kernel = np.ones((12, 2))
    dil_prediction = cv2.dilate(prediction, kernel=dil_kernel, iterations=10)

    prediction = cv2.resize(prediction, (image.shape[1], image.shape[0]))
    dil_prediction = cv2.resize(dil_prediction, (image.shape[1], image.shape[0]))

    contours, _ = cv2.findContours(dil_prediction, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    if len(contours) > 0:
        area_mask = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.float32)

        area_sizes = [cv2.contourArea(x) for x in contours]
        biggest_area = max(area_sizes)
        biggest_idx = area_sizes.index(biggest_area)

        x, y, w, h = cv2.boundingRect(contours[biggest_idx])
        color = (255, 255, 255)

        cv2.rectangle(
            area_mask,
            (x, y),
            (x + w, y + h),
            color,
            -1,
        )
        area_mask = cv2.cvtColor(area_mask, cv2.COLOR_BGR2GRAY)

        return prediction, area_mask, contours[biggest_idx]
    else:
        return None, None, None

def build_line_data(contour: npt.NDArray) -> Line:
    x, y, w, h = cv2.boundingRect(contour)
    x_center = x + (w // 2)
    y_center = y + (h // 2)

    bbox = BBox(x, y, w, h)
    return Line(contour, bbox, (x_center, y_center))

def mask_n_crop(image: np.array, mask: np.array) -> np.array:
    image = image.astype(np.uint8)
    mask = mask.astype(np.uint8)

    if len(image.shape) == 2:
        image = np.expand_dims(image, axis=-1)

    image_masked = cv2.bitwise_and(image, image, mask, mask)
    image_masked = np.delete(
        image_masked, np.where(~image_masked.any(axis=1))[0], axis=0
    )
    image_masked = np.delete(
        image_masked, np.where(~image_masked.any(axis=0))[0], axis=1
    )

    return image_masked


def calculate_rotation_angle_from_lines(
    line_mask: np.array,
    max_angle: float = 5.0,
    debug_angles: bool = False,
) -> float:
    contours, _ = cv2.findContours(line_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    mask_threshold = (line_mask.shape[0] * line_mask.shape[1]) * 0.001
    contours = [x for x in contours if cv2.contourArea(x) > mask_threshold]
    angles = [cv2.minAreaRect(x)[2] for x in contours]

    low_angles = [x for x in angles if abs(x) != 0.0 and x < max_angle]
    high_angles = [x for x in angles if abs(x) != 90.0 and x > (90 - max_angle)]

    if debug_angles:
        print(f"All Angles: {angles}")

    if len(low_angles) > len(high_angles) and len(low_angles) > 0:
        mean_angle = np.mean(low_angles)

    # check for clockwise rotation
    elif len(high_angles) > 0:
        mean_angle = -(90 - np.mean(high_angles))

    else:
        mean_angle = 0

    return mean_angle


def rotate_from_angle(image: np.array, angle: float) -> np.array:
    rows, cols = image.shape[:2]
    rot_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), angle, 1)

    rotated_img = cv2.warpAffine(image, rot_matrix, (cols, rows), borderValue=(0, 0, 0))

    return rotated_img


def get_rotation_angle_from_lines(
    line_mask: npt.NDArray,
    max_angle: float = 5.0,
    debug_angles: bool = False,
) -> float:
    contours, _ = cv2.findContours(line_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    mask_threshold = (line_mask.shape[0] * line_mask.shape[1]) * 0.001
    contours = [x for x in contours if cv2.contourArea(x) > mask_threshold]
    angles = [cv2.minAreaRect(x)[2] for x in contours]

    low_angles = [x for x in angles if abs(x) != 0.0 and x < max_angle]
    high_angles = [x for x in angles if abs(x) != 90.0 and x > (90 - max_angle)]

    if debug_angles:
        print(f"All Angles: {angles}")

    if len(low_angles) > len(high_angles) and len(low_angles) > 0:
        mean_angle = np.mean(low_angles)

    # check for clockwise rotation
    elif len(high_angles) > 0:
        mean_angle = -(90 - np.mean(high_angles))

    else:
        mean_angle = 0

    return mean_angle


def pol2cart(theta, rho):
    x = rho * np.cos(theta)
    y = rho * np.sin(theta)
    return x, y


def cart2pol(x, y):
    theta = np.arctan2(y, x)
    rho = np.hypot(x, y)
    return theta, rho


def rotate_contour(cnt, center, angle):
    cx = center[0]
    cy = center[1]

    cnt_norm = cnt - [cx, cy]

    coordinates = cnt_norm[:, 0, :]
    xs, ys = coordinates[:, 0], coordinates[:, 1]
    thetas, rhos = cart2pol(xs, ys)

    thetas = np.rad2deg(thetas)
    thetas = (thetas + angle) % 360
    thetas = np.deg2rad(thetas)

    xs, ys = pol2cart(thetas, rhos)

    cnt_norm[:, 0, 0] = xs
    cnt_norm[:, 0, 1] = ys

    cnt_rotated = cnt_norm + [cx, cy]
    cnt_rotated = cnt_rotated.astype(np.int32)

    return cnt_rotated


def is_inside_rectangle(point, rect):
    x, y = point
    xmin, ymin, xmax, ymax = rect
    return xmin <= x <= xmax and ymin <= y <= ymax


def filter_contours(prediction: np.array, textarea_contour: np.array) -> list[np.array]:
    filtered_contours = []
    x, y, w, h = cv2.boundingRect(textarea_contour)
    line_contours, _ = cv2.findContours(
        prediction, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )

    for cnt in line_contours:
        center, _, angle = cv2.minAreaRect(cnt)
        is_in_area = is_inside_rectangle(center, [x, y, x + w, y + h])

        if is_in_area:
            filtered_contours.append(cnt)

    return filtered_contours


def post_process_prediction(image: np.array, prediction: np.array):
    prediction, text_area, textarea_contour = get_text_area(image, prediction)

    if prediction is not None:
        cropped_prediction = mask_n_crop(prediction, text_area)
        angle = calculate_rotation_angle_from_lines(cropped_prediction)

        rotated_image = rotate_from_angle(image, angle)
        rotated_prediction = rotate_from_angle(prediction, angle)

        M = cv2.moments(textarea_contour)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        rotated_textarea_contour = rotate_contour(textarea_contour, (cx, cy), angle)

        return rotated_image, rotated_prediction, rotated_textarea_contour, angle
    else:
        return None, None, None, None


def generate_line_preview(prediction: np.array, filtered_contours: list[np.array]):
    preview = np.zeros(shape=prediction.shape, dtype=np.uint8)

    for cnt in filtered_contours:
        cv2.drawContours(preview, [cnt], -1, color=(255, 0, 0), thickness=-1)

    return preview


def optimize_countour(cnt, e=0.001):
    epsilon = e * cv2.arcLength(cnt, True)
    return cv2.approxPolyDP(cnt, epsilon, True)


def build_line_data(contour: np.array, optimize: bool = True) -> Line:
    if optimize:
        contour = optimize_countour(contour)

    x, y, w, h = cv2.boundingRect(contour)
    x_center = x + (w // 2)
    y_center = y + (h // 2)

    bbox = BBox(x, y, w, h)

    return Line(contour, bbox, (x_center, y_center))


def get_line_threshold(line_prediction: np.array, slice_width: int = 20):
    """
    This function generates n slices (of n = steps) width the width of slice_width across the bbox of the detected lines.
    The slice with the max. number of contained contours is taken to be the canditate to calculate the bbox center of each contour and
    take the median distance between each bbox center as estimated line cut-off threshold to sort each line segment across the horizontal

    Note: This approach might turn out to be problematic in case of sparsely spread line segments across a page
    """

    x, y, w, h = cv2.boundingRect(line_prediction)
    x_steps = (w // slice_width) // 2

    bbox_numbers = []

    for step in range(1, x_steps + 1):
        x_offset = x_steps * step
        x_start = x + x_offset
        x_end = x_start + slice_width

        _slice = line_prediction[y : y + h, x_start:x_end]
        contours, _ = cv2.findContours(_slice, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        bbox_numbers.append((len(contours), contours))

    sorted_list = sorted(bbox_numbers, key=lambda x: x[0], reverse=True)

    if len(sorted_list) > 0:
        reference_slice = sorted_list[0]

        y_points = []
        n_contours, contours = reference_slice

        if n_contours == 0:
            logging.warning("number of contours is 0")
            line_threshold = 0
        else:
            for _, contour in enumerate(contours):
                x, y, w, h = cv2.boundingRect(contour)
                y_center = y + (h // 2)
                y_points.append(y_center)

            line_threshold = np.median(y_points) // n_contours
    else:
        line_threshold = 0

    return line_threshold


def sort_bbox_centers(bbox_centers: list[tuple[int, int]], line_threshold: int = 20):
    sorted_bbox_centers = []
    tmp_line = []

    for i in range(0, len(bbox_centers)):
        if len(tmp_line) > 0:
            for s in range(0, len(tmp_line)):

                # TODO: refactor this to make this calculation an enum to choose between both methods
                # y_diff = abs(tmp_line[s][1] - bbox_centers[i][1])
                """
                I use the mean of the hitherto present line chunks in tmp_line since
                the precalculated fixed threshold can break the sorting if
                there is some slight bending in the line. This part may need some tweaking after
                some further practical review
                """
                ys = [y[1] for y in tmp_line]
                mean_y = np.mean(ys)
                y_diff = abs(mean_y - bbox_centers[i][1])

                if y_diff > line_threshold:
                    tmp_line.sort(key=lambda x: x[0])
                    sorted_bbox_centers.append(tmp_line.copy())
                    tmp_line.clear()

                    tmp_line.append(bbox_centers[i])
                    break
                else:
                    tmp_line.append(bbox_centers[i])
                    break
        else:
            tmp_line.append(bbox_centers[i])

    sorted_bbox_centers.append(tmp_line)

    for y in sorted_bbox_centers:
        y.sort(key=lambda x: x[0])

    sorted_bbox_centers = list(reversed(sorted_bbox_centers))

    return sorted_bbox_centers


def group_line_chunks(sorted_bbox_centers, lines: list[Line]):
    new_line_data = []
    for bbox_centers in sorted_bbox_centers:

        if len(bbox_centers) > 1:  # i.e. more than 1 bbox center in a group
            contour_stack = []

            for box_center in bbox_centers:
                for line_data in lines:
                    if box_center == line_data.center:
                        contour_stack.append(line_data.contour)
                        break

            stacked_contour = np.vstack(contour_stack)
            stacked_contour = cv2.convexHull(stacked_contour)
            # TODO: are both calls necessary?
            x, y, w, h = cv2.boundingRect(stacked_contour)
            _bbox = BBox(x, y, w, h)
            x_center = _bbox.x + (_bbox.w // 2)
            y_center = _bbox.y + (_bbox.h // 2)

            new_line = Line(
                contour=stacked_contour, bbox=_bbox, center=(x_center, y_center)
            )

            new_line_data.append(new_line)

        else:
            for _bcenter in bbox_centers:
                for line_data in lines:
                    if _bcenter == line_data.center:
                        new_line_data.append(line_data)
                        break

    return new_line_data


def sort_lines_by_threshold(
    line_mask: np.array,
    lines: list[Line],
    threshold: int = 20,
    calculate_threshold: bool = True,
    group_lines: bool = True,
    debug: bool = False,
):
    bbox_centers = [x.center for x in lines]

    if calculate_threshold:
        line_treshold = get_line_threshold(line_mask)
    else:
        line_treshold = threshold

    if debug:
        print(f"Line threshold: {threshold}")

    sorted_bbox_centers = sort_bbox_centers(bbox_centers, line_threshold=line_treshold)

    if debug:
        print(sorted_bbox_centers)

    if group_lines:
        new_lines = group_line_chunks(sorted_bbox_centers, lines)
    else:
        _bboxes = [x for xs in sorted_bbox_centers for x in xs]

        new_lines = []
        for _bbox in _bboxes:
            for _line in lines:
                if _bbox == _line.center:
                    new_lines.append(_line)

    return new_lines, line_treshold


def sort_lines_by_threshold2(
    line_mask: npt.NDArray,
    lines: list[Line],
    threshold: int = 20,
    calculate_threshold: bool = True,
    group_lines: bool = True,
    debug: bool = False,
):

    bbox_centers = [x.center for x in lines]

    if calculate_threshold:
        line_treshold = get_line_threshold(line_mask)
    else:
        line_treshold = threshold

    if debug:
        print(f"Line threshold: {threshold}")

    sorted_bbox_centers = sort_bbox_centers(bbox_centers, line_threshold=line_treshold)

    if debug:
        print(sorted_bbox_centers)

    if group_lines:
        new_lines = group_line_chunks(sorted_bbox_centers, lines)
    else:
        _bboxes = [x for xs in sorted_bbox_centers for x in xs]

        new_lines = []
        for _bbox in _bboxes:
            for _line in lines:
                if _bbox == _line.center:
                    new_lines.append(_line)

    return new_lines, line_treshold


def get_line_data(image: npt.NDArray, line_mask: npt.NDArray, group_chunks: bool = True) -> LineData:
    angle = get_rotation_angle_from_lines(line_mask)

    rot_mask = rotate_from_angle(line_mask, angle)
    rot_img = rotate_from_angle(image, angle)

    line_contours = get_contours(rot_mask)
    line_data = [build_line_data(x) for x in line_contours]
    line_data = [x for x in line_data if x.bbox.h > 10]
    sorted_lines, _ = sort_lines_by_threshold2(rot_mask, line_data, group_lines=group_chunks)

    data = LineData(rot_img, rot_mask, angle, sorted_lines)

    return data


def extract_line(line: Line, image: np.array, k_factor: float = 1.2) -> np.array:
    """
    Add an optional recursive loop to check that the resulting line is not higher than 2x the bbox_H or
    has any height that is non-sensical in view of the height of the entire image
    """

    bbox_h = line.bbox.h

    tmp_img = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
    cv2.drawContours(tmp_img, [line.contour], -1, (255, 255, 255), -1)
    k_size = int(bbox_h * k_factor)
    morph_rect = cv2.getStructuringElement(shape=cv2.MORPH_RECT, ksize=(k_size, k_size))
    iterations = 1
    tmp_img = cv2.dilate(tmp_img, kernel=morph_rect, iterations=iterations)
    masked_line = mask_n_crop(image, tmp_img)

    return masked_line

def extract_line_images(data: LineData, k_factor: float = 0.75):
    line_images = [extract_line(x, data.image, k_factor) for x in data.lines]
    return line_images

def normalize(image: npt.NDArray) -> npt.NDArray:
    image = image.astype(np.float32)
    image /= 255.0
    return image


def binarize(
        img: np.array, adaptive: bool = True, block_size: int = 51, c: int = 13
) -> np.array:
    line_img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    if adaptive:
        bw = cv2.adaptiveThreshold(
            line_img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c,
        )

    else:
        _, bw = cv2.threshold(line_img, 120, 255, cv2.THRESH_BINARY)

    bw = cv2.cvtColor(bw, cv2.COLOR_GRAY2RGB)
    return bw

def pad_to_width(img: np.array, target_width: int, target_height: int, padding: str) -> np.array:
    _, width, channels = img.shape
    tmp_img, ratio = resize_to_width(img, target_width)

    height = tmp_img.shape[0]
    middle = (target_height - tmp_img.shape[0]) // 2

    if padding == "white":
        upper_stack = np.ones(shape=(middle, target_width, channels), dtype=np.uint8)
        lower_stack = np.ones(shape=(target_height - height - middle, target_width, channels), dtype=np.uint8)

        upper_stack *= 255
        lower_stack *= 255
    else:
        upper_stack = np.zeros(shape=(middle, target_width, channels), dtype=np.uint8)
        lower_stack = np.zeros(shape=(target_height - height - middle, target_width, channels), dtype=np.uint8)

    out_img = np.vstack([upper_stack, tmp_img, lower_stack])

    return out_img


def pad_to_height(img: np.array, target_width: int, target_height: int, padding: str) -> np.array:
    height, _, channels = img.shape
    tmp_img, ratio = resize_to_height(img, target_height)

    width = tmp_img.shape[1]
    middle = (target_width - width) // 2

    if padding == "white":
        left_stack = np.ones(shape=(target_height, middle, channels), dtype=np.uint8)
        right_stack = np.ones(shape=(target_height, target_width - width - middle, channels), dtype=np.uint8)

        left_stack *= 255
        right_stack *= 255

    else:
        left_stack = np.zeros(shape=(target_height, middle, channels), dtype=np.uint8)
        right_stack = np.zeros(shape=(target_height, target_width - width - middle, channels), dtype=np.uint8)

    out_img = np.hstack([left_stack, tmp_img, right_stack])

    return out_img

def pad_ocr_line(
        img: np.array,
        target_width: int = 2000,
        target_height: int = 80,
        padding: str = "black") -> np.array:

    width_ratio = target_width / img.shape[1]
    height_ratio = target_height / img.shape[0]

    if width_ratio < height_ratio:
        out_img = pad_to_width(img, target_width, target_height, padding)

    elif width_ratio > height_ratio:
        out_img = pad_to_height(img, target_width, target_height, padding)
    else:
        out_img = pad_to_width(img, target_width, target_height, padding)

    return cv2.resize(out_img, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

def prepare_ocr_line(image: np.array, target_width: int = 2000, target_height: int = 80):
    line_image = pad_ocr_line(image)
    line_image = cv2.cvtColor(line_image, cv2.COLOR_BGR2GRAY)
    line_image = line_image.reshape((1, target_height, target_width))
    line_image = line_image / 255.0
    line_image = line_image.astype(np.float32)

    return line_image


def read_line_model_config(config_file: str) -> LineDetectionConfig:
    model_dir = os.path.dirname(config_file)
    file = open(config_file, encoding="utf-8")
    json_content = json.loads(file.read())

    onnx_model_file = f"{model_dir}/{json_content['onnx-model']}"
    patch_size = int(json_content["patch_size"])

    config = LineDetectionConfig(onnx_model_file, patch_size)

    return config


def read_layout_model_config(config_file: str) -> LayoutDetectionConfig:
    model_dir = os.path.dirname(config_file)
    file = open(config_file, encoding="utf-8")
    json_content = json.loads(file.read())

    onnx_model_file = f"{model_dir}/{json_content['onnx-model']}"
    patch_size = int(json_content["patch_size"])
    classes = json_content["classes"]

    config = LayoutDetectionConfig(onnx_model_file, patch_size, classes)

    return config

def create_preview_image(
            image: np.array,
            image_predictions: Optional,
            line_predictions: Optional,
            caption_predictions: Optional,
            margin_predictions: Optional,
            alpha: float = 0.4,
    ) -> np.array:
        mask = np.zeros(image.shape, dtype=np.uint8)

        if image_predictions is not None and len(image_predictions) > 0:
            color = tuple([int(x) for x in page_classes["image"].split(",")])

            for idx, _ in enumerate(image_predictions):
                cv2.drawContours(
                    mask, image_predictions, contourIdx=idx, color=color, thickness=-1
                )

        if line_predictions is not None:
            color = tuple([int(x) for x in page_classes["line"].split(",")])

            for idx, _ in enumerate(line_predictions):
                cv2.drawContours(
                    mask, line_predictions, contourIdx=idx, color=color, thickness=-1
                )

        if len(caption_predictions) > 0:
            color = tuple([int(x) for x in page_classes["caption"].split(",")])

            for idx, _ in enumerate(caption_predictions):
                cv2.drawContours(
                    mask, caption_predictions, contourIdx=idx, color=color, thickness=-1
                )

        if len(margin_predictions) > 0:
            color = tuple([int(x) for x in page_classes["margin"].split(",")])

            for idx, _ in enumerate(margin_predictions):
                cv2.drawContours(
                    mask, margin_predictions, contourIdx=idx, color=color, thickness=-1
                )

        cv2.addWeighted(mask, alpha, image, 1 - alpha, 0, image)

        return image


def generate_alpha_mask(mask: Image.Image):
    mask = mask.convert("L")
    alpha_mask = ImageOps.colorize(mask, black="red", white="black")
    alpha_mask = alpha_mask.convert("RGBA")
    array = np.array(alpha_mask, dtype=np.ubyte)
    mask = (array[:, :, :3] == (0, 0, 0)).all(axis=2)
    alpha = np.where(mask, 0, 255)
    array[:, :, -1] = alpha
    alpha_mask = Image.fromarray(np.ubyte(array))
    alpha_mask.putalpha(128)

    return alpha_mask