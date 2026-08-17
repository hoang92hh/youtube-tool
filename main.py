from pathlib import Path
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from workflow import run_workflow
from excel_writer import write_excel
from bridge_server import start_server, create_job, wait_for_result
import re

import threading

# YouTube logic is kept in youtube_gui.py.
# main.py only owns the UI and calls these methods.
from youtube_content import (
    process_channel,
    extract_video_id,
    fetch_transcript_text,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

BASE_DIR = Path(__file__).resolve().parent


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Reference Style Tool V1")
        self.root.geometry("1000x950")
        self.root.minsize(850, 750)

        self.data = None
        self.default_folder = None
        self.skill_path = None
        self.chatgpt_web_data = None

        folder_frame = tk.Frame(root)
        folder_frame.pack(fill="x", padx=12, pady=4)

        tk.Label(folder_frame, text="Thư mục lưu:").pack(side="left")

        self.default_folder_label = tk.Label(
            folder_frame,
            text="(chưa chọn — sẽ hỏi khi lưu)",
            fg="#888"
        )
        self.default_folder_label.pack(side="left", padx=8)
        tk.Button(
            folder_frame,
            text="📁 Chọn thư mục",
            command=self.choose_default_folder
        ).pack(side="right")

        # ============================================================
        # OPENAI API
        # ============================================================
        # tk.Label(
        #     root,
        #     text="OpenAI API",
        #     font=("Arial", 11, "bold")
        # ).pack(anchor="w", padx=12, pady=(12, 4))
        #
        # openai_frame = tk.Frame(root)
        # openai_frame.pack(fill="x", padx=12, pady=4)
        #
        # tk.Label(openai_frame, text="API Key:").pack(side="left")
        #
        # self.openai_key_entry = tk.Entry(openai_frame, show="*")
        # self.openai_key_entry.pack(side="left", fill="x", expand=True, padx=8)
        #
        # tk.Label(openai_frame, text="Model:").pack(side="left")
        #
        # self.model_var = tk.StringVar(value="gpt-5.6")
        # self.model_box = ttk.Combobox(
        #     openai_frame,
        #     textvariable=self.model_var,
        #     width=24,
        #     values=(
        #         "gpt-5.6",
        #         "gpt-5.6-mini",
        #         "gpt-5.6-nano",
        #     ),
        # )
        # self.model_box.pack(side="left", padx=8)
        #
        # ttk.Separator(root, orient="horizontal").pack(
        #     fill="x", padx=12, pady=8
        # )

        transcript_frame = tk.Frame(root)
        transcript_frame.pack(fill="x", padx=12, pady=6)

        tk.Label(transcript_frame, text="Video URL / ID:").pack(side="left")

        self.transcript_entry = tk.Entry(transcript_frame)
        self.transcript_entry.pack(side="left", fill="x", expand=True, padx=8)

        self.transcript_btn = tk.Button(
            transcript_frame,
            text="Lấy transcript",
            command=self.start_transcript
        )
        self.transcript_btn.pack(side="left")

        # ============================================================
        # AI INPUT
        # ============================================================
        tk.Label(
            root,
            text="ĐOẠN VĂN MẪU",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", padx=12, pady=(4, 4))

        self.reference = tk.Text(root, height=10, wrap="word")
        self.reference.pack(fill="both", expand=True, padx=12)

        tk.Label(
            root,
            text="CHỦ ĐỀ MỚI",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.topic = tk.Entry(root)
        self.topic.pack(fill="x", padx=12)

        self.status = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status).pack(
            anchor="w", padx=12, pady=8
        )

        # NEW
        buttons_frame = tk.Frame(root)
        buttons_frame.pack(pady=6)

        tk.Button(
            buttons_frame,
            text="PROCESS_WITH_OPENAI_API",
            command=self.process,
            state = "disabled"
        ).pack(side="left", padx=6)

        tk.Button(
            buttons_frame,
            text="CHECK_PROJECT",
            command=self.check_project
        ).pack(side="left", padx=6)

        self.chatgpt_web_btn = tk.Button(
            buttons_frame,
            text="PROCESS_WITH_CHATGPT_WEB",
            command=self.process_chatgpt_web
        )
        self.chatgpt_web_btn.pack(side="left", padx=6)

        tk.Label(
            root,
            text="ARTICLE",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.result = tk.Text(root, height=8, wrap="word")
        self.result.pack(fill="both", expand=True, padx=12)

        tk.Button(
            root,
            text="EXPORT EXCEL",
            command=self.export
        ).pack(pady=10)

    # ============================================================
    # COMMON UI
    # ============================================================

    def choose_default_folder(self):
        folder = filedialog.askdirectory(
            title="Chọn thư mục lưu kết quả mặc định"
        )
        if folder:
            self.default_folder = folder
            self.default_folder_label.config(text=folder, fg="#000")

    def youtube_log_fn(self, message):
        # process_channel() calls this while working.
        self.youtube_log.insert("end", message + "\n")
        self.youtube_log.see("end")
        self.root.update_idletasks()


    # ============================================================
    # AI WORKFLOW - GIỮ NGUYÊN LOGIC
    # ============================================================

    def choose_skill(self):
        path=filedialog.askopenfilename(title="Chọn Skill Markdown",filetypes=[("Markdown","*.md"),("Text","*.txt"),("All files","*.*")])
        if path:
            self.skill_path=path
            self.skill_path_label.config(text=path,fg="#000")

    STATE_LABELS = {
        "queued": "Đang chờ extension lấy job...",
        "assigned": "Extension đã nhận job...",
        "received": "Content script đã nhận job...",
        "attaching": "Đang đính kèm tệp vào ChatGPT...",
        "prompt_sent": "Đã gửi prompt, chờ ChatGPT xử lý...",
        "waiting_gpt": "Đang chờ ChatGPT trả lời...",
        "done": "Hoàn tất.",
        "error": "Lỗi.",
    }

    # NEW
    def check_project(self):
        try:
            start_server()
            create_job("CHECK_PROJECT", "PROJECT")
            print("Đang chạy function Check project")

        except Exception as exc:
            messagebox.showerror("Check Project", str(exc))

    def process_chatgpt_web(self):
        context = self.reference.get("1.0", "end").strip()
        topic = self.topic.get().strip()
        if not context or not topic:
            messagebox.showwarning("Input", "Cần nhập đoạn văn mẫu và chủ đề mới.")
            return

        try:
            start_server()
            job_id = create_job(context=context,topic=topic)
            self.status.set(f"ChatGPT Web: waiting — {job_id}" )
            threading.Thread(target=self._wait_chatgpt_result,args=(job_id,),daemon=True).start()
            print("Đang chạy function Process ChatGPT Web")

        except Exception as exc:
            messagebox.showerror("ChatGPT Web", str(exc))

    def _wait_chatgpt_result(self, job_id):
        try:
            output = wait_for_result(job_id, 600)
            if not output:
                raise TimeoutError("Không nhận được output.json từ extension.")

            import json
            import pandas as pd

            data = json.loads(output.read_text(encoding="utf-8"))
            scenes = data.get("scenes")
            if not isinstance(scenes, list):
                raise ValueError("JSON không có trường scenes hợp lệ.")

            required = ["stt", "noi_dung_goc", "cau_prompt", "thoi_gian_scene"]
            for i, scene in enumerate(scenes, 1):
                missing = [x for x in required if x not in scene]
                if missing:
                    raise ValueError(f"Scene {i} thiếu: {', '.join(missing)}")

            df = pd.DataFrame(scenes)
            self.chatgpt_web_data = df
            self.root.after(
                0,
                lambda: self._show_chatgpt_result(df, json.dumps(data, ensure_ascii=False, indent=2))
            )
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("ChatGPT Web", str(exc)))
            self.root.after(0, lambda: self.status.set("ChatGPT Web: Error"))


    def _show_chatgpt_result(self,df,csv_text):
        self.result.delete("1.0","end"); self.result.insert("1.0",csv_text)
        self.status.set(f"ChatGPT Web: Done — {len(df)} scenes")
        self._auto_export({"scenes": df.to_dict(orient="records")})

    def process(self):
        reference = self.reference.get("1.0", "end").strip()
        topic = self.topic.get().strip()
        api_key = self.openai_key_entry.get().strip()
        model = self.model_var.get().strip()

        if not api_key:
            messagebox.showwarning(
                "OpenAI API",
                "Vui lòng nhập OpenAI API Key."
            )
            return

        if not reference or not topic:
            messagebox.showwarning(
                "Input",
                "Cần nhập đoạn văn mẫu và chủ đề mới."
            )
            return

        # Replace .env for the current process only.
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_MODEL"] = model

        try:
            self.status.set("Processing...")
            self.root.update_idletasks()

            # NEW
            self.data = run_workflow(
                reference,
                topic,
                self.status_callback
            )

            self.result.delete("1.0", "end")
            self.result.insert("1.0", self.data["article"])
            self.status.set(
                f"Done - {len(self.data['scenes'])} scenes"
            )
            # self._auto_export(self.data)

        except Exception as exc:
            self.status.set("Error")
            messagebox.showerror("Error", str(exc))

    def status_callback(self, text):
        self.status.set(text)
        self.root.update_idletasks()

    # NEW
    def export(self):
        if self.data is not None:
            export_data = self.data
        elif self.chatgpt_web_data is not None:
            export_data = {"scenes": self.chatgpt_web_data.to_dict(orient="records")}
        else:
            messagebox.showwarning("Export", "Chưa có kết quả.")
            return

        if self.default_folder:
            path = str(
                Path(self.default_folder) / "reference_style_result.xlsx"
            )
        else:
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")]
            )

        if not path:
            return

        write_excel(export_data, path)
        messagebox.showinfo("Export", f"Đã lưu: {path}")

    # NEW
    def _auto_export(self, export_data):
        folder = self.default_folder or str(BASE_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{timestamp}.xlsx"
        path = str(Path(folder) / filename)

        try:
            write_excel(export_data, path)
            self.status.set(f"Đã tự động lưu: {path}")
        except Exception as exc:
            messagebox.showerror("Auto Export", str(exc))

    def start_transcript(self):
        raw = self.transcript_entry.get().strip()
        video_id = extract_video_id(raw)

        if not video_id:
            messagebox.showerror(
                "Link không hợp lệ",
                "Không nhận diện được video ID."
            )
            return


        try:
            text, lang = fetch_transcript_text(video_id)
            text = self.clean_transcript(text)
            self.reference.delete("1.0", tk.END)
            self.reference.insert("1.0", text)

            messagebox.showinfo( "Hoàn tất", f"Đã lưu transcript vào Đoạn Code Mẫu" )

        except (TranscriptsDisabled, NoTranscriptFound):
            messagebox.showwarning( "Không có transcript","Video này không có phụ đề.")
        except VideoUnavailable:
            messagebox.showerror("Lỗi", "Video không khả dụng.")
        except Exception as exc:
            messagebox.showerror("Lỗi", str(exc))

    @staticmethod
    def clean_transcript( text, max_chars=10000, max_paragraphs=8):
        # 1. Xóa timestamp [7s], [10s]...
        text = re.sub(r'\[\d+s\]\s*', '', text)

        # 2. Marker như [âm nhạc], [tiếng cười]...
        #    được coi là điểm ngắt đoạn
        text = re.sub(r'\[[^\]]*\]\s*', '\n\n', text)

        # 3. Chuẩn hóa từng đoạn
        raw_paragraphs = re.split(r'\n\s*\n', text)

        paragraphs = []

        for paragraph in raw_paragraphs:
            paragraph = re.sub(r'\s+', ' ', paragraph).strip()

            if paragraph:
                paragraphs.append(paragraph)

        # 4. Nếu tổng text <= 10.000 ký tự
        #    thì giữ toàn bộ các đoạn
        total_length = sum(len(p) for p in paragraphs)

        if total_length <= max_chars:
            selected = paragraphs

        else:
            # 5. Lấy các đoạn từ đầu.
            #    Nếu thêm đoạn tiếp theo vượt 10.000
            #    thì dừng luôn.
            selected = []
            current_length = 0

            for paragraph in paragraphs:
                paragraph_length = len(paragraph)

                # +2 cho "\n\n"
                separator_length = 2 if selected else 0

                if current_length + separator_length + paragraph_length > max_chars:
                    break

                selected.append(paragraph)
                current_length += separator_length + paragraph_length

        # 6. Nếu sau khi giới hạn 10.000 ký tự
        #    vẫn còn hơn 8 đoạn thì lấy tối đa 8 đoạn.
        if len(selected) > max_paragraphs:
            selected = selected[:max_paragraphs]

        # 7. Ghép lại thành các đoạn văn
        return '\n\n'.join(selected)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
