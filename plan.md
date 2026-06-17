# Basler GigE Camera → OBS Integration Plan

## Project Overview

**Goal:** Stream video from Basler DMF4-37gm GigE Vision camera into OBS Studio for local preview and future remote viewing (Google Meet/Teams).

---

## 1. Hardware Specifications

| Property | Value |
|----------|-------|
| Camera Model | Basler dmA2048-37gm (Dart series) |
| Resolution | 2048x1536 (monochrome) |
| Connection Type | RJ45 Gigabit Ethernet |

---

## 2. Required Software Stack

### 2.1 Basler Pylon SDK

| Component | Purpose | Download Source |
|-----------|---------|-----------------|
| Pylon Runtime (v6.x+) | Core camera SDK, DLLs for Windows | https://www.baslerweb.com/downloads/ |
| PEPYSONIC Plugin | Python/C# bindings for frame streaming | Same installer includes |

**Installation Notes:**
- Use the Basler Setup Assistant to install both Runtime and Plugins
- Default installation path: `C:\Program Files\Basler\Pylon SDK v6.x`
- Keep default paths for DLL compatibility with OBS plugin

### 2.2 Development Environment (Choice)

| Option | Tools Required | When to Use |
|--------|----------------|-------------|
| **Python + PEPYSONIC** | Python 3.x, pip, virtual environment | Quick prototype, script-based control |
| **C++ Plugin Dev** | Visual Studio 2019+, CMake, OBS SDK | Production OBS source plugin |
| **C# (.NET)** | .NET 6/7, PEPYSONIC NuGet | If using Unity/Windows Forms GUI |

### 2.3 OBS Studio

- Version: Stable build (v30+)
- Plugin folder location: `%APPDATA%\OBS Studio\obs-plugins\win64`

---

## 3. Network Requirements

| Requirement | Specification |
|-------------|---------------|
| Cable | CAT5e or better (1 Gbps) |
| Switch | Gigabit Ethernet managed/unmanaged switch |
| Camera IP | DHCP or static configuration via Pylon |
| PC Subnet | Same VLAN/subnet as camera (recommended) |
| Bandwidth | ~80-90 Mbps at 1280x1024 @ 15 FPS (monochrome) |

---

## 4. Implementation Path

### Phase 1: Pylon SDK Setup (Week 1)

**Tasks:**
- [ ] Download and install Basler Pylon Runtime v6.x
- [ ] Verify installation: Run `pylon-examples.exe` from Pylon bin directory
- [ ] Document DLL paths in `%APPDATA%\Basler\PEPYSOONIC`

**Documentation Sources:**
- User Guide: `C:\Program Files\Basler\Pylon SDK v6.x\docs\user-guide.pdf`
- API Reference: `C:\Program Files\Basler\Pylon SDK v6.x\docs\api-reference.pdf`
- Sample Code: `C:\Program Files (x86)\Basler\Samples\Python`

### Phase 2: Camera Connection & Testing (Week 1)

**Tasks:**
- [ ] Connect camera to network via RJ45
- [ ] Configure IP address on camera using Pylon Config Tool (if needed)
- [ ] Create test Python/C++ application that initializes camera
- [ ] Capture first frame and verify video output in preview window

**API Summary - Camera Initialization:**
```python
# Python PEPYSONIC example structure
import pylon
camera = pylon.SpVideoInput.GetFirstByManufacturer("Basler")
camera.Open()  # Initializes GigE camera
camera.StartAcquisition(pylon.AcquisitionType.Continuous)
```

### Phase 3: Stream Output Implementation (Week 2-3)

**Option A: OBS Plugin (C++)**
- Implement IObsSource, IObsProperties, IObsRenderer interfaces
- Create DLL output plugin in `obs-plugins\win64`
- Use PEPYSONIC to push frames into OBS video source queue

