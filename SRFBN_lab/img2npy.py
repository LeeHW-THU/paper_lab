# -*- coding: utf-8 -*-
# @Time    : 2019-05-23 18:10
# @Author  : LeeHW
# @File    : img2npy.py
# @Software: PyCharm
from flags import *
import os
from glob import glob
from scipy import misc
import numpy as np
from tqdm import tqdm

HR_path = os.path.join(save_dir, 'HR_x4')
LR_path = os.path.join(save_dir, 'LR_x4')
save_HR_npy_path = os.path.join(save_dir, 'HR_npy')
save_LR_npy_path = os.path.join(save_dir, 'LR_npy')
HR_list = sorted(glob(os.path.join(HR_path, '*.png')))
LR_list = sorted(glob(os.path.join(LR_path, '*.png')))
os.mkdir(save_HR_npy_path)
os.mkdir(save_LR_npy_path)


def img2npy(bar, save_npy_path):
	for path in bar:
		img = misc.imread(path)
		save_path = os.path.join(save_npy_path, os.path.basename(path).split('.')[0] + '.npy')
		np.save(save_path, img)


if __name__ == '__main__':
	print('===> Preparing HR binary file...')
	HR_bar = tqdm(HR_list)
	img2npy(HR_bar, save_HR_npy_path)
	print('===> Preparing LR binary file...')
	LR_bar = tqdm(LR_list)
	img2npy(LR_bar, save_LR_npy_path)
	print('===> Prepare OK...')
