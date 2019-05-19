
# coding: utf-8

# In[1]:


import os
import numpy as np
from PIL import Image
from scipy.misc import imread, imresize, imsave
from scipy.misc import imresize

import tensorflow as tf

from tensorflow.contrib.slim.nets import inception


# In[2]:


slim = tf.contrib.slim
flags = tf.flags
FLAGS = tf.flags.FLAGS
tf.app.flags.DEFINE_string('f', '', 'kernel')
tf.flags.DEFINE_string(
    'master', '', 'The address of the TensorFlow master to use.')

tf.flags.DEFINE_string(
    'checkpoint_path','./inception_ckpt/inception_v3.ckpt', 'Path to checkpoint for inception network.')

tf.flags.DEFINE_string(
   'input_dir', './input_dir', 'Input directory with images.')

tf.flags.DEFINE_string(
   'output_dir', './output_dir', 'Output directory with images.')

tf.flags.DEFINE_integer(
    'image_width', 299, 'Width of each input images.')

tf.flags.DEFINE_integer(
    'image_height', 299, 'Height of each input images.')

tf.flags.DEFINE_integer(
    'image_resize', 330, 'Height of each input images.')

tf.flags.DEFINE_integer(
    'batch_size', 10, 'How many images process at one time.')

tf.flags.DEFINE_float(
    'max_epsilon', 16.0, 'Maximum size of adversarial perturbation.')

tf.flags.DEFINE_float(
    'prob', 0.5, 'probability of using diverse inputs.')

# if momentum = 1, this attack becomes M-DI-2-FGSM
tf.flags.DEFINE_float(
    'momentum', 0.0, 'Momentum.')

tf.flags.DEFINE_string(
    'GPU_ID', '0', 'which GPU to use.')


# In[3]:


def load_images(input_dir, output_dir, batch_shape):
    images = np.zeros(batch_shape)
    filenames = []
    idx = 0
    batch_size = batch_shape[0]
    for filepath in tf.gfile.Glob(os.path.join(input_dir, '*.png')):
        temp_name = str.split(filepath, '/')
        output_name = output_dir + '/'+ temp_name[-1]
        if os.path.isfile(output_name) == False:
            with tf.gfile.Open(filepath) as f:
                img = Image.open(filepath)
                img = img.convert("RGB")
                image = np.array(img).astype(np.float) / 255.0
            images[idx, :, :, :] = image * 2.0 - 1.0
            filenames.append(os.path.basename(filepath))
            idx += 1
        if idx == batch_size:
            yield filenames, images
            filenames = []
            images = np.zeros(batch_shape)
            idx = 0
    if idx > 0:
        yield filenames, images

def save_images(images, filenames, output_dir):
  """Saves images to the output directory.
  Args:
    images: array with minibatch of images
    filenames: list of filenames without path
      If number of file names in this list less than number of images in
      the minibatch then only first len(filenames) images will be saved.
    output_dir: directory where to save images
  """
  for i, filename in enumerate(filenames):
    # Images for inception classifier are normalized to be in [-1, 1] interval,
    # so rescale them back to [0, 1].
    with tf.gfile.Open(os.path.join(output_dir, filename), 'w') as f:
      imsave(f, (images[i, :, :, :] + 1.0) * 0.5 * 255, format='png')


def graph(x, y, i, x_max, x_min, grad):
  eps = 2.0 * FLAGS.max_epsilon / 255.0
  eps_iter = 2.0 / 255.0
  num_classes = 1001
  momentum = FLAGS.momentum

  with slim.arg_scope(inception.inception_v3_arg_scope()):
    logits, end_points = inception.inception_v3(
        input_diversity(x), num_classes=num_classes, is_training=False)
  pred = tf.argmax(end_points['Predictions'], 1)

  # here is the way to stable gt lables
  first_round = tf.cast(tf.equal(i, 0), tf.int64)
  y = first_round * pred + (1 - first_round) * y
  
  one_hot = tf.one_hot(y, num_classes)
  cross_entropy = tf.losses.softmax_cross_entropy(one_hot, logits)

  # compute the gradient info 
  noise = tf.gradients(cross_entropy, x)[0]
  noise = noise / tf.reduce_mean(tf.abs(noise), [1,2,3], keep_dims=True)
  # accumulate the gradient 
  noise = momentum * grad + noise

  x = x + eps_iter * tf.sign(noise)
  x = tf.clip_by_value(x, x_min, x_max)
  i = tf.add(i, 1)
  return x, y, i, x_max, x_min, noise


def stop(x, y, i, x_max, x_min, grad):
  num_iter = int(min(FLAGS.max_epsilon+4, 1.25*FLAGS.max_epsilon))
  return tf.less(i, num_iter)


def input_diversity(input_tensor):
  rnd = tf.random_uniform((), FLAGS.image_width, FLAGS.image_resize, dtype=tf.int32)
  rescaled = tf.image.resize_images(input_tensor, [rnd, rnd], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
  h_rem = FLAGS.image_resize - rnd
  w_rem = FLAGS.image_resize - rnd
  pad_top = tf.random_uniform((), 0, h_rem, dtype=tf.int32)
  pad_bottom = h_rem - pad_top
  pad_left = tf.random_uniform((), 0, w_rem, dtype=tf.int32)
  pad_right = w_rem - pad_left
  padded = tf.pad(rescaled, [[0, 0], [pad_top, pad_bottom], [pad_left, pad_right], [0, 0]], constant_values=0.)
  padded.set_shape((input_tensor.shape[0], FLAGS.image_resize, FLAGS.image_resize, 3))
  return tf.cond(tf.random_uniform(shape=[1])[0] < tf.constant(FLAGS.prob), lambda: padded, lambda: input_tensor)


def main(_):
  eps = 2.0 * FLAGS.max_epsilon / 255.0
  batch_shape = [FLAGS.batch_size, FLAGS.image_height, FLAGS.image_width, 3]

  with tf.Graph().as_default():
    # Prepare graph
    x_input = tf.placeholder(tf.float32, shape=batch_shape)
    x_max = tf.clip_by_value(x_input + eps, -1.0, 1.0)
    x_min = tf.clip_by_value(x_input - eps, -1.0, 1.0)

    y = tf.constant(np.zeros([FLAGS.batch_size]), tf.int64)
    i = tf.constant(0)
    grad = tf.zeros(shape=batch_shape)
    x_adv, _, _, _, _, _ = tf.while_loop(stop, graph, [x_input, y, i, x_max, x_min, grad])
    # Run computation
    saver = tf.train.Saver()
    with tf.Session() as sess:
      saver.restore(sess, FLAGS.checkpoint_path)
      for filenames, images in load_images(FLAGS.input_dir, FLAGS.output_dir, batch_shape):
        adv_images = sess.run(x_adv, feed_dict={x_input: images})
        save_images(adv_images, filenames, FLAGS.output_dir)


tf.app.run()

