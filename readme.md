# PhysTrackX

Measure motion in a video: track a ball, plot it, and fit the physics.

## Quick start

### 1. Install

**Windows**
1. Download the code: on https://github.com/xoth42/phystrackx click **Code > Download ZIP**, and unzip it
   (or `git clone https://github.com/xoth42/phystrackx`).
2. Open the folder and double-click **`install.bat`**. It installs everything it needs (uv, Python and the
   libraries) and takes a few minutes the first time.
3. When it says **Done**, start PhysTrackX from the **desktop icon** or the **Start menu**.

   (Alternative: [PhysTrackX-Setup.exe](https://github.com/xoth42/phystrackx/releases/latest/download/PhysTrackX-Setup.exe),
   a normal installer. If Windows says "Windows protected your PC", choose More info, then Run anyway.)

**macOS**
1. Download or clone the code as above.
2. In Terminal, in that folder: `sh install.sh`
3. Open **PhysTrackX** from Applications (or run `phystrackx` in a terminal).

**Linux**
1. Download or clone the code as above.
2. In a terminal, in that folder: `sh install.sh`
3. Run `phystrackx`.

### 2. Measure a video

1. **Open Video…** and pick your video (or **Open Project…** for a saved .phystrack).
2. **Trim** to the part you want (from just before the motion starts).
3. **Place Ruler** (or **Auto Ruler**): put it along something of known length, type the length, **Apply Ruler**.
4. **Place Axis** (or **Auto Axis**): put the origin where you measure from (e.g. the bottom of the tube).
5. **Mark Circle** (for a ball) or **Mark Rectangle**: draw it around the object.
6. **Track.** Check the path; fix a frame by dragging the box, then Track again.
7. **Plots:** choose what to plot (e.g. r against t) and a fit model; the fit gives the period.
8. **Save Project** (.phystrack), and **Export Data (CSV)…** for the numbers.

### 3. Update or uninstall

- Update: download the code again (or `git pull`) and rerun `install.bat` / `install.sh`.
- Uninstall: run `uninstall.bat` (Windows) or `sh uninstall.sh` (macOS/Linux). Your videos and projects are kept.

More detail on the app: [qt/README.md](qt/README.md).

---

# Old README (TODO: clean up)

Below is the original README, from the older Tk app. Parts of it are out of date.

## PhysTrackX (original)

## 🎓 Purpose

PhysTrackX is developed to assist students in understanding physics concepts through visualization and data analysis. It encourages curiosity, supports hands-on learning, and bridges theoretical concepts with practical application.

This software was created by **Isam Abdullah Balghari** under the mentorship of **Dr. Muhammad Sabieh Anwar**.

---

**PhysTrackX** is a user-friendly, visually engaging application designed for physics education and analysis. It allows high school and early undergraduate students to interactively engage with real-world experiments using video analysis, mathematical tools, and data visualization. The software turns ordinary experiment footage into a powerful source of measurement, exploration, and understanding.

<p align="center">
  <img src="https://i.postimg.cc/Pq5XTQkk/app.png" alt="PhysTrackX Demo" width="700"/>
</p>

---

## 🌟 Features

- 📹 **Import Your Own Video Experiments**  
  Load any experimental video to analyze frame-by-frame.

- 🎯 **Interactive Axes Setup**  
  Easily place coordinate axes and adjust scale based on your setup.

- 📏 **Object Marking & Annotation Tools**  
  Mark rectangles, draw shapes, or crop regions of interest.

- 🧠 **OCR Integration**  
  Recognize textual data (like timers or scales) embedded in videos.

- 🧪 **Geometry Plugin**  
  Visualize triangles, angles, and geometric constructs in your footage.

- 📊 **Plotting Tool**  
  View real-time motion plots (position, velocity, acceleration) with a click.

- 💾 **Save & Export Data**  
  Export measurements and plots as CSV or images for reporting.

- 🌌 **Clean, Dark-Themed GUI**  
  Built with `customtkinter` for a smooth and modern interface.

---

## 💻 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/isamabdullah88/phystrackx.git
cd phystrackx
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Run the App

```bash
python tk/phystrackx.py
```

The Qt version (a rewrite in progress) is in `qt/`; see `qt/README.md`.

### 💾 Windows Executable

Windows `.exe` binary versions are available for download [here](https://github.com/isamabdullah88/phystrackx/releases). No Python installation required.

---

## ☕ Support This Project

If PhysTrackX has helped you or your students learn physics better, consider supporting. 

Contribute to science outreach by donating to:

### 👉 [Khwarizmi Science Society](https://khwarizmi.org/support-us/)

---

## 📜 License & Usage

This project is licensed under the **Business Source License 1.1 (BSL)**.

### For Researchers and Students
You are free (and encouraged!) to use this software for **non-commercial** purposes, including:
* Academic research and thesis work.
* Personal learning and experimentation.
* Educational demonstrations.

If you use this work in your research, please provide attribution to **Isam Abdullah Balghari**.

### For Commercial Entities
Use of this software for primary commercial advantage or monetary compensation is **prohibited** until the Change Date (**March 18, 2030**). On that date, the license will automatically convert to the **GNU GPLv3**.

If you are interested in using this technology commercially before 2030, please contact me directly to discuss a commercial license.

---
*For full details, please see the [LICENSE](LICENSE) file.*

---

## 📬 Contact

Have suggestions, ideas, or want to collaborate?

- GitHub: [github.com/isamabdullah88](https://github.com/isamabdullah88)
- Email: isamabdullah88[at]gmail.com

---

## 📜 Acknowledgments & Credits

PhysTrackX relies on open-source software, models, and community assets:

* **Tracking Engine:** [NanoTrack](https://github.com/HaoGao/NanoTrack) deployed via [ONNX Runtime](https://onnxruntime.ai/).
* **OCR Integration:** [Tesseract OCR Engine](https://github.com/tesseract-ocr/tesseract).
* **UI Icons:** Downloaded from [Flaticon](https://www.flaticon.com).
* **Media & Audio:** Background music by *BG4V — Background Music for Videos*.

For a full list of third-party licenses and asset credits, see [ATTRIBUTION.md](ATTRIBUTION.md).
