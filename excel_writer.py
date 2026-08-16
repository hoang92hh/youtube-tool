from openpyxl import Workbook


def write_excel(data, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Scenes"

    ws.append(["stt", "nội dung gốc", "câu prompt", "thời gian"])

    # NEW
    for scene in data["scenes"]:
        ws.append([
            scene["stt"],
            scene["noi_dung_goc"],
            scene["cau_prompt"],
            scene["thoi_gian_scene"],
        ])

    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 200
    ws.column_dimensions["C"].width = 300
    ws.column_dimensions["D"].width = 16

    wb.save(path)
