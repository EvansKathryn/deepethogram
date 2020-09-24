import os
import numpy as np
import subprocess

from deepethogram import utils

from setup_data import get_testing_directory

testing_directory = get_testing_directory()
config_path = os.path.join(testing_directory, 'project_config.yaml')
BATCH_SIZE = 4 # small but not too small
# if less than 10, might have bugs with visualization
STEPS_PER_EPOCH = 20
NUM_EPOCHS = 2

def command_from_string(string):
    command = string.split(' ')
    if command[-1] == '':
        command = command[:-1]
    return command

def add_default_arguments(string, train=True):
    string += f'project.config_file={config_path} '
    string += f'compute.batch_size={BATCH_SIZE} '
    if train:
        string += f'train.steps_per_epoch.train={STEPS_PER_EPOCH} train.steps_per_epoch.val={STEPS_PER_EPOCH} '
        string += f'train.steps_per_epoch.test={STEPS_PER_EPOCH} '
        string += f'train.num_epochs={NUM_EPOCHS} '
    return string

def test_flow():
    string = (f'python -m deepethogram.flow_generator.train preset=deg_f ')
    string = add_default_arguments(string)
    command = command_from_string(string)
    ret = subprocess.run(command)
    assert ret.returncode == 0

    string = (f'python -m deepethogram.flow_generator.train preset=deg_m ')
    string = add_default_arguments(string)
    command = command_from_string(string)
    ret = subprocess.run(command)
    assert ret.returncode == 0

    string = (f'python -m deepethogram.flow_generator.train preset=deg_s ')
    string = add_default_arguments(string)
    command = command_from_string(string)
    ret = subprocess.run(command)
    assert ret.returncode == 0

def test_feature_extractor():
    string = (f'python -m deepethogram.feature_extractor.train preset=deg_f flow_generator.weights=latest ')
    string = add_default_arguments(string)
    command = command_from_string(string)
    ret = subprocess.run(command)
    assert ret.returncode == 0

    string = (f'python -m deepethogram.feature_extractor.train preset=deg_m flow_generator.weights=latest ')
    string = add_default_arguments(string)
    command = command_from_string(string)
    ret = subprocess.run(command)
    assert ret.returncode == 0

    # for resnet3d, must specify weights, because we can't just download them from the torchvision repo
    string = (f'python -m deepethogram.feature_extractor.train preset=deg_s flow_generator.weights=latest '
              f'feature_extractor.weights=latest ')
    string = add_default_arguments(string)
    command = command_from_string(string)
    ret = subprocess.run(command)
    assert ret.returncode == 0

def test_feature_extraction():
    # the reason for this complexity is that I don't want to run inference on all directories
    string = (f'python -m deepethogram.feature_extractor.inference preset=deg_f reload.latest=True ')
    datadir = os.path.join(testing_directory, 'DATA')
    subdirs = utils.get_subfiles(datadir, 'directory')
    np.random.seed(42)
    subdirs = np.random.choice(subdirs, size=100, replace=False)
    dir_string = ','.join([str(i) for i in subdirs])
    dir_string = '[' + dir_string + ']'
    string += f'inference.directory_list={dir_string} inference.overwrite=True '
    string = add_default_arguments(string, train=False)
    command = command_from_string(string)
    ret = subprocess.run(command)
    assert ret.returncode == 0
    # string += 'inference.directory_list=[]'

def test_sequence_train():
    string = (f'python -m deepethogram.sequence.train ')
    string = add_default_arguments(string)
    command = command_from_string(string)
    print(command)
    ret = subprocess.run(command)
    assert ret.returncode == 0
