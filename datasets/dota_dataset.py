# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import cv2
import sys
sys.path.append('/home/aistudio/work/DAL')
sys.path.append('/home/aistudio/external-libraries')
import numpy as np
from paddle.io import Dataset

from utils.augment import *
from utils.utils import plot_gt
from utils.bbox import quad_2_rbox


class DOTADataset(Dataset):

    def __init__(self,
                 dataset=None,
                 augment=False,
                 level=1,
                 only_latin=True):
        super(DOTADataset, self).__init__()
        self.level = level
        self.image_set_path = dataset
        if dataset is not None:
            self.image_list = self._load_image_names()
        if self.level == 1:
            self.classes = ('__background__', 'plane', 'ship', 'storage-tank', 'baseball-diamond',
                            'tennis-court', 'basketball-court', 'ground-track-field', 'harbor',
                            'bridge', 'large-vehicle', 'small-vehicle', 'helicopter', 'roundabout',
                            'soccer-ball-field', 'swimming-pool')
        self.num_classes = len(self.classes)
        self.class_to_ind = dict(zip(self.classes, range(self.num_classes)))
        self.augment = augment

    def __len__(self):
        return len(self.image_list)

    def __getitem__(self, index):
        im_path = self.image_list[index]
        im = cv2.cvtColor(cv2.imread(im_path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        roidb = self._load_annotation(self.image_list[index])
        gt_inds = np.where(roidb['gt_classes'] != 0)[0]
        bboxes = roidb['boxes'][gt_inds, :]
        classes = roidb['gt_classes'][gt_inds]
        gt_boxes = np.zeros((len(gt_inds), 6), dtype=np.float32)
        if self.augment:
            transform = Augment([HSV(0.5, 0.5, p=0.5),
                                 HorizontalFlip(p=0.5),
                                 VerticalFlip(p=0.5),
                                 Affine(degree=20, translate=0.1, scale=0.2, p=0.5),
                                 Noise(0.02, p=0.2),
                                 Blur(1.3, p=0.5),
                                 ], box_mode='xyxyxyxy', )
            im, bboxes = transform(im, bboxes)

        mask = mask_valid_boxes(quad_2_rbox(bboxes, 'xywha'), return_mask=True)
        bboxes = bboxes[mask]
        gt_boxes = gt_boxes[mask]
        classes = classes[mask]

        for i, bbox in enumerate(bboxes):
            gt_boxes[i, :5] = quad_2_rbox(np.array(bbox), mode='xyxya')
            gt_boxes[i, 5] = classes[i]

        ## test augmentation
        # plot_gt(im, gt_boxes[:,:-1], im_path, mode = 'xyxya')
        # print(im_path)
        return {'image': im, 'boxes': gt_boxes, 'path': im_path}

    def _load_image_names(self):
        """
        Load the names listed in this dataset's image set file.
        """
        image_set_file = self.image_set_path
        assert os.path.exists(image_set_file), \
            'Path does not exist: {}'.format(image_set_file)
        with open(image_set_file) as f:
            image_list = [x.strip() for x in f.readlines()]
        return image_list

    def _load_annotation(self, index):  # index = '/home3/victory8858/dataset/DOTA_Split/train/images/P0000__1__0___0.png'
        root_dir = index.split('/images/P')[0]  # root_dir:  /home3/victory8858/dataset/DOTA_Split/train
        # print(root_dir)
        label_dir = os.path.join(root_dir,'labelTxt')  # label_dir:  /home3/victory8858/dataset/DOTA_Split/train\labelTxt
        _, img_name = os.path.split(index)  # P0000__1__0___0.png
        filename = os.path.join(label_dir, img_name[:-4] + '.txt')  # '/home3/victory8858/dataset/DOTA_Split/train\\labelTxt\\P0000__1__0___0.txt'
        boxes, gt_classes = [], []
        with open(filename, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            objects = content.split('\n')
            for obj in objects:
                if len(obj) != 0:
                    *box, class_name, difficult = obj.split(' ')
                    if difficult == '1' or difficult == '2':
                        continue
                    box = [eval(x) for x in obj.split(' ')[:8]]
                    label = self.class_to_ind[class_name]
                    boxes.append(box)
                    gt_classes.append(label)
        return {'boxes': np.array(boxes, dtype=np.int32), 'gt_classes': np.array(gt_classes)}

    def display(self, boxes, img_path):
        img = cv2.imread(img_path)
        for box in boxes:
            coors = box.reshape(4, 2)
            img = cv2.polylines(img, [coors], True, (0, 0, 255), 2)
        cv2.imshow(img_path, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def return_class(self, id):
        id = int(id)
        return self.classes[id]


if __name__ == '__main__':
    train_data = DOTADataset(dataset='/home/aistudio/data/DOTA/trainval.txt')
    print(train_data[4])
