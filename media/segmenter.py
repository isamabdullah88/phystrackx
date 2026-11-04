"""
segmenter.py

Segment Anything (ViT-B, Meta AI) for finding objects in a frame from a few clicks or a box. The
image is encoded once; each prompt after that only runs the small decoder, so new clicks are fast.

Torch is used for the model only. Arrays cross into torch as Python lists: the installed torch
build is linked against NumPy 1.x, so its NumPy bridge is unavailable beside the pinned NumPy 2
(torch.from_numpy and tensor.numpy() fail). The list conversions are slower, but are only paid
per frame and per prompt.

Author: Isam Balghari
"""

import numpy as np

SAM_SIZE = 1024  # The model's input side length
SAM_CHECKPOINT = "models/sam_vit_b_01ec64.pth"

_model_cache: dict = {}


def _import_torch():
    """Imports torch without its NumPy-1.x warning: torch prints a long traceback-like message on
    import beside NumPy 2. Its NumPy bridge is not used here (see the module notes), so the
    message is noise that reads like a crash; it is logged as one line instead."""
    import contextlib
    import io
    import logging
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        import torch
    if "NumPy" in captured.getvalue():
        logging.getLogger(__name__).info("torch is built for NumPy 1.x; its NumPy bridge is not used")
    return torch


_default = None


def default_segmenter():
    """The shared Segment Anything model (loaded once, a few seconds), or None when the model file
    is not installed or cannot be loaded. Safe on a worker thread: no Tk."""
    global _default
    if _default is None:
        import logging
        import os
        from core import abspath
        path = abspath(SAM_CHECKPOINT)
        if not os.path.isfile(path):
            return None
        try:
            _default = SamSegmenter(path)
        except Exception:
            logging.getLogger(__name__).exception("Segment Anything could not be loaded")
            return None
    return _default


class SamSegmenter:
    """Object masks from point and box prompts, on one frame at a time."""

    def __init__(self, checkpoint: str) -> None:
        torch = _import_torch()
        from segment_anything import sam_model_registry

        self.torch = torch
        key = checkpoint
        if key not in _model_cache:
            model = sam_model_registry["vit_b"](checkpoint=checkpoint)
            model.eval()
            _model_cache[key] = model
        self.sam = _model_cache[key]
        self._embedding = None
        self._scale = 1.0
        self._size = (0, 0)  # The frame's (height, width)

    # ---------------------------------------------------------------------------------------------
    def _tensor(self, values):
        return self.torch.tensor(np.asarray(values, dtype=np.float32).tolist())

    def set_image(self, rgb: np.ndarray) -> None:
        """Encodes an RGB frame (uint8, H x W x 3). Call again when the frame changes."""
        import cv2

        h, w = rgb.shape[:2]
        self._size = (h, w)
        self._scale = SAM_SIZE / max(h, w)
        new_h, new_w = int(round(h * self._scale)), int(round(w * self._scale))
        resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        padded = np.zeros((SAM_SIZE, SAM_SIZE, 3), np.float32)
        padded[:new_h, :new_w] = resized

        mean = np.array(self.sam.pixel_mean.reshape(-1).tolist(), np.float32)
        std = np.array(self.sam.pixel_std.reshape(-1).tolist(), np.float32)
        normalised = (padded - mean) / std
        x = self._tensor(normalised).permute(2, 0, 1).unsqueeze(0)  # 1 x 3 x 1024 x 1024
        with self.torch.no_grad():
            self._embedding = self.sam.image_encoder(x)

    def predict(self, points=None, labels=None, box=None):
        """
        Object mask from prompts, in the frame's pixels.

        Args:
            points: (N, 2) clicks as (x, y) in frame pixels.
            labels: (N,) 1 for "this is the object", 0 for "this is not".
            box: (x0, y0, x1, y1) in frame pixels, or None.

        Returns:
            (mask, score): a boolean (H, W) array and the model's confidence in it (0-1).
        """
        if self._embedding is None:
            raise RuntimeError("Call set_image() before predict().")
        torch = self.torch

        coords = None
        point_labels = None
        if points is not None and len(points):
            coords = self._tensor(np.asarray(points, np.float32) * self._scale).unsqueeze(0)
            point_labels = torch.tensor(np.asarray(labels, np.float32).tolist()).unsqueeze(0)
        boxes = None
        if box is not None:
            boxes = self._tensor(np.asarray(box, np.float32).reshape(1, 4) * self._scale)

        with torch.no_grad():
            sparse, dense = self.sam.prompt_encoder(
                points=(coords, point_labels) if coords is not None else None,
                boxes=boxes, masks=None)
            low_res, iou = self.sam.mask_decoder(
                image_embeddings=self._embedding,
                image_pe=self.sam.prompt_encoder.get_dense_pe(),
                sparse_prompt_embeddings=sparse,
                dense_prompt_embeddings=dense,
                multimask_output=True)
            h, w = self._size
            new_h, new_w = int(round(h * self._scale)), int(round(w * self._scale))
            masks = self.sam.postprocess_masks(low_res, input_size=(new_h, new_w),
                                               original_size=(h, w))

        best = int(torch.argmax(iou[0]).item())
        mask = np.array(masks[0, best].tolist()) > 0.0
        return mask, float(iou[0, best].item())
