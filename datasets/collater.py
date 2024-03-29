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

import paddle
from paddle.vision.transforms import Compose
import numpy as np
import numpy.random as npr
from utils.utils import Rescale, Normailize, Reshape


# TODO: keep_ratio

class Collater(object):
    """"""

    def __init__(self, scales, keep_ratio=False, multiple=32):
        if isinstance(scales, (int, float)):
            self.scales = np.array([scales], dtype=np.int32)
        else:
            self.scales = np.array(scales, dtype=np.int32)
        self.keep_ratio = keep_ratio
        self.multiple = multiple

    def __call__(self, batch):
        random_scale_inds = npr.randint(0, high=len(self.scales))
        target_size = self.scales[random_scale_inds]
        target_size = int(np.floor(float(target_size) / self.multiple) * self.multiple)
        rescale = Rescale(target_size=target_size, keep_ratio=self.keep_ratio)
        transform = Compose([Normailize(), Reshape(unsqueeze=False)])

        images = [sample['image'] for sample in batch]
        bboxes = [sample['boxes'] for sample in batch]
        batch_size = len(images)
        max_width, max_height = -1, -1
        for i in range(batch_size):
            im, _ = rescale(images[i])
            height, width = im.shape[0], im.shape[1]
            max_width = width if width > max_width else max_width
            max_height = height if height > max_height else max_height

        padded_ims = paddle.zeros([batch_size, 3, max_height, max_width])

        num_params = bboxes[0].shape[-1]
        max_num_boxes = max(bbox.shape[0] for bbox in bboxes)
        padded_boxes = paddle.ones([batch_size, max_num_boxes, num_params]) * -1
        for i in range(batch_size):
            im, bbox = images[i], bboxes[i]
            im, im_scale = rescale(im)
            height, width = im.shape[0], im.shape[1]
            padded_ims[i, :, :height, :width] = transform(im)
            if num_params < 9:
                bbox[:, :4] = bbox[:, :4] * im_scale
            else:
                bbox[:, :8] = bbox[:, :8] * np.hstack((im_scale, im_scale))
            padded_boxes[i, :bbox.shape[0], :] = paddle.to_tensor(bbox)
        return {'image': padded_ims, 'boxes': padded_boxes}
