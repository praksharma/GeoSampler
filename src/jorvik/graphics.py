"""Process-start graphics selection; never changes system graphics or sandboxing."""
import os
import shlex
import sys
from pathlib import Path


MODES = ("auto", "software")
DRM_ROOT = Path("/sys/class/drm")
NVIDIA_EGL = Path("/usr/share/glvnd/egl_vendor.d/10_nvidia.json")
NVIDIA_VULKAN = Path("/usr/share/vulkan/icd.d/nvidia_icd.json")
GRAPHICS_OVERRIDES = ("QSG_RHI_BACKEND", "QT_OPENGL", "QT_QUICK_BACKEND",
                      "QTWEBENGINE_CHROMIUM_FLAGS", "__EGL_VENDOR_LIBRARY_FILENAMES",
                      "VK_DRIVER_FILES", "VK_ICD_FILENAMES", "VK_LOADER_LAYERS_DISABLE",
                      "QSG_RHI_PREFER_SOFTWARE_RENDERER", "QT_VK_PHYSICAL_DEVICE_INDEX")
SOFTWARE_FLAGS = ("--use-gl=angle", "--use-angle=swiftshader", "--disable-gpu-compositing")
CONFLICTING_FLAGS = {"--use-gl", "--use-angle", "--use-vulkan", "--disable-gpu",
                     "--disable-gpu-compositing", "--disable-software-rasterizer", "--disable-webgl", "--disable-webgl2"}


def graphics_mode(value):
    return value if isinstance(value, str) and value in MODES else "auto"


def nvidia_wayland_available(environment):
    if not sys.platform.startswith("linux"):
        return False
    if not (environment.get("WAYLAND_DISPLAY") or environment.get("XDG_SESSION_TYPE") == "wayland"):
        return False
    if environment.get("QT_QPA_PLATFORM", "wayland") not in ("", "wayland", "wayland-egl"):
        return False
    if not NVIDIA_EGL.is_file() or not NVIDIA_VULKAN.is_file():
        return False
    active = []
    try:
        for card in DRM_ROOT.glob("card[0-9]*"):
            if not card.name[4:].isdigit():
                continue
            connected = any(path.read_text().strip() == "connected"
                            for path in DRM_ROOT.glob(card.name + "-*/status"))
            if connected:
                active.append((card / "device/vendor").read_text().strip().lower())
    except OSError:
        return False
    # Only one display-driving GPU is unambiguous; do not guess on hybrid setups.
    return active == ["0x10de"]


def configure_graphics(mode, environment=None):
    environment = os.environ if environment is None else environment
    mode = graphics_mode(mode)
    if mode == "software":
        flags = shlex.split(environment.get("QTWEBENGINE_CHROMIUM_FLAGS", ""))
        flags = [flag for flag in flags if flag.split("=", 1)[0] not in CONFLICTING_FLAGS]
        # CPU compositing avoids sharing GL textures with an incompatible desktop driver.
        environment["QTWEBENGINE_CHROMIUM_FLAGS"] = shlex.join([*flags, *SOFTWARE_FLAGS])
        environment["QT_OPENGL"] = "software"
    elif not any(environment.get(key) for key in GRAPHICS_OVERRIDES) and nvidia_wayland_available(environment):
        environment.update({"QSG_RHI_BACKEND": "vulkan",
                            "__EGL_VENDOR_LIBRARY_FILENAMES": str(NVIDIA_EGL),
                            "VK_DRIVER_FILES": str(NVIDIA_VULKAN),
                            "VK_LOADER_LAYERS_DISABLE": "*MESA*"})
    return mode
