from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SKILL_DIR = BASE_DIR / "skill"


def load_skill_file():
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def load_instruction(name):
    return (SKILL_DIR / "instructions" / name).read_text(encoding="utf-8")
