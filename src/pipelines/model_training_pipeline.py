from kfp import dsl

from src.constants import PIPELINE_NAME
from src.pipeline_components.data_transformation_component import data_transformation_component
from src.pipeline_components.evaluation_component import evaluation_component
from src.pipeline_components.fine_tuning_component import fine_tuning_component
from src.pipeline_components.inference_component import inference_component


def use_gpu(task: dsl.PipelineTask) -> dsl.PipelineTask:
    """One NVIDIA T4 + enough CPU/RAM for Phi-3-mini (course settings)."""
    return (
        task.set_accelerator_type("NVIDIA_TESLA_T4")
        .set_accelerator_limit(1)
        .set_cpu_limit("16")
        .set_memory_limit("50G")
    )


@dsl.pipeline(
    name=PIPELINE_NAME,
    description="ParcelCheck: format the refund claims, fine-tune Phi-3 with LoRA, decide on the test claims, score the decisions.",
)
def model_training_pipeline(
    raw_data_path: str,
    test_size: float = 0.15,
    seed: int = 42,
    num_train_epochs: int = 2,
    learning_rate: float = 2e-4,
    max_test_samples: int = 0,
) -> None:
    data_task = data_transformation_component(
        raw_data_path=raw_data_path,
        test_size=test_size,
        seed=seed,
    ).set_display_name("Data transformation")

    fine_tuning_task = fine_tuning_component(
        train_dataset=data_task.outputs["train_dataset_path"],
        num_train_epochs=num_train_epochs,
        learning_rate=learning_rate,
        seed=seed,
    ).set_display_name("Fine-tuning (LoRA)")
    use_gpu(fine_tuning_task)

    inference_task = inference_component(
        model=fine_tuning_task.outputs["model"],
        test_dataset=data_task.outputs["test_dataset_path"],
        max_samples=max_test_samples,
    ).set_display_name("Inference on held-out claims")
    use_gpu(inference_task)

    evaluation_component(
        predictions=inference_task.outputs["predictions"],
    ).set_display_name("Evaluation (decision + money)")
