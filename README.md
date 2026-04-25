# 🔐 Clipboard Data Leakage Prevention Tool

A concise quickstart and reference for the Clipboard DLP prototype. Full design notes and storage strategy are available in the `docs/` directory.

Badges: Python 3.10+ | Platform: Windows | Linux | Educational

---

**Quick Start (copy-paste)**

```bash
git clone https://github.com/Shr1H4x/clipboard-security-tool.git
cd clipboard-security-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

See `docs/INSTALLATION.md` for detailed platform notes and packaging instructions.

---

**Run the CLI demo**

```bash
python -m clipboard_dlp.cli info
python -m clipboard_dlp.cli analyze --text "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
```

If you installed the project with `pip install -e .`, use the `clipboard-dlp` entry:

```bash
clipboard-dlp analyze --text "sk-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
```

---

**Run tests**

```bash
pytest -q
```

---

**Where to look next**
- `docs/INSTALLATION.md` — full install & platform notes
- `docs/clipboard_dlp_storage_strategy.md` — storage strategy and privacy model
- `src/clipboard_dlp/analyzer.py` — pattern rules and entropy classifier
- `tests/test_analyzer.py` — example tests

---

This repository is a prototype: it provides a detection engine and CLI demo. The next development steps are `monitor.py` (real-time capture), GUI/tray components, and configuration. If you'd like, I can add a minimal GitHub Actions CI workflow to run tests on push.

