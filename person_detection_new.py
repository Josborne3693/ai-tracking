import numpy as np
import os
import six.moves.urllib as urllib
import sys
import tarfile
import tensorflow as tf
import zipfile
import pandas as pd

from collections import defaultdict
from io import StringIO
from matplotlib import pyplot as plt
from PIL import Image

config = tf.ConfigProto()
config.gpu_options.allow_growth = True
#config.gpu_options.per_process_gpu_memory_fraction = gpuAmount
session = tf.Session(config=config)

# recorded videos are 'jonathan.m4v' , 'petar.m4v'
# 'fletcher.m4v' , 'otherDude.m4v' , 'otherDude2.m4v'

# processed ones are 'jonathan.m4v' , 'petar.m4v'
# 'fletcher.m4v' , 'otherDude.m4v' , 'otherDude2.m4v'

os.chdir('/tensorflow/models/research/object_detection/')

videoName = "drone_footage_1.mp4"

import cv2
cap = cv2.VideoCapture(videoName)

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print width, height

# This is needed since the notebook is stored in the object_detection folder.
sys.path.append("..")


# ## Object detection imports
# Here are the imports from the object detection module.

# In[3]:

from utils import label_map_util

from utils import visualization_utils as vis_util


# # Model preparation

# ## Variables
#
# Any model exported using the `export_inference_graph.py` tool can be loaded here simply by changing `PATH_TO_CKPT` to point to a new .pb file.
#
# By default we use an "SSD with Mobilenet" model here. See the [detection model zoo](https://github.com/tensorflow/models/blob/master/object_detection/g3doc/detection_model_zoo.md) for a list of other models that can be run out-of-the-box with varying speeds and accuracies.

# In[4]:

# What model to download.
MODEL_NAME = 'ssd_mobilenet_v1_coco_11_06_2017'
MODEL_FILE = MODEL_NAME + '.tar.gz'
DOWNLOAD_BASE = 'http://download.tensorflow.org/models/object_detection/'

# Path to frozen detection graph. This is the actual model that is used for the object detection.
PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join('data', 'mscoco_label_map.pbtxt')

NUM_CLASSES = 90


# ## Download Model

# In[5]:
'''
opener = urllib.request.URLopener()
opener.retrieve(DOWNLOAD_BASE + MODEL_FILE, MODEL_FILE)
tar_file = tarfile.open(MODEL_FILE)
for file in tar_file.getmembers():
  file_name = os.path.basename(file.name)
  if 'frozen_inference_graph.pb' in file_name:
	tar_file.extract(file, os.getcwd())
'''
# ## Load a (frozen) Tensorflow model into memory.

# In[6]:

detection_graph = tf.Graph()
with detection_graph.as_default():
  od_graph_def = tf.GraphDef()
  with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
	serialized_graph = fid.read()
	od_graph_def.ParseFromString(serialized_graph)
	tf.import_graph_def(od_graph_def, name='')


# ## Loading label map
# Label maps map indices to category names, so that when our convolution network predicts `5`, we know that this corresponds to `airplane`.  Here we use internal utility functions, but anything that returns a dictionary mapping integers to appropriate string labels would be fine

# In[7]:

label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)


# ## Helper code

def load_image_into_numpy_array(image):
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape(
	  (im_height, im_width, 3)).astype(np.uint8)

# make directories for saving files
count = 1
saveDir = '/tf_files/people/'
dirName = os.path.splitext(videoName)[0] + '_' + str(count)
dirMade = False
while dirMade == False:
	try:
		os.mkdir(saveDir + 'save_threat_image/' + dirName)
		os.mkdir(saveDir + 'save_image/' + dirName)
		dirMade = True
	except OSError as exc:
		if count > 10:
			print(exc)
			sys.exit("Quitting program because more than 10 directories were found/made.")
		else:
			count += 1
		dirName = videoName + str(count)
		dirMade == False


# do the detection

frame = 0
person_frame_count = 1

