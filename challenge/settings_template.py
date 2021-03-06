# -*- coding: utf-8 -*-
""" challenge settings  """

INPUT_FOLDER = 'input'

OUTPUT_FOLDER = 'output'

MODEL_CHECKPOINT = 'checkpoints/logs_test_size_0_2_512x512_pos_neg_sample/snapshot9350.ckpt'

CONFIG_FILE = 'config/yolov3_eval_digestpath.cfg'

USE_CUDA = True

CUT_SIZE = 512

OVERLAP = int(0.5 * CUT_SIZE)

BOARDCACHE = 2
