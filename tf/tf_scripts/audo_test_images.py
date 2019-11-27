from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
# import sys
import time
import os
import re
import csv

import numpy as np
import tensorflow as tf
from tensorflow.python.platform import gfile
import collections


def create_image_lists(image_dir):
    if not tf.compat.v1.gfile.Exists(image_dir):
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
    proto_as_ascii_lines = tf.compat.v1.gfile.GFile(label_file).readlines()
    for l in proto_as_ascii_lines:
        label.append(l.rstrip())
    return label


if __name__ == "__main__":
    image_dir = "tf/tf_files/datatest"
    file_name = "tf/tf_files/datatest/img.jpg"
    model_file = "tf/tf_files/retrained_graph.pb"
    label_file = "tf/tf_files/retrained_labels.txt"
    input_height = 224
    input_width = 224
    input_mean = 128
    input_std = 128
    input_layer = "input"
    output_layer = "final_result"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image_dir",
        type=str,
        default="tf/tf_files/datatest",
        help="image directory to be processed"
    )
    parser.add_argument(
        "--graph_dir",
        type=str,
        default='tf/tf_files/retrained_graphs',
        help="""\
      Path to classify_image_graph_def.pb,
      imagenet_synset_to_human_label_map.txt, and
      imagenet_2012_challenge_label_map_proto.pbtxt.\
      """
    )
    parser.add_argument(
        "--labels",
        type=str,
        default='tf/tf_files/retrained_labels.txt',
        help="name of file containing labels"
    )
    parser.add_argument(
        "--input_height",
        type=int,
        default=224,
        help="input height"
    )
    parser.add_argument(
        "--input_width",
        type=int,
        default=224,
        help="input width"
    )
    parser.add_argument(
        "--input_mean",
        type=int,
        default=128,
        help="input mean"
    )
    parser.add_argument(
        "--input_std",
        type=int,
        default=128,
        help="input std"
    )
    parser.add_argument(
        "--input_layer",
        type=str,
        default="input",
        help="name of input layer"
    )
    parser.add_argument(
        "--output_layer",
        type=str,
        default="final_result",
        help="name of output layer"
    )
    args = parser.parse_args()

    if args.graph_dir:
        model_dir = args.graph_dir
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

    label_results = create_image_lists(image_dir)
    input_WidthAndHeight = {
        'mobilenet_v1_1.0_224': 224,
        'mobilenet_v2_1.4_224': 224,
        'inception_v3': 299
    }
    input_layers = {
        'mobilenet_v1_1.0_224': 'input',
        'mobilenet_v2_1.4_224': 'input',
        'inception_v3': 'Mul'
    }
    model_name_list = ['mobilenet_v1_1.0_224',
                       'mobilenet_v2_1.4_224', 'inception_v3']
    learning_rate_list = ['0.0001', '0.0005',
                          '0.001', '0.005', '0.01', '0.05', '0.1']
    training_step_list = ['100', '200', '300', '400',
                          '500', '600', '700', '800', '900', '1000']
    testing_percentage_list = ['10', '20', '30']
    NO = 1
    with open("tests.csv", "w", newline="") as f:
        fieldnames = ['NO', 'model name', 'percent test', 'learning rate', 'training step', 'basil leaf', 'chili leaf',
                      'kaffir lime leaf', 'lemon basil leaf', 'lemon leaf', 'mint leaf', 'sweet basil leaf', 'time']
        TheWriter = csv.DictWriter(f, fieldnames=fieldnames)
        TheWriter.writeheader()
        for model_name in model_name_list:
            for percent_test in testing_percentage_list:
                for learning_rate in learning_rate_list:
                    for training_step in training_step_list:
                        model_file = "{}/retrained_graph_{}-PT{}-LR{}-TS{}.pb".format(
                            model_dir, model_name, percent_test, learning_rate, training_step)
                        graph = load_graph(model_file)
                        input_name = "import/" + input_layers[model_name]
                        output_name = "import/" + output_layer
                        input_operation = graph.get_operation_by_name(
                            input_name)
                        output_operation = graph.get_operation_by_name(
                            output_name)

                        sumary = {}
                        start = time.time()

                        for label_name, label_lists in label_results.items():
                            sumary[label_name] = {
                                "list_score": []
                            }
                            sum_score = 0
                            for index, img in enumerate(label_lists["test"]):
                                t = read_tensor_from_image_file(img,
                                                                input_height=input_WidthAndHeight[model_name],
                                                                input_width=input_WidthAndHeight[model_name],
                                                                input_mean=input_mean,
                                                                input_std=input_std)
                                with tf.Session(graph=graph) as sess:
                                    results = sess.run(output_operation.outputs[0], {
                                        input_operation.outputs[0]: t})
                                results = np.squeeze(results)
                                labels = load_labels(label_file)
                                labels_idx = dict([(value, idx)
                                                   for idx, value in enumerate(labels)])
                                score = results[labels_idx[label_name]]
                                sum_score += score
                                sumary[label_name]["list_score"].append(score)
                            sumary[label_name]["average"] = sum_score / \
                                len(sumary[label_name]["list_score"])
                        end = time.time()
                        # print(" >>> Test accuracy images <<<")
                        # print("use time {}".format(end - start))
                        row = {
                            'NO': NO,
                            'model name': model_name,
                            'percent test': percent_test,
                            'learning rate': learning_rate,
                            'training step': training_step,
                            'time': round(end - start, 2)
                        }
                        for leaf, leaf_scores in sumary.items():
                            row[leaf] = round(leaf_scores["average"]*100, 2)
                            # print("{} amount {} leafs ~ ~ ~ average of test accuracy: {:.2f}%".format(
                            #    leaf, len(leaf_scores["list_score"]), leaf_scores["average"]*100))
                        TheWriter.writerow(row)
                        NO = NO + 1
