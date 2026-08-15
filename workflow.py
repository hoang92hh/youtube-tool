import json

from openai_client import response_text
from skill_loader import load_skill_file, load_instruction


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "article": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "stt": {"type": "integer"},
                    "original_content": {"type": "string"},
                    "prompt": {"type": "string"},
                    "duration": {"type": "number"}
                },
                "required": ["stt", "original_content", "prompt", "duration"]
            }
        }
    },
    "required": ["article", "scenes"]
}


def run_workflow(reference, topic, status_callback=None):
    def status(text):
        if status_callback:
            status_callback(text)

    skill = load_skill_file()

    status("1/3 Analyzing reference...")
    analysis = response_text(
        instructions=skill + "\n\n" + load_instruction("analysis.md"),
        input_text=(
            "REFERENCE TEXT:\n\n"
            + reference
            + "\n\nAnalyze this reference and produce a concise style profile "
              "for the next writing stage."
        ),
    )

    status("2/3 Creating article...")
    article = response_text(
        instructions=skill + "\n\n" + load_instruction("create.md"),
        input_text=(
            "STYLE PROFILE:\n\n"
            + analysis
            + "\n\nNEW TOPIC:\n\n"
            + topic
            + "\n\nWrite the complete new article."
        ),
    )

    status("3/3 Creating scenes...")
    scene_instruction = load_instruction("scene.md")
    output_instruction = (
        skill
        + "\n\n"
        + scene_instruction
        + "\n\nReturn ONLY valid JSON matching this schema:\n"
        + json.dumps(SCHEMA, ensure_ascii=False)
    )

    result_text = response_text(
        instructions=output_instruction,
        input_text=(
            "ARTICLE:\n\n"
            + article
            + "\n\nDivide this article into scenes and return the final structured result."
        ),
    )

    try:
        data = json.loads(result_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "AI không trả về JSON hợp lệ. Raw output:\n" + result_text
        ) from exc

    validate_result(data)
    return data


def validate_result(data):
    if not isinstance(data, dict):
        raise ValueError("Output phải là object.")
    if not isinstance(data.get("article"), str) or not data["article"].strip():
        raise ValueError("Thiếu article.")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Thiếu scenes.")

    for index, scene in enumerate(scenes, start=1):
        if scene.get("stt") != index:
            raise ValueError(f"STT không liên tục tại scene {index}.")
        if not isinstance(scene.get("original_content"), str) or not scene["original_content"].strip():
            raise ValueError(f"Scene {index} thiếu original_content.")
        if not isinstance(scene.get("prompt"), str) or not scene["prompt"].strip():
            raise ValueError(f"Scene {index} thiếu prompt.")
        if not isinstance(scene.get("duration"), (int, float)) or scene["duration"] <= 0:
            raise ValueError(f"Scene {index} có duration không hợp lệ.")
