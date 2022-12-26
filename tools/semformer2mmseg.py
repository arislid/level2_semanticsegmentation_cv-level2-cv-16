import argparse
import os.path as osp
from collections import OrderedDict

import mmcv
import torch
from mmcv.runner import CheckpointLoader


def convert_senformer(ckpt):
    new_state_dict = {}
    new_ckpt = OrderedDict()

    for k, v in ckpt.items():
        # print('k:', k)
        if 'DeFormerV1Branch' in k:
            k = k.replace('DeFormerV1Branch', 'TransformerLearner')
        if 'scale_heads' in k:
            k = k.replace('scale_heads', 'learners')
        if 'norm_queriesPost' in k:
            k = k.replace('norm_queriesPost', 'norm_embs')
        if 'norm_queriesPre' in k:
            pass
        else:
            new_ckpt[k] = v

    for k, v in new_ckpt.items():
        if k.startswith('neck'):
            print('new_k:', k)
    # return new_state_dict
    return new_ckpt


def convert_swin(ckpt):
    new_ckpt = OrderedDict()

    def correct_unfold_reduction_order(x):
        out_channel, in_channel = x.shape
        x = x.reshape(out_channel, 4, in_channel // 4)
        x = x[:, [0, 2, 1, 3], :].transpose(1,
                                            2).reshape(out_channel, in_channel)
        return x

    def correct_unfold_norm_order(x):
        in_channel = x.shape[0]
        x = x.reshape(4, in_channel // 4)
        x = x[[0, 2, 1, 3], :].transpose(0, 1).reshape(in_channel)
        return x

    for k, v in ckpt.items():
        if k.startswith('head'):
            continue
        elif k.startswith('neck'):
            print('k:', k)
            new_v = v
            if 'attn.' in k:
                new_k = k.replace('attn.', 'attn.w_msa.')
            elif 'mlp.' in k:
                if 'mlp.fc1.' in k:
                    new_k = k.replace('mlp.fc1.', 'ffn.layers.0.0.')
                elif 'mlp.fc2.' in k:
                    new_k = k.replace('mlp.fc2.', 'ffn.layers.1.')
                else:
                    new_k = k.replace('mlp.', 'ffn.')
            elif 'downsample' in k:
                new_k = k
                if 'reduction.' in k:
                    new_v = correct_unfold_reduction_order(v)
                elif 'norm.' in k:
                    new_v = correct_unfold_norm_order(v)
            else:
                new_k = k
            # new_k = new_k.replace('layers', 'stages', 1)

        elif k.startswith('backbone.layers'):
            new_v = v
            if 'attn.' in k:
                new_k = k.replace('attn.', 'attn.w_msa.')
            elif 'mlp.' in k:
                if 'mlp.fc1.' in k:
                    new_k = k.replace('mlp.fc1.', 'ffn.layers.0.0.')
                elif 'mlp.fc2.' in k:
                    new_k = k.replace('mlp.fc2.', 'ffn.layers.1.')
                else:
                    new_k = k.replace('mlp.', 'ffn.')
            elif 'downsample' in k:
                new_k = k
                if 'reduction.' in k:
                    new_v = correct_unfold_reduction_order(v)
                elif 'norm.' in k:
                    new_v = correct_unfold_norm_order(v)
            else:
                new_k = k
            new_k = new_k.replace('layers', 'stages', 1)
        elif k.startswith('backbone.patch_embed'):
            new_v = v
            if 'proj' in k:
                new_k = k.replace('proj', 'projection')
            else:
                new_k = k
        else:
            new_v = v
            new_k = k

        new_ckpt[new_k] = new_v

    return new_ckpt

def main():
    parser = argparse.ArgumentParser(
        description='Convert keys in official pretrained segformer to '
                    'MMSegmentation style.')
    parser.add_argument('--src', default='../mmsegmentation/pretrained_models/senformer_r101_512x512_coco.pth' ,help='src model path or url')
    # The dst path must be a full path of the new checkpoint.
    parser.add_argument('--dst', default='mmseg_senformer_r101_512x512_coco.pth', help='save path')
    args = parser.parse_args()

    checkpoint = CheckpointLoader.load_checkpoint(args.src, map_location='cpu')
    if 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    elif 'model' in checkpoint:
        state_dict = checkpoint['model']
    else:
        state_dict = checkpoint
    weight = convert_swin(state_dict)
    weight = convert_senformer(weight)
    mmcv.mkdir_or_exist(osp.dirname(args.dst))
    torch.save(weight, args.dst)


if __name__ == '__main__':
    main()