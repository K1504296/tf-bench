from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tflite_runtime.interpreter as tflite
import os

import argparse
import io
import time
import numpy as np

from PIL import Image
from tflite_runtime.interpreter import Interpreter
from tvm.contrib.download import download_testdata


def load_test_image(height, width, dtype='float32'):
    image_url = 'https://github.com/dmlc/mxnet.js/blob/master/data/cat.png?raw=true'
    image_path = download_testdata(image_url, 'cat.png', module='data')
    resized_image = Image.open(image_path).resize((height, width))

    #image_data = np.asarray(resized_image).astype("float32")
    image_data = np.asarray(resized_image).astype(dtype)

    # Add a dimension to the image so that we have NHWC format layout
    image_data = np.expand_dims(image_data, axis=0)

    # Preprocess image as described here:
    # https://github.com/tensorflow/models/blob/edb6ed22a801665946c63d650ab9a0b23d98e1b1/research/slim/preprocessing/inception_preprocessing.py#L243
    image_data[:, :, :, 0] = 2.0 / 255.0 * image_data[:, :, :, 0] - 1
    image_data[:, :, :, 1] = 2.0 / 255.0 * image_data[:, :, :, 1] - 1
    image_data[:, :, :, 2] = 2.0 / 255.0 * image_data[:, :, :, 2] - 1    
    print('input', image_data.shape)
    return image_data

def set_input_tensor(interpreter, image):
  tensor_index = interpreter.get_input_details()[0]['index']
  input_tensor = interpreter.tensor(tensor_index)()[0]
  input_tensor[:, :] = image


def classify_image(interpreter, image, top_k=1):
  """Returns a sorted array of classification results."""
  set_input_tensor(interpreter, image)
  interpreter.invoke()
  output_details = interpreter.get_output_details()[0]
  output = np.squeeze(interpreter.get_tensor(output_details['index']))

  # If the model is quantized (uint8 data), then dequantize the results
  if output_details['dtype'] == np.uint8:
    scale, zero_point = output_details['quantization']
    output = scale * (output - zero_point)

  ordered = np.argpartition(-output, top_k)
  return [(i, output[i]) for i in ordered[:top_k]]

model_dir = './mobilenet_v2_1.0_224/'
model_name ='mobilenet_v2_1.0_224.tflite'
repeat=10

interpreter = tflite.Interpreter("../tvm-bench/"+ model_dir + model_name)
interpreter.allocate_tensors()

_, height, width, _ = interpreter.get_input_details()[0]['shape']
image = load_test_image(height, width, 'float32')

numpy_time = np.zeros(repeat)

for i in range(0,repeat):
     start_time = time.time()
     results = classify_image(interpreter, image)

     elapsed_ms = (time.time() - start_time) * 1000
     numpy_time[i] = elapsed_ms

print("tflite %-20s %-19s (%s)" % (model_name, "%.2f ms" % np.mean(numpy_time), "%.2f ms" % np.std(numpy_time)))

