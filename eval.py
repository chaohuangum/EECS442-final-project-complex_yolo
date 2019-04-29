"""
    Evaluate on a single image. 
"""

import torch
import torch.nn as nn
from torch.autograd import Variable

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import time
import cv2
from scipy import misc
import os

from utils import *

def drawRect(img,pt1,pt2,pt3,pt4,color,lineWidth):
    cv2.line(img, pt1, pt2, color, lineWidth)
    cv2.line(img, pt2, pt3, color, lineWidth)
    cv2.line(img, pt3, pt4, color, lineWidth)
    cv2.line(img, pt1, pt4, color, lineWidth)

def get_region_boxes(output, conf_thresh, num_classes, anchors, num_anchors, only_objectness=1, validation=False):
    anchor_step = int(len(anchors)/num_anchors)
    if output.dim() == 3:
        output = output.unsqueeze(0)
    batch = output.size(0)
    assert(output.size(1) == (7+num_classes)*num_anchors)
    h = output.size(2)    #16
    w = output.size(3)    #32

    nB = output.data.size(0)
    nA = num_anchors     # num_anchors = 5
    nC = num_classes     # num_classes = 8
    nH = output.data.size(2)  # nH  16
    nW = output.data.size(3)  # nW  32
    anchor_step = int(len(anchors)/num_anchors)
    
    output   = output.view(nB, nA, (7+nC), nH, nW)
    x = torch.sigmoid(output.index_select(2, Variable(torch.cuda.LongTensor([0]))).view(nB, nA, nH, nW))
    y = torch.sigmoid(output.index_select(2, Variable(torch.cuda.LongTensor([1]))).view(nB, nA, nH, nW))
    w = output.index_select(2, Variable(torch.cuda.LongTensor([2]))).view(nB, nA, nH, nW)
    l = output.index_select(2, Variable(torch.cuda.LongTensor([3]))).view(nB, nA, nH, nW)
    im= output.index_select(2, Variable(torch.cuda.LongTensor([4]))).view(nB, nA, nH, nW)
    re= output.index_select(2, Variable(torch.cuda.LongTensor([5]))).view(nB, nA, nH, nW)
    conf = torch.sigmoid(output.index_select(2, Variable(torch.cuda.LongTensor([6]))).view(nB, nA, nH, nW))
    cls = output.index_select(2, Variable(torch.linspace(7,7+nC-1,nC).long().cuda()))
    cls = cls.view(nB*nA, nC, nH*nW).transpose(1,2).contiguous().view(nB*nA*nH*nW, nC)

    pred_boxes = torch.cuda.FloatTensor((7+nC), nB*nA*nH*nW)
    grid_x = torch.linspace(0, nW-1, nW).repeat(nH,1).repeat(nB*nA, 1, 1).view(nB*nA*nH*nW).cuda()
    grid_y = torch.linspace(0, nH-1, nH).repeat(nW,1).t().repeat(nB*nA, 1, 1).view(nB*nA*nH*nW).cuda()
    anchor_w = torch.Tensor(anchors).view(nA, anchor_step).index_select(1, torch.LongTensor([0])).cuda()
    anchor_l = torch.Tensor(anchors).view(nA, anchor_step).index_select(1, torch.LongTensor([1])).cuda()
    anchor_w = anchor_w.repeat(nB, 1).repeat(1, 1, nH*nW).view(nB*nA*nH*nW)
    anchor_l = anchor_l.repeat(nB, 1).repeat(1, 1, nH*nW).view(nB*nA*nH*nW)

    pred_boxes[0] = x.data.view(nB*nA*nH*nW).cuda() + grid_x
    pred_boxes[1] = y.data.view(nB*nA*nH*nW).cuda() + grid_y
    pred_boxes[2] = torch.exp(w.data).view(nB*nA*nH*nW).cuda() * anchor_w
    pred_boxes[3] = torch.exp(l.data).view(nB*nA*nH*nW).cuda() * anchor_l
    pred_boxes[4] = im.data.view(nB*nA*nH*nW).cuda()
    pred_boxes[5] = re.data.view(nB*nA*nH*nW).cuda()
    
    pred_boxes[6] = conf.data.view(nB*nA*nH*nW).cuda()
    pred_boxes[7:(7+nC)] = cls.data.view(nC,nB*nA*nH*nW).cuda()
    pred_boxes = convert2cpu(pred_boxes.transpose(0,1).contiguous().view(-1,(7+nC)))   #torch.Size([2560, 15])
    
    all_boxes =[]
    cls_predicted = []
    for i in range(2560):
        if pred_boxes[i][6]>conf_thresh:
            all_boxes.append(pred_boxes[i])
            _, tmp = torch.max(pred_boxes[i][7:].view(1, -1), 1)
            #print(tmp.shape)
            #print(tmp)
            cls_predicted.append(tmp.item())
    return all_boxes, cls_predicted

