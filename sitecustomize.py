"""Compatibility shim for torchvision with the bundled Torch build."""

try:
    import torch

    _torchvision_library = torch.library.Library("torchvision", "DEF")
    _torchvision_library.define(
        "nms(Tensor dets, Tensor scores, float iou_threshold) -> Tensor"
    )
except Exception:
    pass
