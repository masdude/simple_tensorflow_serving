import sys
import io
import os
import logging
import numpy as np
from PIL import Image


def get_image_channel_layout(request_layout, support_signatures=None):
    """
    Try select a channel layout by requested layout and model signatures
    """
    layout = request_layout
    if support_signatures is not None:
        # get input tensor "image"
        for item in support_signatures["inputs"]:
            if item["name"] == "image":
                shape = item["shape"]
                if len(shape) == 4:
                    channel_size = shape[-1]
                    if channel_size == 1:
                        layout = "L"
                    elif channel_size == 3:
                        layout = "RGB"
                    elif channel_size == 4:
                        layout = "RGBA"
                break
    return layout


def get_image_request_data_and_options(request, support_signatures=None, save_file_dir=None):
    """
    Get data items for image application
    :return: (numpy.ndarray, image specific options dict)
    """
    options = {}
    image_file = request.files["image"]
    image_content = image_file.read()
    image_string = np.fromstring(image_content, np.uint8)
    if sys.version_info[0] < 3:
        import cStringIO
        image_string_io = cStringIO.StringIO(image_string)
    else:
        image_string_io = io.BytesIO(image_string)

    if save_file_dir is not None:
        with open(os.path.join(save_file_dir, image_file.filename), "wb") as save_file:
            save_file.write(image_content)

    image_file = Image.open(image_string_io)

    channel_layout = request.form.get("channel_layout", "RGB")
    channel_layout = get_image_channel_layout(channel_layout, support_signatures)
    if channel_layout in ["RGB", "RGBA"]:
        if channel_layout != str(image_file.mode):
            logging.info("Convert image from %s to %s" % (image_file.mode, channel_layout))
            image_file = image_file.convert(channel_layout)
    else:
        logging.error("Illegal image_layout: {}".format(channel_layout))

    image_array = np.array(image_file)

    # TODO: Support multiple images without reshaping
    if "shape" in request.form:
        # Example: "32,32,1,3" -> (32, 32, 1, 3)
        shape = tuple([int(item) for item in request.form["shape"].split(",")])
        image_array = image_array.reshape(shape)
    else:
        image_array = image_array.reshape(1, *image_array.shape)

    return image_array, options


def create_json_from_formdata_request(request, support_signatures=None, save_file_dir=None):
    json_data = {}

    # general arguments
    if "model_version" in request.form:
        json_data["model_version"] = int(request.form["model_version"])
    if "run_profile" in request.form:
        json_data["run_profile"] = request.form["run_profile"]

    # decide upload file type based on file key
    if "image" in request.files:
        data, options = get_image_request_data_and_options(
            request, support_signatures, save_file_dir)
        json_data["data"] = {"image": data}
        for key in options:
            json_data[key] = options[key]
    else:
        raise Exception("Unknown file type, must be image")
    return json_data
