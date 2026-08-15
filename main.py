from pathlib import Path
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from workflow import run_workflow
from excel_writer import write_excel
from bridge_server import start_server, create_job, wait_for_result

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

        

        # ============================================================
        # YOUTUBE
        # ============================================================
        tk.Label(
            root,
            text="YouTube Research",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=12, pady=(4, 4))

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

        tk.Label(root, text="YouTube API Key:").pack(
            anchor="w", padx=12, pady=(6, 2)
        )

        self.youtube_api_key_entry = tk.Entry(root, show="*")
        self.youtube_api_key_entry.pack(fill="x", padx=12, pady=4)

        tk.Label(
            root,
            text="Danh sách link kênh YouTube (mỗi link 1 dòng):"
        ).pack(anchor="w", padx=12, pady=(6, 2))

        self.youtube_urls_text = tk.Text(root, height=4, wrap="word")
        self.youtube_urls_text.pack(fill="x", padx=12, pady=4)

        topn_frame = tk.Frame(root)
        topn_frame.pack(fill="x", padx=12, pady=4)

        tk.Label(
            topn_frame,
            text="Top N video xem nhiều nhất mỗi kênh:"
        ).pack(side="left")

        self.top_n_entry = tk.Entry(topn_frame, width=6)
        self.top_n_entry.insert(0, "10")
        self.top_n_entry.pack(side="left", padx=8)

        self.youtube_run_btn = tk.Button(
            root,
            text="▶ Phân tích kênh",
            command=self.start_youtube_analysis
        )
        self.youtube_run_btn.pack(anchor="w", padx=12, pady=6)

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

        tk.Label(root, text="Nhật ký YouTube:").pack(
            anchor="w", padx=12, pady=(4, 2)
        )

        self.youtube_log = tk.Text(root, height=5, bg="#f5f5f5")
        self.youtube_log.pack(fill="x", padx=12, pady=4)

        ttk.Separator(root, orient="horizontal").pack(
            fill="x", padx=12, pady=8
        )

        # ============================================================
        # OPENAI API
        # ============================================================
        tk.Label(
            root,
            text="OpenAI API",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 4))

        openai_frame = tk.Frame(root)
        openai_frame.pack(fill="x", padx=12, pady=4)

        tk.Label(openai_frame, text="API Key:").pack(side="left")

        self.openai_key_entry = tk.Entry(openai_frame, show="*")
        self.openai_key_entry.pack(side="left", fill="x", expand=True, padx=8)

        tk.Label(openai_frame, text="Model:").pack(side="left")

        self.model_var = tk.StringVar(value="gpt-5.6")
        self.model_box = ttk.Combobox(
            openai_frame,
            textvariable=self.model_var,
            width=24,
            values=(
                "gpt-5.6",
                "gpt-5.6-mini",
                "gpt-5.6-nano",
            ),
        )
        self.model_box.pack(side="left", padx=8)

        ttk.Separator(root, orient="horizontal").pack(
            fill="x", padx=12, pady=8
        )

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

        tk.Button(
            root,
            text="PROCESS_WITH_OPENAI_API",
            command=self.process
        ).pack(pady=6)

        tk.Button(
            root,
            text="PROCESS_WITH_CHATGPT_WEB",
            command=self.process_chatgpt_web
        ).pack(pady=6)

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
    # YOUTUBE BUTTONS
    # ============================================================

    def start_youtube_analysis(self):
        api_key = self.youtube_api_key_entry.get().strip()
        urls = [
            line.strip()
            for line in self.youtube_urls_text.get("1.0", "end").splitlines()
            if line.strip()
        ]

        try:
            top_n = int(self.top_n_entry.get().strip())
            if top_n <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Sai giá trị", "Top N phải là số nguyên > 0.")
            return

        if not api_key:
            messagebox.showerror("Thiếu API Key", "Vui lòng nhập YouTube API Key.")
            return

        if not urls:
            messagebox.showerror("Thiếu link", "Vui lòng nhập ít nhất một link kênh.")
            return

        self.youtube_run_btn.config(state="disabled", text="Đang xử lý...")
        self.youtube_log.delete("1.0", "end")

        try:
            all_rows = []
            for url in urls:
                try:
                    rows = process_channel(
                        url,
                        api_key,
                        top_n,
                        self.youtube_log_fn,
                    )
                    all_rows.extend(rows)
                except Exception as exc:
                    self.youtube_log_fn(f"❌ Lỗi với link {url}: {exc}")

            if not all_rows:
                messagebox.showwarning(
                    "Không có dữ liệu",
                    "Không lấy được video nào."
                )
                return

            import pandas as pd

            df = pd.DataFrame(all_rows).sort_values(
                "Lượt xem", ascending=False
            )

            if self.default_folder:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(
                    self.default_folder,
                    f"youtube_research_{timestamp}.xlsx"
                )
            else:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel file", "*.xlsx")],
                    initialfile="youtube_research_result.xlsx",
                    title="Lưu kết quả vào đâu?"
                )

            if not save_path:
                self.youtube_log_fn("Đã hủy lưu file.")
                return

            df.to_excel(save_path, index=False)
            self.youtube_log_fn(
                f"✅ Đã lưu {len(df)} video vào: {save_path}"
            )
            messagebox.showinfo(
                "Hoàn tất",
                f"Đã phân tích xong {len(df)} video!\nFile: {save_path}"
            )

        finally:
            self.youtube_run_btn.config(
                state="normal", text="▶ Phân tích kênh"
            )

    def start_transcript(self):
        raw = self.transcript_entry.get().strip()
        video_id = extract_video_id(raw)

        if not video_id:
            messagebox.showerror(
                "Link không hợp lệ",
                "Không nhận diện được video ID."
            )
            return

        folder = self.default_folder
        if not folder:
            folder = filedialog.askdirectory(
                title="Chọn thư mục để lưu transcript"
            )

        if not folder:
            return

        try:
            self.youtube_log_fn(f"→ Đang lấy transcript: {video_id}")
            text, lang = fetch_transcript_text(video_id)

            file_path = os.path.join(
                folder,
                f"transcript_{video_id}.txt"
            )

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)

            self.youtube_log_fn(
                f"✅ Đã lưu transcript ({lang}): {file_path}"
            )
            messagebox.showinfo(
                "Hoàn tất",
                f"Đã lưu transcript vào:\n{file_path}"
            )

        except (TranscriptsDisabled, NoTranscriptFound):
            messagebox.showwarning(
                "Không có transcript",
                "Video này không có phụ đề."
            )
        except VideoUnavailable:
            messagebox.showerror("Lỗi", "Video không khả dụng.")
        except Exception as exc:
            self.youtube_log_fn(f"❌ Lỗi transcript: {exc}")
            messagebox.showerror("Lỗi", str(exc))

    # ============================================================
    # AI WORKFLOW - GIỮ NGUYÊN LOGIC
    # ============================================================

    def choose_skill(self):
        path=filedialog.askopenfilename(title="Chọn Skill Markdown",filetypes=[("Markdown","*.md"),("Text","*.txt"),("All files","*.*")])
        if path:
            self.skill_path=path
            self.skill_path_label.config(text=path,fg="#000")

    def process_chatgpt_web(self):
        context = self.reference.get("1.0", "end").strip()
        topic = self.topic.get().strip()
        if not context or not topic:
            messagebox.showwarning( "Input",  "Cần nhập đoạn văn mẫu và chủ đề mới."  )
            return

        try:
            start_server()
            job_id = create_job(context=context,topic=topic)
            self.status.set(f"ChatGPT Web: waiting — {job_id}" )
            threading.Thread(target=self._wait_chatgpt_result,args=(job_id,),daemon=True).start()

        except Exception as exc:
            messagebox.showerror("ChatGPT Web",str(exc))


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

        except Exception as exc:
            self.status.set("Error")
            messagebox.showerror("Error", str(exc))

    def status_callback(self, text):
        self.status.set(text)
        self.root.update_idletasks()

    def export(self):
        if not self.data:
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

        write_excel(self.data, path)
        messagebox.showinfo("Export", f"Đã lưu: {path}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
