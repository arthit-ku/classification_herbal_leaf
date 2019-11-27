from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# import argparse
# import sys
import os
import shutil
import time
import uuid
import atexit

import numpy as np
import tensorflow as tf
# import io

from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS
# , jsonify, send_from_directory
from flask import Flask, request, render_template, json

app = Flask(__name__,
            static_url_path='',
            static_folder='static',
            template_folder='templates')
app.secret_key = "super secret key"
CORS(app)


def clear_id():
    folder = 'tf/tf_files/uploads/user-images/'
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)
    return True


scheduler = BackgroundScheduler()
scheduler.add_job(func=clear_id, trigger="interval", hours=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

partLeaf = ["basil_leaf", "basil_leaf_notperfect", "chili_leaf", "chili_leaf_notperfect", "kaffir_lime_leaf",
            "kaffir_lime_leaf_notperfect", "lemon_basil_leaf", "lemon_basil_leaf_notperfect", "lemon_leaf",
            "lemon_leaf_notperfect", "mint_leaf", "mint_leaf_notperfect", "sweet_basil_leaf",
            "sweet_basil_leaf_notperfect"]


@app.route("/", methods=["GET"])
def main():
    return render_template('index.html')


@app.route("/predict", methods=["POST"])
def prepare():
    file = request.files['file']
    client_id = request.form.get("id")
    res = {}
    if(client_id == ""):
        res["status"] = "error"
        res["response"] = "id not found!"
    else:
        locate_file_path = "tf/tf_files/uploads/user-images/{}".format(
            client_id)
        if not os.path.exists(locate_file_path):
            os.makedirs(locate_file_path)
        res["status"] = "success"
        res["response"] = preprocessing(file, locate_file_path, client_id)
    return json.dumps(res)


@app.route("/save", methods=["POST"])
def save_img():
    leaf_path = request.form.get("leaf")
    client_id = request.form.get("id")
    res = {}
    if(client_id == ""):
        res["status"] = "error"
        res["response"] = "id not found!"
    else:
        full_path_id = "tf/tf_files/uploads/user-images/{}".format(client_id)
        full_path_leaf = "tf/tf_files/uploads/dataset/{}".format(leaf_path)
        if not os.path.exists(full_path_id):
            return "error id not found!"
        if not os.path.exists(full_path_leaf):
            os.makedirs(full_path_leaf)
        randomString = uuid.uuid4().hex
        randomString = randomString.lower()[0:10]
        shutil.move("{}/leaf.png".format(full_path_id),
                    "{}/{}.png".format(full_path_leaf, randomString))
        res["status"] = "success"
        res["response"] = "Saved"
    return json.dumps(res)


def preprocessing(file, locate_file_path, client_id):
    full_path_file_name = "{}/leaf.png".format(locate_file_path)
    file.save(full_path_file_name)  # saving uploaded img
    graph = load_graph(model_file)
    t = read_tensor_from_image_file(full_path_file_name,
                                    input_height=input_height,
                                    input_width=input_width,
                                    input_mean=input_mean,
                                    input_std=input_std)

    input_name = "import/" + input_layer
    output_name = "import/" + output_layer
    input_operation = graph.get_operation_by_name(input_name)
    output_operation = graph.get_operation_by_name(output_name)

    with tf.compat.v1.Session(graph=graph) as sess:
        start = time.time()
        results = sess.run(output_operation.outputs[0], {
                           input_operation.outputs[0]: t})
        end = time.time()
    results = np.squeeze(results)
    top_k = results.argsort()[-5:][::-1]
    labels = load_labels(label_file, True)

    Return = {}
    Return["time"] = '{:.3f}'.format(end-start)
    Return["results"] = []
    Return["leafs"] = []
    print('\nEvaluation time (1-image): {:.3f}s\n'.format(end-start))
    template = "{} (score={:0.5f})"
    leafPerfect = ["สมบูรณ์", "ไม่สมบูรณ์"]
    leafName = {
        "basil_leaf": ["กระเพรา", 0],
        "basil_leaf_notperfect": ["กระเพรา", 1],
        "chili_leaf": ["พริก", 0],
        "chili_leaf_notperfect": ["พริก", 1],
        "kaffir_lime_leaf": ["มะกรูด", 0],
        "kaffir_lime_leaf_notperfect": ["มะกรูด", 1],
        "lemon_basil_leaf": ["แมงลัก", 0],
        "lemon_basil_leaf_notperfect": ["แมงลัก", 1],
        "lemon_leaf": ["มะนาว", 0],
        "lemon_leaf_notperfect": ["มะนาว", 1],
        "mint_leaf": ["สะระแหน่", 0],
        "mint_leaf_notperfect": ["สะระแหน่", 1],
        "sweet_basil_leaf": ["โหระพา", 0],
        "sweet_basil_leaf_notperfect": ["โหระพา", 1]
    }
    for i in top_k:
        result = {}
        result["leaf"] = '{}'.format(labels[i])
        result["leafThai"] = leafName['{}'.format(labels[i])][0]
        result["perfect"] = leafPerfect[leafName['{}'.format(labels[i])][1]]
        result["percent"] = '{:0.2f}'.format(results[i]*100)
        Return["results"].append(result)
        print(template.format(labels[i], results[i]))
    for i in labels:
        result = {}
        result["leaf"] = i
        if notperfect_leaf is True:
            result["leafThai"] = 'ใบ{}{}'.format(
                leafName[i][0], leafPerfect[leafName[i][1]])
        else:
            result["leafThai"] = 'ใบ{}'.format(leafName[i][0])
        Return["leafs"].append(result)
    Return["notperfect_leaf"] = notperfect_leaf
    return Return


def load_graph(model_file):
    graph = tf.compat.v1.Graph()
    graph_def = tf.compat.v1.GraphDef()

    with open(model_file, "rb") as f:
        graph_def.ParseFromString(f.read())
    with graph.as_default():
        tf.import_graph_def(graph_def)

    return graph


def read_tensor_from_image_file(file_name, input_height=224, input_width=224, input_mean=0, input_std=255):
    input_name = "file_reader"
    # output_name = "normalized"
    file_reader = tf.compat.v1.read_file(file_name, input_name)
    if file_name.endswith(".png"):
        image_reader = tf.image.decode_png(
            file_reader, channels=3, name='png_reader')
    elif file_name.endswith(".gif"):
        image_reader = tf.squeeze(
            tf.image.decode_gif(file_reader, name='gif_reader'))
    elif file_name.endswith(".bmp"):
        image_reader = tf.image.decode_bmp(file_reader, name='bmp_reader')
    else:
        image_reader = tf.image.decode_jpeg(
            file_reader, channels=3, name='jpeg_reader')
    float_caster = tf.cast(image_reader, tf.float32)
    dims_expander = tf.expand_dims(float_caster, 0)
    resized = tf.compat.v1.image.resize_bilinear(
        dims_expander, [input_height, input_width])
    normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
    sess = tf.compat.v1.Session()
    result = sess.run(normalized)
    return result


def load_labels(label_file, path=False):
    label = []
    proto_as_ascii_lines = tf.compat.v1.gfile.GFile(label_file).readlines()
    for l in proto_as_ascii_lines:
        if(path):
            label.append(l.rstrip().replace(" ", "_"))
        else:
            label.append(l.rstrip())
    return label


if __name__ == "__main__":
    # enable notprefect mode
    notperfect_leaf = True
    file_name = "tf/tf_files/uploads/leaf.png"
    model_file = "tf/tf_files/retrained_graph.pb"
    label_file = "tf/tf_files/retrained_labels.txt"
    input_height = 224
    input_width = 224
    input_mean = 128
    input_std = 128
    # Mull , input , Placeholder
    input_layer = "input"
    output_layer = "final_result"
    # Flask init
    app.debug = True
    app.run(host='0.0.0.0', port=88)
