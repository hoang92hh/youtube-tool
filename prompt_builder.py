import json
import sys
from pathlib import Path

BASE_DIR_PROMPT = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def build_get_dna_prompt(context):
    default_prompt = "Sử dụng `01_analyze_author_style.md` để phân tích văn bản mẫu dưới đây và tạo AUTHOR STYLE DNA.\n\nVĂN BẢN MẪU:\n\n{0}"
    prompt_file = BASE_DIR_PROMPT / "prompts" / "prompt_get_DNA.txt"

    if not prompt_file.is_file():
        return default_prompt.replace("{0}", context)

    template = prompt_file.read_text(encoding="utf-8").strip()

    if not template:
        return default_prompt.replace("{0}", context)

    if "{0}" not in template or "AUTHOR STYLE DNA" not in template:
        return "FILE_ERROR"

    return template.replace("{0}", context)


def build_research_write_prompt(dna, topic):
    default_prompt = "Sử dụng `02_research_and_write_author_style.md` trong project.\n\nTôi có các thông tin đầu vào quan trọng sau :\n{0}\n\nCHỦ ĐỀ:\n{1}\n\nHãy thực hiện workflow theo đúng quy định của skill 02_research_and_write_author_style.md "
    prompt_file = BASE_DIR_PROMPT / "prompts" / "prompt_get_new_content.txt"

    if not prompt_file.is_file():
        return default_prompt.replace("{0}", dna).replace("{1}", topic)

    template = prompt_file.read_text(encoding="utf-8").strip()

    if not template:
        return default_prompt.replace("{0}", dna).replace("{1}", topic)

    if "{0}" not in template or "{1}" not in template:
        return "FILE_ERROR"

    return template.replace("{0}", dna).replace("{1}", topic)