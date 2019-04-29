# Complex YOLO for 3D bounding box on KITTI
## EECS442: Computer Vision Final Project
### Shengyu Feng, Chao Huang, Hanwen Miao, Yijiao Qin
This repo is a PyTorch implementation of complex yolo architecture proposed by Matin et.al in the paper https://arxiv.org/abs/1803.06199 
We train and evaluate our model on the challenging KITTI benchmark.
This repo is inspired by https://github.com/AI-liu/Complex-YOLO and https://github.com/wl5/complex_yolo_3d 	
Our further work includes:
1. Fix bugs in region_loss, shown in region_loss_v2;
2. Rewrite main.ipnb to train our model for our desired output;
3. Modify a great mount of codes and dismiss the unnecessary part to improve the readiability and effciency.

## Data
You need to download the dataset from http://www.cvlibs.net/datasets/kitti/eval_object.php?obj_benchmark=3d
The dataset needed in this project is the 12GB left color images and 29GB velodyn point cloud.

## Training
To train the model, you need to run main.py

## Predict
To see the predicted output, you should run eval.py

Note: You also need to modify the file path to match your own file path of dataset, to make the model work.