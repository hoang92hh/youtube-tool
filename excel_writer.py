from openpyxl import Workbook


def write_excel(data, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Scenes"

    ws.append(["stt", "nội dung gốc", "câu prompt", "thời gian"])

    for scene in data["scenes"]:
        ws.append([
            scene["stt"],
            scene["original_content"],
            scene["prompt"],
            scene["duration"],
        ])

    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 70
    ws.column_dimensions["C"].width = 90
    ws.column_dimensions["D"].width = 16

    wb.save(path)
