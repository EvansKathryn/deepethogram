"""
Based on code from Nvidia's FlowNet2
Copyright 2017 NVIDIA CORPORATION

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Changes: 2D -> 3D. changed filter sizes, number of input images, number of layers... only kept their naming
convention and overall structure
"""
from .components import *
import warnings

class TinyMotionNet3D(nn.Module):
    def __init__(self, num_images=11, input_channels=3, batchnorm=True, flow_div=1,
                 channel_base=16):
        super().__init__()
        self.num_images = num_images
        if input_channels is None:
            self.input_channels = self.num_images * 3
        else:
            self.input_channels = int(input_channels)

        # self.out_channels = int((num_images-1)*2)
        self.batchnorm = batchnorm
        bias = not self.batchnorm
        warnings.warn('ignoring flow div value of {}: setting to 1 instead'.format(flow_div))
        self.flow_div = 1

        self.channels = [channel_base * (2 ** i) for i in range(0, 3)]
        print(self.channels)

        self.conv1 = conv3d(self.input_channels, self.channels[0], kernel_size=7, batchnorm=batchnorm, bias=bias)
        self.conv2 = conv3d(self.channels[0], self.channels[1], stride=(1, 2, 2), kernel_size=5, batchnorm=batchnorm,
                            bias=bias)
        self.conv3 = conv3d(self.channels[1], self.channels[2], stride=(1, 2, 2), batchnorm=batchnorm, bias=bias)
        self.conv4 = conv3d(self.channels[2], self.channels[1], stride=(1, 2, 2), batchnorm=batchnorm, bias=bias)

        self.conv5 = conv3d(self.channels[1], self.channels[1], kernel_size=(2, 3, 3), batchnorm=batchnorm, bias=bias)

        self.deconv3 = deconv3d(self.channels[1], self.channels[1], kernel_size=(1, 4, 4), stride=(1, 2, 2),
                                padding=(0, 1, 1),
                                batchnorm=batchnorm, bias=bias)
        self.deconv2 = deconv3d(self.channels[1], self.channels[0], kernel_size=(1, 4, 4), stride=(1, 2, 2),
                                padding=(0, 1, 1),
                                batchnorm=batchnorm, bias=bias)

        self.iconv3 = conv3d(self.channels[2], self.channels[2], kernel_size=(2, 3, 3), batchnorm=batchnorm, bias=bias)
        self.iconv2 = conv3d(self.channels[1], self.channels[1], kernel_size=(2, 3, 3), batchnorm=batchnorm, bias=bias)

        self.xconv3 = conv3d(self.channels[1] + self.channels[2] + 2, self.channels[1], batchnorm=batchnorm, act=False)
        self.xconv2 = conv3d(self.channels[0] + self.channels[1] + 2, self.channels[0], batchnorm=batchnorm, act=False)

        self.predict_flow4 = predict_flow_3d(self.channels[1], 2)
        self.predict_flow3 = predict_flow_3d(self.channels[1], 2)
        self.predict_flow2 = predict_flow_3d(self.channels[0], 2)

        self.upsampled_flow4_to_3 = nn.ConvTranspose3d(2, 2, kernel_size=(1, 4, 4), stride=(1, 2, 2), padding=(0, 1, 1))
        # self.upsampled_flow4_to_3 = nn.ConvTranspose3d(2, 2, kernel_size=(1,4,4), stride=(1,2,2), padding=1)
        self.upsampled_flow3_to_2 = nn.ConvTranspose3d(2, 2, kernel_size=(1, 4, 4), stride=(1, 2, 2), padding=(0, 1, 1))

        self.concat = CropConcat(dim=1)
        # self.interpolate = Interpolate

    def forward(self, x):
        # N, C, T, H, W = x.shape
        out_conv1 = self.conv1(x)  # 1 -> 1
        # print('out_conv1:      {}'.format(out_conv1.shape))
        out_conv2 = self.conv2(out_conv1)  # 1 -> 1/2
        # print('out_conv2:      {}'.format(out_conv2.shape))
        out_conv3 = self.conv3(out_conv2)  # 1/2 -> 1/4
        # print('out_conv3:      {}'.format(out_conv3.shape))
        out_conv4 = self.conv4(out_conv3)  # 1/4 -> 1/8
        # print('out_conv4:      {}'.format(out_conv4.shape))
        out_conv5 = self.conv5(out_conv4)
        # print('out_conv5:      {}'.format(out_conv5.shape))

        flow4 = self.predict_flow4(out_conv5) * self.flow_div
        # print('flow4:          {}'.format(flow4.shape))
        # see motionnet.py for explanation of multiplying by 2
        flow4_up = self.upsampled_flow4_to_3(flow4) * 2
        # print('flow4_up:       {}'.format(flow4_up.shape))
        out_deconv3 = self.deconv3(out_conv5)
        # print('out_deconv3:    {}'.format(out_deconv3.shape))

        iconv3 = self.iconv3(out_conv3)
        # print('iconv3:         {}'.format(iconv3.shape))
        concat3 = self.concat((iconv3, out_deconv3, flow4_up))
        # print('concat3:        {}'.format(concat3.shape))
        out_interconv3 = self.xconv3(concat3)

        # print('out_interconv3: {}'.format(out_interconv3.shape))
        flow3 = self.predict_flow3(out_interconv3) * self.flow_div
        # print('flow3:          {}'.format(flow3.shape))
        flow3_up = self.upsampled_flow3_to_2(flow3) * 2
        # print('flow3_up:       {}'.format(flow3_up.shape))
        out_deconv2 = self.deconv2(out_interconv3)
        # print('out_deconv2:    {}'.format(out_deconv2.shape))

        iconv2 = self.iconv2(out_conv2)
        # print('iconv2:         {}'.format(iconv2.shape))

        concat2 = self.concat((iconv2, out_deconv2, flow3_up))
        # print('concat2:        {}'.format(concat2.shape))
        out_interconv2 = self.xconv2(concat2)
        # print('out_interconv2: {}'.format(out_interconv2.shape))
        flow2 = self.predict_flow2(out_interconv2) * self.flow_div
        # print('flow2:          {}'.format(flow2.shape))

        return flow2, flow3, flow4