# -*- coding: utf-8 -*-
# @Time    : 2019-05-23 19:10
# @Author  : LeeHW
# @File    : train.py
# @Software: PyCharm
import tensorflow as tf
import numpy as np
b = np.load('/Users/hongweili/Desktop/THU_lab/papers_lab/SRFBN_lab/data/Prepare/HR_npy/0001_rot0_ds0.npy')
HR=tf.Tensor(op='test',value_index=b.shape,dtype=float)
print(b.shape)
