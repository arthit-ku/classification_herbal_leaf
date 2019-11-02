from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
# import sys
import time
import os
import re

import numpy as np
import tensorflow as tf
from tensorflow.python.platform import gfile
import collections


def create_image_lists(image_dir):
    if not gfile.Exists(image_dir):
        tf.logging.error("Image directory '" + image_dir + "' not found.")
        return None
    result = collections.OrderedDict()
    sub_dirs = [
        os.path.join(image_dir, item)
        for item in gfile.ListDirectory(image_dir)]
    sub_dirs = sorted(item for item in sub_dirs
                      if gfile.IsDirectory(item))
    for sub_dir in sub_dirs:
        extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp']
        file_list = []
        dir_name = os.path.basename(sub_dir)
        if dir_name == image_dir:
            continue
        tf.logging.info("Looking for images in '" + dir_name + "'")
        for extension in extensions:
            file_glob = os.path.join(image_dir, dir_name, '*.' + extension)
            file_list.extend(gfile.Glob(file_glob))
        if not file_list:
            tf.logging.warning('No files found')
            continue
        label_name = re.sub(r'[^a-z0-9]+', ' ', dir_name.lower())
        result[label_name] = {
            'dir': dir_name,
            'test': file_list
        }
    return result


def load_graph(model_file):
    graph = tf.Graph()
    graph_def = tf.GraphDef()

    with open(model_file, "rb") as f:
        graph_def.ParseFromString(f.read())
    with graph.as_default():
        tf.import_graph_def(graph_def)

    return graph


def read_tensor_from_image_file(file_name, input_height=299, input_width=299, input_mean=0, input_std=255):
    input_name = "file_reader"
    # output_name = "normalized"
    file_reader = tf.read_file(file_name, input_name)
    if file_name.endswith(".png"):
        image_reader = tf.image.decode_png(file_reader, channels=3,
                                           name='png_reader')
    elif file_name.endswith(".gif"):
        image_reader = tf.squeeze(tf.image.decode_gif(file_reader,
                                                      name='gif_reader'))
    elif file_name.endswith(".bmp"):
        image_reader = tf.image.decode_bmp(file_reader, name='bmp_reader')
    else:
        image_reader = tf.image.decode_jpeg(file_reader, channels=3,
                                            name='jpeg_reader')
    float_caster = tf.cast(image_reader, tf.float32)
    dims_expander = tf.expand_dims(float_caster, 0)
    resized = tf.image.resize_bilinear(
        dims_expander, [input_height, input_width])
    normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
    sess = tf.Session()
    result = sess.run(normalized)

    return result


def load_labels(label_file):
    label = []
    proto_as_ascii_lines = tf.gfile.GFile(label_file).readlines()
    for l in proto_as_ascii_lines:
        label.append(l.rstrip())
    return label


if __name__ == "__main__":
    image_dir = "tf_files/datatest"
    file_name = "tf_files/datatest/img.jpg"
    model_file = "tf_files/retrained_graph.pb"
    label_file = "tf_files/retrained_labels.txt"
    input_height = 224
    input_width = 224
    input_mean = 128
    input_std = 128
    input_layer = "input"
    output_layer = "final_result"

    parser = argparse.ArgumentParser()
    parser.add_argument("--image_dir", help="image directory to be processed")
    parser.add_argument("--graph", help="graph/model to be executed")
    parser.add_argument("--labels", help="name of file containing labels")
    parser.add_argument("--input_height", type=int, help="input height")
    parser.add_argument("--input_width", type=int, help="input width")
    parser.add_argument("--input_mean", type=int, help="input mean")
    parser.add_argument("--input_std", type=int, help="input std")
    parser.add_argument("--input_layer", help="name of input layer")
    parser.add_argument("--output_layer", help="name of output layer")
    args = parser.parse_args()

    if args.graph:
        model_file = args.graph
    if args.image_dir:
        image_dir = args.image_dir
    if args.labels:
        label_file = args.labels
    if args.input_height:
        input_height = args.input_height
    if args.input_width:
        input_width = args.input_width
    if args.input_mean:
        input_mean = args.input_mean
    if args.input_std:
        input_std = args.input_std
    if args.input_layer:
        input_layer = args.input_layer
    if args.output_layer:
        output_layer = args.output_layer
    graph = load_graph(model_file)
    label_results = create_image_lists(image_dir)

    input_name = "import/" + input_layer
    output_name = "import/" + output_layer
    input_operation = graph.get_operation_by_name(input_name)
    output_operation = graph.get_operation_by_name(output_name)

    sumary = {}
    for label_name, label_lists in label_results.items():
        sumary[label_name] = {
            "list_score": []
        }
        sum_score = 0
        for index, img in enumerate(label_lists["test"]):
            t = read_tensor_from_image_file(img,
                                            input_height=input_height,
                                            input_width=input_width,
                                            input_mean=input_mean,
                                            input_std=input_std)
            with tf.Session(graph=graph) as sess:
                start = time.time()
                results = sess.run(output_operation.outputs[0], {
                                   input_operation.outputs[0]: t})
                end = time.time()
            results = np.squeeze(results)
            labels = load_labels(label_file)
            labels_idx = dict([(value, idx)
                               for idx, value in enumerate(labels)])
            score = results[labels_idx[label_name]]
            sum_score += score
            sumary[label_name]["list_score"].append(score)
        sumary[label_name]["average"] = sum_score / \
            len(sumary[label_name]["list_score"])
    print("Test accuracy images")
    for leaf, leaf_scores in sumary.items():
        print("{} amount {} leafs ~ ~ ~ average of test accuracy: {:.2f}%".format(
            leaf, len(leaf_scores["list_score"]), leaf_scores["average"]*100))
