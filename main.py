from pathlib import Path
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

# from workflow import run_workflow
from excel_writer import write_excel
from bridge_server import start_server, create_job, wait_for_result
from  prompt_builder import build_get_dna_prompt, build_research_write_prompt
import re

import threading

# YouTube logic is kept in youtube_gui.py.
# main.py only owns the UI and calls these methods.
from youtube_content import (
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

        self.default_folder = None
        self.skill_path = None
        self.chatgpt_web_data = None

        self.author_dir = Path(__file__).resolve().parent / "author"
        self.author_dir.mkdir(parents=True, exist_ok=True)
        self.author_files = {}

        # ============================================================
        # FOLDER
        # ============================================================

        folder_frame = tk.Frame(root)
        folder_frame.pack(fill="x", padx=12, pady=4)

        tk.Label(
            folder_frame,
            text="Thư mục lưu:"
        ).pack(side="left")

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
        ).pack(side="right", padx=4)

        tk.Button(
            folder_frame,
            text="CHECK_PROJECT",
            command=self.check_project
        ).pack(side="right", padx=4)

        # ============================================================
        # TRANSCRIPT
        # ============================================================

        transcript_frame = tk.Frame(root)
        transcript_frame.pack(
            fill="x",
            padx=12,
            pady=6
        )

        tk.Label(
            transcript_frame,
            text="Video URL / ID:"
        ).pack(side="left")

        self.transcript_entry = tk.Entry(
            transcript_frame
        )
        self.transcript_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=8
        )

        self.transcript_btn = tk.Button(
            transcript_frame,
            text="Lấy transcript",
            command=self.start_transcript
        )
        self.transcript_btn.pack(side="left")

        # ============================================================
        # ĐOẠN VĂN MẪU
        # ============================================================

        reference_section = tk.Frame(root)
        reference_section.pack(fill="x", padx=12, pady=(4, 4))

        reference_header = tk.Frame(reference_section)
        reference_header.pack(fill="x")

        self.reference_visible = True

        self.reference_toggle_btn = tk.Button(
            reference_header,
            text="▲",
            width=3,
            command=self.toggle_reference
        )
        self.reference_toggle_btn.pack(side="left")

        tk.Label(
            reference_header,
            text="ĐOẠN VĂN MẪU",
            font=("Arial", 10, "bold")
        ).pack(side="left")

        self.get_adn_btn = tk.Button(
            reference_header,
            text="GET_ADN",
            command=self.get_DNA
        )
        self.get_adn_btn.pack(side="right")

        self.reference = tk.Text(
            reference_section,
            height=10,
            wrap="word"
        )
        self.reference.pack(fill="x")


        author_frame = tk.Frame(root)
        author_frame.pack(fill="x", padx=12, pady=(4, 4))
        tk.Label(author_frame, text="DNA TÁC GIẢ:").pack(side="left")

        self.author_combo = ttk.Combobox(author_frame, state="readonly")
        self.author_combo.pack(side="left", fill="x", expand=True, padx=8)
        self.author_combo.bind("<<ComboboxSelected>>", self.on_author_selected)
        self.load_authors()


        # ============================================================
        # CHỦ ĐỀ MỚI
        # ============================================================

        topic_frame = tk.Frame(root)
        topic_frame.pack(
            fill="x",
            padx=12,
            pady=(8, 4)
        )

        tk.Label(
            topic_frame,
            text="CHỦ ĐỀ MỚI",
            font=("Arial", 10, "bold")
        ).pack(side="left")

        self.chatgpt_web_btn = tk.Button(
            topic_frame,
            text="PROCESS_WITH_CHATGPT_WEB",
            command=self.process_chatgpt_web
        )
        self.chatgpt_web_btn.pack(
            side="right"
        )

        self.topic = tk.Entry(root)
        self.topic.pack(
            fill="x",
            padx=12
        )


        # ============================================================
        # ARTICLE
        # ============================================================

        article_section = tk.Frame(root)
        article_section.pack(fill="x", padx=12, pady=(8, 4))

        article_header = tk.Frame(article_section)
        article_header.pack(fill="x")

        self.article_visible = True

        self.article_toggle_btn = tk.Button(
            article_header,
            text="▲",
            width=3,
            command=self.toggle_article
        )
        self.article_toggle_btn.pack(side="left")

        tk.Label(
            article_header,
            text="ARTICLE",
            font=("Arial", 10, "bold")
        ).pack(side="left")

        tk.Button(
            article_header,
            text="EXPORT EXCEL",
            command=self.export
        ).pack(side="right")

        self.result = tk.Text(
            article_section,
            height=10,
            wrap="word"
        )
        self.result.pack(fill="both", expand=True)


        # ============================================================
        # STATUS
        # ============================================================

        self.status = tk.StringVar(
            value="Ready"
        )

        tk.Label(
            root,
            textvariable=self.status
        ).pack(
            anchor="w",
            padx=12,
            pady=8
        )

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


    # NEW
    def check_project(self):
        try:
            start_server()
            job_id = create_job("PROJECT",  "CHECK_PROJECT")
            self.status.set("Check Project: đang kiểm tra...")
            threading.Thread(
                target=self._wait_check_project_result,
                args=(job_id,),
                daemon=True
            ).start()
        except Exception as exc:
            messagebox.showerror("Check Project", str(exc))

    def _wait_check_project_result(self, job_id):
        try:
            output = wait_for_result(job_id, 600)
            if not output:
                raise TimeoutError("Check Project Fail")

            import json
            data = json.loads(output.read_text(encoding="utf-8"))
            message = data.get("message")

            if not message:
                raise ValueError("CHECK_PROJECT không có message.")

            self.root.after(0, lambda: self.status.set(f"CHECK_PROJECT: Done — {message}"))
            self.root.after(0,lambda: messagebox.showinfo("CHECK_PROJECT", message))

        except Exception as exc:
            self.root.after(0,  lambda: messagebox.showerror("Check Project",str(exc)))


    def get_DNA(self):
        context = self.reference.get("1.0", "end").strip()
        if not context:
            messagebox.showwarning("Input", "Cần nhập đoạn văn mẫu.")
            return
        try:
            start_server()
            context = build_get_dna_prompt(context)
            job_id = create_job(context= context,topic= "GET_DNA")
            self.status.set(f"get_DNA: waiting — {job_id}")
            threading.Thread(target=self._wait_get_DNA_result,args=(job_id,),daemon=True).start()
            print("Đang chạy function get_DNA")

        except Exception as exc:
            messagebox.showerror("getDNA", str(exc))

    def _wait_get_DNA_result(self, job_id):
        try:
            output = wait_for_result(job_id, 600)
            if not output:
                raise TimeoutError("Không nhận được output.json DNA từ extension.")

            data = json.loads(output.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Output GET_DNA không phải JSON object.")

            author_name = str(data.get("author_name", "")).strip()
            dna = data.get("style_dna")

            if not author_name:
                raise ValueError("JSON không có trường 'author_name'.")
            if not dna:
                raise ValueError("JSON không có trường 'style_dna'.")

            md_file = self.author_dir / f"{author_name}.md"
            md_file.write_text(str(dna), encoding="utf-8")

            self.author_files[author_name] = md_file
            self.author_dna = str(dna)

            self.root.after(0, lambda: self._refresh_author_combo(author_name))
            self.root.after(0, lambda: self.status.set(f"get_DNA: Done — {author_name}"))
            self.root.after(0, lambda: messagebox.showinfo("get_DNA", f"DNA đã được lấy: {author_name}"))
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("getDNA", str(exc)))
            self.root.after(0, lambda: self.status.set("getDNA: Error"))


    def process_chatgpt_web(self):
        topic = self.topic.get().strip()
        author_name = self.author_combo.get().strip()
        if not topic:
            messagebox.showwarning("Input", "Cần nhập chủ đề mới.")
            return
        if not author_name:
            messagebox.showwarning("Input", "Cần chọn DNA tác giả.")
            return
        try:
            md_file = self.author_files.get(author_name)
            if not md_file or not md_file.exists():
                raise FileNotFoundError(f"Không tìm thấy file DNA: {author_name}.md")
            dna = md_file.read_text(encoding="utf-8")
            start_server()
            content = build_research_write_prompt(dna, topic)
            job_id = create_job(context=content, topic="PROCESS_CHATGPT_WEB")
            self.status.set(f"ChatGPT Web: waiting — {job_id}")
            threading.Thread(target=self._wait_chatgpt_result, args=(job_id,), daemon=True).start()
            print("Đang chạy function Process ChatGPT Web")
        except Exception as exc:
            messagebox.showerror("ChatGPT Web", str(exc))

    def _wait_chatgpt_result(self, job_id):
        try:
            output = wait_for_result(job_id, 600)
            if not output:
                raise TimeoutError("Không nhận được New Content từ extension.")

            content = json.loads(output.read_text(encoding="utf-8"))
            if not isinstance(content, str):
                raise ValueError("Output ChatGPT không phải text.")

            self._auto_export_txt(content)
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("ChatGPT Web", str(exc)))
            self.root.after(0, lambda: self.status.set("ChatGPT Web: Error"))


    def _show_chatgpt_result(self,df,csv_text):
        self.result.delete("1.0","end"); self.result.insert("1.0",csv_text)
        self.status.set(f"ChatGPT Web: Done — {len(df)} scenes")
        self._auto_export({"scenes": df.to_dict(orient="records")})

    def status_callback(self, text):
        self.status.set(text)
        self.root.update_idletasks()

    # NEW
    def export(self):
        if self.chatgpt_web_data is not None:
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


    # NEW
    def _auto_export_txt(self, export_data):
        folder = self.default_folder or str(BASE_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{timestamp}.md"
        path = str(Path(folder) / filename)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(export_data))
            self.status.set(f"Đã tự động lưu: {path}")
            self.root.after(0, lambda: messagebox.showinfo("Auto Export", f"Đã tự động lưu: {path}"))
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

            self.reference.delete("1.0", tk.END)
            self.reference.insert("1.0", text)
            messagebox.showinfo( "Hoàn tất", f"Đã lưu transcript vào Đoạn Code Mẫu" )

        except (TranscriptsDisabled, NoTranscriptFound):
            messagebox.showwarning( "Không có transcript","Video này không có phụ đề.")
        except VideoUnavailable:
            messagebox.showerror("Lỗi", "Video không khả dụng.")
        except Exception as exc:
            messagebox.showerror("Lỗi", str(exc))

    def toggle_reference(self):
        if self.reference_visible:
            self.reference.pack_forget()
            self.reference_toggle_btn.config(text="▼")
            self.reference_visible = False
        else:
            self.reference.pack(fill="x")
            self.reference_toggle_btn.config(text="▲")
            self.reference_visible = True

    def toggle_article(self):
        if self.article_visible:
            self.result.pack_forget()
            self.article_toggle_btn.config(text="▼")
            self.article_visible = False
        else:
            self.result.pack(fill="x")
            self.article_toggle_btn.config(text="▲")
            self.article_visible = True

    def load_authors(self):
        self.author_files.clear()
        authors = []

        for path in sorted(self.author_dir.glob("*.md")):
            author_name = path.stem.strip()
            if author_name:
                authors.append(author_name)
                self.author_files[author_name] = path

        self.author_combo["values"] = authors
        if authors:
            self.author_combo.current(0)
            self.on_author_selected()

    def on_author_selected(self, event=None):
        author_name = self.author_combo.get()
        path = self.author_files.get(author_name)
        if not path:
            return

        try:
            self.author_dna = path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            messagebox.showerror("DNA tác giả", str(exc))

    def _refresh_author_combo(self, author_name):
        authors = sorted(self.author_files.keys())
        self.author_combo["values"] = authors
        self.author_combo.set(author_name)



if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