**Option B: Virtual Webcam Alternative** ⭐ **RECOMMENDED**
- Serve camera frames via pyvirtualcam virtual camera
- OBS can ingest as "Video Capture Device" (Virtual Camera)
- Simpler deployment, no plugin development required
- Example: [pypylon-webcam repo](https://github.com/FredericDlugi/pypylon-webcam)

---

## 5. Documentation Deliverables

| Document | Status | Location |
|----------|--------|----------|
| SDK Setup Guide | Pending | plan.md (this file) |
| API Reference Notes | Pending | plan.md / external links |
| Plugin Development Guide | External | OBS SDK GitHub repo |
| Sample Code Repository | Existing | [pypylon-webcam](https://github.com/FredericDlugi/pypylon-webcam) |

---

## 6. **REPO VIABILITY ASSESSMENT** ⭐ NEW

### Repository: `pypylon-webcam` (Existing Project)

**Status:** ✅ **Viable Alternative Approach Confirmed**

#### Architecture Overview
- **GUI Framework:** PyQt5 with threaded architecture
- **Camera SDK:** PYPYTHON (Python bindings for Basler Pylon SDK)
- **Virtual Output:** `pyvirtualcam` → OBS Virtual Camera device
- **Face Detection:** OpenCV DNN face detection with auto-tracking - not needed

#### Key Features
| Feature | Implementation |
|---------|---------------|
| Camera Discovery | Pylon TlFactory enumeration |
| Frame Grabbing | GrabThread (multithreaded) |
| Virtual Output | pyvirtualcam (VGA 640x480 @ 30 FPS default) |
| Preview Window | OpenCV named window with face bounding box overlay |
| Face Detection | OpenCV DNN TensorFlow model - Not needed|
| Auto-Tracking | Automatic camera panning to center detected faces - not needed |
| Camera Controls | Brightness, contrast, gamma, saturation, hue, sharpness sliders |

#### Project Structure
```
main.py                    # PyQt5 application entry point
grab_thread.py            # Frame grabbing thread (Pylon → virtualcam)
preview_thread.py         # OpenCV preview window
face_detector_thread.py   # Face detection pipeline - not needed 
face_finder.py            # OpenCV DNN face detection logic - not needed
config_gui.py             # Camera discovery & settings GUI
settings.py               # JSON-based config persistence
requirements.txt          # Python dependencies (pypylon, pyvirtualcam)
```

#### Requirements
```
numpy==1.20.3
opencv-python==4.5.2.52
pypylon==1.7.2
PyQt5==5.15.4
pyvirtualcam==0.8.0
```

---

### Viability Analysis

| Aspect | Assessment | Notes |
|--------|------------|-------|
| **Camera Support** | ✅ Compatible | PYPYTHON supports GigE cameras including dmA2048 series |
| **OBS Integration** | ✅ Verified | pyvirtualcam creates virtual camera detected by OBS as "Video Capture Device" |
| **Deployment Complexity** | 🟢 Low | Single Python install + OBS restart, no DLL registration needed |
| **Performance** | 🟡 Moderate | Face detection at ~0.1 FPS (controlled via sleep), suitable for webcam use; Not part of my goal|
| **Code Maturity** | 🟠 Partially Complete | Core functionality exists; needs camera model compatibility check |
| **Documentation** | 🟠 Basic | README exists but limited; plan.md can serve as documentation |

#### Strengths
- ✅ No OBS plugin development required (avoids C++ complexity)
- ✅ Python-only dependencies, cross-platform potential
- ✅ Built-in preview window for testing before streaming
- ✅ Face centering/auto-tracking features built-in
- ✅ Camera settings GUI for runtime adjustment

#### Considerations
- ⚠️ **Camera Resolution:** Repository tested with daA1920; dmA2048 (monochrome 2048x1536) needs resolution format conversion check
- ⚠️ **Color Format:** Pylon GigE monochrome cameras may need BGR/YUV conversion for virtualcam
- ⚠️ **Face Detection Model:** OpenCV DNN model expects color images; convert monochrome appropriately

---

### Recommended Approach: Hybrid Implementation

**Phase 1A (Weeks 1-2): Use Existing Repo as Foundation**
```
1. Clone pypylon-webcam repo
2. Install requirements (pip install -r requirements.txt)
3. adapt for dmA2048
4. Configure resolution to target OBS input format 
5. Verify virtual camera detected by OBS Studio
```

**Phase 2 (Week 3): Integration & Testing**
```
1. Load plugin in OBS Studio → Add Source → Video Capture Device
2. Validate frame rate, latency, resolution settings
3. Test full pipeline end-to-end with conferencing apps
```

**Phase 3 (Future): Optimization (Optional)**
```
- If monochrome quality not sufficient: Consider color camera or image processing
```

---

### Revised Timeline (With Existing Repo)

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| SDK Setup & Config | 1 week | Pylon installed, camera discovered |
| Repo Adaptation | 1-2 weeks | pypylon-webcam running with dmA2048 |
| OBS Integration Test | 1 week | Full virtual cam pipeline verified |

**Total Estimated: 3-4 weeks (vs. 6+ weeks for custom OBS plugin)**


---

## 8. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| USB to GigE adapter incompatibility | Medium | Use true Ethernet, not USB adaptors |
| Pylon SDK version conflicts with OBS | Low | Test plugin compatibility before install |
| Camera resolution/FPS limits | Medium | Verify max FPS at target resolution early |


---

## 9. **RECOMMENDED NEXT STEPS** ⭐ UPDATED

### Immediate Actions (Week 1)

1. **Review existing pypylon-webcam repo**
   - Check `grab_thread.py` for BGR8 output format handling
   - Verify pyvirtualcam configuration matches OBS requirements
   - Identify any dmA2048-specific configuration needed

2. **Install Basler Pylon SDK v6.x**
   - Follow Phase 1 tasks from plan.md
   - Document installation paths for dependency resolution

3. **Create test virtual camera application**
   ```python
   # Minimal test script to verify setup
   import pypylon
   from pypylon import pylon
   
   camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFromAddress("192.168.1.100"))
   camera.Open()
   camera.PixelFormat = "BGR8"  # Required for pyvirtualcam
   ```

### Week 2-3: Integration

4. **Adapt pypylon-webcam for dmA2048** (if needed)
   - Modify resolution settings in `grab_thread.py`
   - Test face detection with monochrome input
   - Adjust `face_finder.py` confidence threshold if needed

5. **OBS Integration Testing**
   - Install OBS Studio stable build
   - Add "Video Capture Device" source pointing to virtual camera
   - Validate end-to-end streaming pipeline

### Week 4+: Optimization

6. **Performance Tuning**
   - Adjust FPS settings for target use case
   - Optimize face detection frequency if real-time tracking needed
   - Test conferencing app compatibility (Meet/Teams)

---

## 10. Conclusion & Recommendation

**The pypylon-webcam repository provides a Viable Alternative Implementation Path** that:

- ✅ Avoids complex OBS plugin development (C++ DLL, IObsSource interfaces)
- ✅ Uses Python-only stack for simpler deployment
- ✅ Includes preview window and face tracking features "out of the box"
- ⚠️ Requires adaptation for dmA2048 monochrome camera specifics

**Recommended Path:** Proceed with existing repo as base, adapt for target hardware → deploy virtual webcam → integrate into OBS. This is **more viable** than building custom OBS plugin from scratch.

---

*Last Updated: 2026-06-15*