with detection_graph.as_default():
	with tf.Session(graph=detection_graph) as sess:
		while True:
			frame = frame + 1
			print "frame: " + str(frame)
			ret, image_np = cap.read()
			# Expand dimensions since the model expects images to have shape: [1, None, None, 3]
			image_np_expanded = np.expand_dims(image_np, axis=0)
			image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
			# Each box represents a part of the image where a particular object was detected.
			boxes = detection_graph.get_tensor_by_name('detection_boxes:0')
			# Each score represent how level of confidence for each of the objects.
			# Score is shown on the result image, together with the class label.
			scores = detection_graph.get_tensor_by_name('detection_scores:0')
			classes = detection_graph.get_tensor_by_name('detection_classes:0')
			num_detections = detection_graph.get_tensor_by_name('num_detections:0')
			# Actual detection.
			try:
				(boxes, scores, classes, num_detections) = sess.run(
				[boxes, scores, classes, num_detections],
				feed_dict={image_tensor: image_np_expanded})
			except TypeError as exc:
				print exc
				sys.exit("Empty frame fed to detection, either the video is over or the connection was lost")

			# Convert tensorflow data to pandas data frams
			# print boxes
			df = pd.DataFrame(boxes.reshape(100, 4), columns=['y_min', 'x_min', 'y_max', 'x_max'])
			df1 = pd.DataFrame(classes.reshape(100, 1), columns=['classes'])
			df2 = pd.DataFrame(scores.reshape(100, 1), columns=['scores'])
			df5 = pd.concat([df, df1, df2], axis=1)

			# Transform box bound coordinates to pixel coordintate

			df5['y_min_t'] = df5['y_min'].apply(lambda x: x * height)
			df5['x_min_t'] = df5['x_min'].apply(lambda x: x * width)
			df5['y_max_t'] = df5['y_max'].apply(lambda x: x * height)
			df5['x_max_t'] = df5['x_max'].apply(lambda x: x * width)

			# Create objects pixel location x and y
			# X
			df5['ob_wid_x'] = df5['x_max_t'] - df5["x_min_t"]
			df5['ob_mid_x'] = df5['ob_wid_x'] / 2
			df5['x_loc'] = df5["x_min_t"] + df5['ob_mid_x']
			# Y
			df5['ob_hgt_y'] = df5['y_max_t'] - df5["y_min_t"]
			df5['ob_mid_y'] = df5['ob_hgt_y'] / 2
			df5['y_loc'] = df5["y_min_t"] + df5['ob_mid_y']

# Reviewed
########
			df6 = df5 #.loc[(df5['classes'] == 1 ) %  (df5['scores'] > person_threshold)]

			maxSavedFrames = 25

			# Scan People in Frame
			if (df6.empty) or (df6.iloc[0]['scores'] < .80):
				continue
			else:
				# A person was detected, get coordinates, display roi, save image
				w = int(df6.iloc[0]['ob_wid_x'])
				x = int(df6.iloc[0]['x_min_t'])
				h = int(df6.iloc[0]['ob_hgt_y'])
				y = int(df6.iloc[0]["y_min_t"])

				roi = image_np[y:y + h, x:x + w]

				cv2.imwrite(saveDir + 'save_threat_image/' + dirName + "/cap" + "-frame%d.jpg" % person_frame_count, roi)
				cv2.rectangle(image_np, (x,y), (x+ w, y+ h), (0, 0, 255), 10)
				cv2.imwrite(saveDir + 'save_image/' + dirName + "/cap" +"-frame%d.jpg" % person_frame_count, image_np)
				
				# only save maxSavedFrames # of frames
				# writes over frames
				#if person_frame_count == maxSavedFrames:
				#	person_frame_count = 1
				#else:
				person_frame_count += 1

			cv2.imshow('object detection', cv2.resize(image_np, (800,600)))
			if cv2.waitKey(25) & 0xFF == ord('q'):
				cv2.destroyAllWindows()
				break
		sess.close()


	  # Visualization of the results of a detection.
#      vis_util.visualize_boxes_and_labels_on_image_array(
#          image_np,
#          np.squeeze(boxes),
#          np.squeeze(classes).astype(np.int32),
#          np.squeeze(scores),
#          category_index,
#          use_normalized_coordinates=True,
#         line_thickness=8)
