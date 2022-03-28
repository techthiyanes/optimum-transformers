from transformers.modeling_outputs import SequenceClassifierOutput
from .base import _forward_onnx, _warmup_onnx_graph
from transformers import TextClassificationPipeline
import torch


class OptimumTextClassificationPipeline(TextClassificationPipeline):
    def __init__(self, *args, onnx_model, example, **kwargs):
        super().__init__(*args, **kwargs)
        self.onnx_model = onnx_model
        self.example = example
        _warmup_onnx_graph(self)

    def _forward(self, model_inputs):
        return SequenceClassifierOutput(logits=torch.tensor(_forward_onnx(self.onnx_model, model_inputs)[0]))
