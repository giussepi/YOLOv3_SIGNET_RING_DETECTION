# -*- coding: utf-8 -*-

import argparse
import yaml

import cv2
import torch
from torch.autograd import Variable
import matplotlib
import matplotlib.pyplot as plt


from constants import BOX_COLOR
from models.yolov3 import *
from utils.utils import *
from utils.parse_yolo_weights import parse_yolo_weights
from utils.vis_bbox import vis_bbox


def main():
    """
    Visualize the detection result for the given image and the pre-trained model.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpu', type=int, default=0)
    parser.add_argument('--cfg', type=str, default='config/yolov3_default.cfg')
    parser.add_argument('--ckpt', type=str,
                        help='path to the checkpoint file')
    parser.add_argument('--weights_path', type=str,
                        default=None, help='path to weights file')
    parser.add_argument('--image', type=str)
    parser.add_argument('--background', action='store_true',
                        default=False, help='background(no-display mode. save "./output.png")')
    parser.add_argument('--detect_thresh', type=float,
                        default=None, help='confidence threshold')
    args = parser.parse_args()

    with open(args.cfg, 'r') as f:
        cfg = yaml.load(f)

    imgsize = cfg['TEST']['IMGSIZE']
    model = YOLOv3(cfg['MODEL'])

    confthre = cfg['TEST']['CONFTHRE']
    nmsthre = cfg['TEST']['NMSTHRE']

    if args.detect_thresh:
        confthre = args.detect_thresh

    img = cv2.imread(args.image)
    img_raw = img.copy()[:, :, ::-1].transpose((2, 0, 1))
    img, info_img = preprocess(img, imgsize, jitter=0)  # info = (h, w, nh, nw, dx, dy)
    img = np.transpose(img / 255., (2, 0, 1))
    img = torch.from_numpy(img).float().unsqueeze(0)

    if args.gpu >= 0:
        model.cuda(args.gpu)
        img = Variable(img.type(torch.cuda.FloatTensor))
    else:
        img = Variable(img.type(torch.FloatTensor))

    assert args.weights_path or args.ckpt, 'One of --weights_path and --ckpt must be specified'

    if args.weights_path:
        print("loading yolo weights %s" % (args.weights_path))
        parse_yolo_weights(model, args.weights_path)
    elif args.ckpt:
        print("loading checkpoint %s" % (args.ckpt))
        state = torch.load(args.ckpt)
        if 'model_state_dict' in state.keys():
            model.load_state_dict(state['model_state_dict'])
        else:
            model.load_state_dict(state)

    model.eval()

    with torch.no_grad():
        outputs = model(img)
        outputs = postprocess(outputs, 80, confthre, nmsthre)

    if outputs[0] is None:
        print("No Objects Deteted!!")
        return

    bboxes = list()
    colors = list()

    for x1, y1, x2, y2, conf, cls_conf, cls_pred in outputs[0]:
        print(int(x1), int(y1), int(x2), int(y2), float(conf), int(cls_pred))
        print('\t+ Conf: %.5f' % cls_conf.item())
        box = yolobox2label([y1, x1, y2, x2], info_img)
        bboxes.append(box)
        colors.append(BOX_COLOR)

    if args.background:
        matplotlib.use('Agg')

    vis_bbox(
        img_raw, bboxes, instance_colors=colors, linewidth=2)
    plt.show()

    if args.background:
        plt.savefig('output.png')


if __name__ == '__main__':
    main()