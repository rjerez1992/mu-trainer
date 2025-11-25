# Mu Online Trainer

Automated game state monitoring and Discord notifications for Mu Online. Uses image recognition and OCR to track character level, zen amounts, and game status, with automated health checks and milestone notifications.

### Libraries & Responsibilities

- `interception-python` – hardware-grade input control
- `ctypes` Win32 – window management
- `mss` – fast screenshots
- `opencv-python` – image processing and template matching
- `pytesseract` – OCR for level/zen reading
- `playsound` – audio notifications

Core services handle specific tasks:
- Game state detection (ingame, dialog, inventory, character menu)
- OCR processing for level and zen amounts
- Discord webhook notifications for milestones and errors
- Automated monitoring loops with health checks

## Installation

### Prerequisites
- **Interception driver**: Install from [oblitum/Interception](https://github.com/oblitum/Interception) (Windows driver for hardware input)
- **Tesseract OCR**: Install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and ensure it's on PATH

### Setup
```bash
poetry install
```

## Usage

Run the trainer:
```bash
poetry run trainer
```

Test modes (run individually):
```bash
poetry run trainer --test-notification     # Test Discord notifications
poetry run trainer --test-get-level        # Test level OCR
poetry run trainer --test-zen             # Test zen OCR
poetry run trainer --test-dialog          # Test dialog detection
poetry run trainer --test-ingame          # Test ingame detection
poetry run trainer --test-inventory       # Test inventory detection
poetry run trainer --test-character       # Test character menu detection
poetry run trainer --test-image-find      # Test image matching
```

### Configuration
Edit constants in `trainer.py`:
- `DISCORD_WEBHOOK_URL` – Your Discord webhook URL
- `DISCORD_UID` – Your Discord user ID
- `CHARACTER_NAME` – Character name for notifications
- `FOCUS_WINDOW_SUBSTRING` – Window title substring to focus
- Region offsets and sizes for your client resolution

### Required Assets
- `sounds/start.mp3`, `sounds/reward.mp3` – Audio cues
- `image-find/needle.png` – Reward detection template
- `vision/` directory – Screenshots and needle images for game state detection
- `vision_run/` (auto-created) – Runtime debug outputs

