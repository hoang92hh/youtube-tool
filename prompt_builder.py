import json
from pathlib import Path

def build_get_dna_prompt(context):
    return f"Sử dụng `01_analyze_author_style.md` để phân tích văn bản mẫu dưới đây và tạo AUTHOR STYLE DNA.\n\nVĂN BẢN MẪU:\n\n{context}"

def build_research_write_prompt(dna_file, topic):
    data = json.loads(Path(dna_file).read_text(encoding="utf-8"))
    dna = data["style_dna"]
    return f"Sử dụng `02_research_and_write_author_style.md`.\n\nAUTHOR STYLE DNA:\n{dna}\n\nCHỦ ĐỀ:\n{topic}\n\nHãy thực hiện workflow theo đúng quy định của skill."