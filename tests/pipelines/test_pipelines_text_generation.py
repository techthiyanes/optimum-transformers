import unittest

from transformers import MODEL_FOR_CAUSAL_LM_MAPPING, TF_MODEL_FOR_CAUSAL_LM_MAPPING
from optimum_transformers import OptimumTextGenerationPipeline, pipeline
from transformers.testing_utils import is_pipeline_test, require_tf, require_torch

from .test_pipelines_common import ANY, PipelineTestCaseMeta


# @is_pipeline_test
class TextGenerationPipelineTests(unittest.TestCase, metaclass=PipelineTestCaseMeta):
    model_mapping = MODEL_FOR_CAUSAL_LM_MAPPING
    tf_model_mapping = TF_MODEL_FOR_CAUSAL_LM_MAPPING

    @require_torch
    def test_small_model_onnx(self):
        text_generator = pipeline(task="text-generation", model="sshleifer/tiny-gpt2", framework="pt")
        # Using `do_sample=False` to force deterministic output
        outputs = text_generator("This is a test", do_sample=False)
        self.assertEqual(
            outputs,
            [
                {
                    "generated_text": ANY(str)
                }
            ],
        )

        outputs = text_generator(["This is a test", "This is a second test"])
        self.assertEqual(
            outputs,
            [
                [
                    {
                        "generated_text": ANY(str)
                    }
                ],
                [
                    {
                        "generated_text": ANY(str)
                    }
                ],
            ],
        )

    @require_torch
    def test_small_model_onnx_quantized(self):
        text_generator = pipeline(task="text-generation", model="sshleifer/tiny-gpt2", framework="pt", optimize=True)
        # Using `do_sample=False` to force deterministic output
        outputs = text_generator("This is a test", do_sample=False)
        self.assertEqual(
            outputs,
            [
                {
                    "generated_text": ANY(str)
                }
            ],
        )

        outputs = text_generator(["This is a test", "This is a second test"])
        self.assertEqual(
            outputs,
            [
                [
                    {
                        "generated_text": ANY(str)
                    }
                ],
                [
                    {
                        "generated_text": ANY(str)
                    }
                ],
            ],
        )

    def get_test_pipeline(self, model, tokenizer, feature_extractor):
        text_generator = OptimumTextGenerationPipeline(model=model, tokenizer=tokenizer)
        return text_generator, ["This is a test", "Another test"]

    def run_pipeline_test(self, text_generator, _):
        model = text_generator.model
        tokenizer = text_generator.tokenizer

        outputs = text_generator("This is a test")
        self.assertEqual(outputs, [{"generated_text": ANY(str)}])
        self.assertTrue(outputs[0]["generated_text"].startswith("This is a test"))

        outputs = text_generator("This is a test", return_full_text=False)
        self.assertEqual(outputs, [{"generated_text": ANY(str)}])
        self.assertNotIn("This is a test", outputs[0]["generated_text"])

        text_generator = pipeline(task="text-generation", model=model, tokenizer=tokenizer, return_full_text=False)
        outputs = text_generator("This is a test")
        self.assertEqual(outputs, [{"generated_text": ANY(str)}])
        self.assertNotIn("This is a test", outputs[0]["generated_text"])

        outputs = text_generator("This is a test", return_full_text=True)
        self.assertEqual(outputs, [{"generated_text": ANY(str)}])
        self.assertTrue(outputs[0]["generated_text"].startswith("This is a test"))

        outputs = text_generator(["This is great !", "Something else"], num_return_sequences=2, do_sample=True)
        self.assertEqual(
            outputs,
            [
                [{"generated_text": ANY(str)}, {"generated_text": ANY(str)}],
                [{"generated_text": ANY(str)}, {"generated_text": ANY(str)}],
            ],
        )

        if text_generator.tokenizer.pad_token is not None:
            outputs = text_generator(
                ["This is great !", "Something else"], num_return_sequences=2, batch_size=2, do_sample=True
            )
            self.assertEqual(
                outputs,
                [
                    [{"generated_text": ANY(str)}, {"generated_text": ANY(str)}],
                    [{"generated_text": ANY(str)}, {"generated_text": ANY(str)}],
                ],
            )

        # Empty prompt is slighly special
        # it requires BOS token to exist.
        # Special case for Pegasus which will always append EOS so will
        # work even without BOS.
        if text_generator.tokenizer.bos_token_id is not None or "Pegasus" in tokenizer.__class__.__name__:
            outputs = text_generator("")
            self.assertEqual(outputs, [{"generated_text": ANY(str)}])
        else:
            with self.assertRaises((ValueError, AssertionError)):
                outputs = text_generator("")

        if text_generator.framework == "tf":
            # TF generation does not support max_new_tokens, and it's impossible
            # to control long generation with only max_length without
            # fancy calculation, dismissing tests for now.
            return
        # We don't care about infinite range models.
        # They already work.
        # Skip this test for XGLM, since it uses sinusoidal positional embeddings which are resized on-the-fly.
        if tokenizer.model_max_length < 10000 and "XGLM" not in tokenizer.__class__.__name__:
            # Handling of large generations
            with self.assertRaises((RuntimeError, IndexError, ValueError, AssertionError)):
                text_generator("This is a test" * 500, max_new_tokens=20)

            outputs = text_generator("This is a test" * 500, handle_long_generation="hole", max_new_tokens=20)
            # Hole strategy cannot work
            with self.assertRaises(ValueError):
                text_generator(
                    "This is a test" * 500,
                    handle_long_generation="hole",
                    max_new_tokens=tokenizer.model_max_length + 10,
                )