bc={}
bc['minX'] = 0; bc['maxX'] = 80; bc['minY'] = -40; bc['maxY'] = 40
bc['minZ'] =-2; bc['maxZ'] = 1.25

class_list = ['Car', 'Van' , 'Truck' , 'Pedestrian' , 'Person_sitting' , 'Cyclist' , 'Tram', 'Misc' ]
id_to_classes = dict(zip(range(8), class_list))

for file_i in range(100):
	print("Predicting image = %d" % file_i)
	test_i = str(file_i).zfill(6)

	cur_dir = '/home/ubuntu'
	lidar_file = cur_dir  +  '/KITTI/training/velodyne/' + test_i + '.bin'
	calib_file = cur_dir  +  '/KITTI/training/calib/' + test_i + '.txt'
	label_file = cur_dir  +  '/KITTI/training/label_2/' + test_i + '.txt'

	# load target data
	calib = load_kitti_calib(calib_file)  
	target = get_target(label_file, calib['Tr_velo2cam'])

	# load point cloud data
	a = np.fromfile(lidar_file, dtype=np.float32).reshape(-1, 4)
	b = removePoints(a,bc)
	rgb_map = makeBVFeature(b, bc , 40.0 / 512)
	misc.imsave('eval_output/eval_bv'+test_i+'.png', rgb_map)

	# load trained model  and  forward
	input = torch.from_numpy(rgb_map)       # (512, 1024, 3)
	input = input.reshape(1, 3, 512, 1024)
	model = torch.load('model/ComplexYOLO_epoch44') # original github set it to be 250
	model.cuda()
	
	# Set model.training to true so that batch normalization and dropout are engaged
	# model.train()
	model.eval()

	# Predict multiple times for each image
	num_predict = 1
	
	img = cv2.imread('eval_output/eval_bv'+test_i+'.png')

	# Paint ground truth
	true_boxes = []
	for j in range(103):
	    if target[j][1] == 0:
	      break
	    img_y = int(target[j][1] * 1024.0)   # 32 cell = 1024 pixels   
	    img_x = int(target[j][2] * 512.0)    # 16 cell = 512 pixels 
	    img_width  = int(target[j][3] * 1024.0)   # 32 cell = 1024 pixels   
	    img_height = int(target[j][4] * 512.0)    # 16 cell = 512 pixels 
	    rect_top1 = int(img_y - img_width / 2)
	    rect_top2 = int(img_x - img_height / 2)
	    rect_bottom1 = int(img_y + img_width / 2)
	    rect_bottom2 = int(img_x + img_height / 2)
	    cv2.rectangle(img, (rect_top1, rect_top2), (rect_bottom1,rect_bottom2), (0, 0, 255), 3)
	    label = id_to_classes[target[j][0]]
	    t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN,1,1)[0]
	    cv2.putText(img, label, (rect_top1, rect_top2), cv2.FONT_HERSHEY_PLAIN, 1.5, [0,0,255],1)

	    box = [rect_top2, rect_bottom2, rect_top1, rect_bottom1]
	    true_boxes.append(box)

	for k in range(num_predict):
		output = model(input.float().cuda())    #torch.Size([1, 75, 16, 32])

		# eval result
		conf_thresh   = 0.5
		num_classes = int(8)
		num_anchors = int(5)
		# g = cv2.imread('eval_bv.png')

		all_boxes, cls_predicted = get_region_boxes(output, conf_thresh, num_classes, anchors, num_anchors)
		
		# port pdb; pdb.set_trace()

		for i in range(len(all_boxes)):
		    #import pdb; pdb.set_trace()	
		    print("Box predicted!") 
		    pred_img_y = int(all_boxes[i][0]*1024.0 / 32.0)   # 32 cell = 1024 pixels   
		    pred_img_x = int(all_boxes[i][1]*512.0 / 16.0)    # 16 cell = 512 pixels 
		    pred_img_width  = int(all_boxes[i][2]*1024.0 / 32.0)   # 32 cell = 1024 pixels   
		    pred_img_height = int(all_boxes[i][3]*512.0 / 16.0)    # 16 cell = 512 pixels 


		    rect_top1 = int(pred_img_y-pred_img_width/2)
		    rect_top2 = int(pred_img_x-pred_img_height/2)
		    rect_bottom1 = int(pred_img_y+pred_img_width/2)
		    rect_bottom2 = int(pred_img_x+pred_img_height/2)
		    cv2.rectangle(img, (rect_top1,rect_top2), (rect_bottom1,rect_bottom2), (255,0,0), 3)
# 		    label = id_to_classes[cls_predicted[i]]
# 		    t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN,1,1)[0]
# 		    cv2.putText(img, label, (rect_top1, rect_top2), cv2.FONT_HERSHEY_PLAIN, 0.5, [255,0,0],1)
		    #print(label)
		    
		    box = [rect_top2, rect_bottom2, rect_top1, rect_bottom1]

	misc.imsave('eval_output/eval_bv_bbx' + test_i + '.png', img)
