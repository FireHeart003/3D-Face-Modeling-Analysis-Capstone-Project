import argparse
import io
import sys
from pathlib import Path
from flask import Flask, request, send_file, jsonify, Response
from flask_cors import CORS
from PIL import Image

sys.path.insert(0, ".")

from face_renderer.filament_renderer import FaceRenderer
from face_renderer.make_head_only import make_head_only_obj, build_head_face_mask_by_y
from face_renderer.obj_to_glb import obj_to_glb

# ---------------------------------------------------------------------------
# Defaults/Global Vars
# ---------------------------------------------------------------------------
DEFAULT_OBJ     = "tests/assets/makehuman_raw/mesh.obj" # Input OBJ File
DEFAULT_OBJ_OUT = "out_face_milestone3/head_only.obj" # Where head-only OBJ will be saved
DEFAULT_GLB     = "out_face_milestone3/head_only.glb" # The Cached GLB file
DEFAULT_PORT    = 8000

app = Flask(__name__)
CORS(app)

renderer     = None
current_glb  = None
current_size = 512

# ---------------------------------------------------------------------------
# HTML viewer
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Face Viewer</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #1a1a1a; color: #e0e0e0;
    height: 100vh; display: flex; flex-direction: column; overflow: hidden;
  }
  header {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; background: #111;
    border-bottom: 1px solid #333; flex-shrink: 0;
  }
  header h1 { font-size: 15px; font-weight: 500; color: #ccc; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #444; flex-shrink: 0; }
  .dot.ok   { background: #4caf50; }
  .dot.busy { background: #ff9800; animation: pulse 0.8s ease-in-out infinite; }
  .dot.err  { background: #f44336; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  #status-text { font-size: 12px; color: #888; }
  .main { display: flex; flex: 1; overflow: hidden; }

  /* Viewport */
  .viewport {
    flex: 1; position: relative;
    display: flex; align-items: center; justify-content: center;
    background: #1a1a1a; cursor: grab; overflow: hidden;
  }
  .viewport.dragging { cursor: grabbing; }
  #face-img {
    max-width: 100%; max-height: 100%;
    object-fit: contain; display: block;
    pointer-events: none; user-select: none; -webkit-user-drag: none;
  }
  .placeholder { text-align: center; color: #555; font-size: 14px; line-height: 2.2; }
  .placeholder .big { font-size: 52px; }
  .loading-ring {
    position: absolute; top: 12px; right: 12px;
    width: 20px; height: 20px;
    border: 2px solid #444; border-top-color: #aaa;
    border-radius: 50%; animation: spin 0.6s linear infinite;
    opacity: 0; transition: opacity 0.1s;
  }
  .loading-ring.active { opacity: 1; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .hint {
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
    font-size: 11px; color: #666;
    background: #111; border: 1px solid #333; border-radius: 20px;
    padding: 4px 12px; white-space: nowrap; pointer-events: none;
  }

  /* Sidebar */
  .sidebar {
    width: 220px; flex-shrink: 0; background: #111;
    border-left: 1px solid #333;
    display: flex; flex-direction: column;
    padding: 16px 14px; gap: 14px; overflow-y: auto;
  }
  .section-title {
    font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.08em; color: #555; margin-bottom: 2px;
  }
  .ctrl { display: flex; flex-direction: column; gap: 4px; }
  .ctrl-row { display: flex; justify-content: space-between; align-items: center; }
  .ctrl-row label { font-size: 12px; color: #aaa; }
  .ctrl-row .val  { font-size: 12px; font-weight: 500; color: #ddd; min-width: 42px; text-align: right; }
  input[type=range] { width: 100%; accent-color: #7c8cf8; cursor: pointer; }
  .divider { height: 1px; background: #2a2a2a; flex-shrink: 0; }
  button {
    width: 100%; padding: 7px 0; font-size: 12px; font-family: inherit;
    background: #1e1e1e; color: #ccc; border: 1px solid #333; border-radius: 6px;
    cursor: pointer; transition: background 0.15s;
  }
  button:hover { background: #2a2a2a; color: #fff; }
  button.primary { background: #2d3561; border-color: #4a55a2; color: #c5caf7; }
  button.primary:hover { background: #3a4480; }
  button.danger  { background: #3d2020; border-color: #8b3a3a; color: #f7c5c5; }
  button.danger:hover  { background: #4f2828; }
  .btn-group { display: flex; flex-direction: column; gap: 6px; }
  .info-text { font-size: 11px; color: #555; line-height: 1.7; }
  .info-text kbd {
    font-size: 10px; background: #222; border: 1px solid #444;
    border-radius: 3px; padding: 1px 5px; color: #888; font-family: inherit;
  }
</style>
</head>
<body>

<header>
  <h1>Face Viewer</h1>
  <div class="dot busy" id="dot"></div>
  <span id="status-text">loading…</span>
</header>

<div class="main">
  <div class="viewport" id="viewport"
    onmousedown="startDrag(event)"
    onmousemove="onDrag(event)"
    onmouseup="endDrag()"
    onmouseleave="endDrag()">
    <div class="placeholder" id="placeholder">
      <div class="big">⬡</div>
      Loading model…
    </div>
    <img id="face-img" src="" alt="" style="display:none;" />
    <div class="loading-ring" id="ring"></div>
    <div class="hint">drag to orbit &nbsp;·&nbsp; scroll to zoom</div>
  </div>

  <div class="sidebar">
    <div>
      <div class="section-title">Camera</div>
      <div style="display:flex;flex-direction:column;gap:10px;margin-top:6px;">
        <div class="ctrl">
          <div class="ctrl-row"><label>Yaw</label><span class="val" id="v-yaw">0°</span></div>
          <input type="range" id="s-yaw" min="-180" max="180" value="0" step="1" oninput="onSlider()">
        </div>
        <div class="ctrl">
          <div class="ctrl-row"><label>Pitch</label><span class="val" id="v-pitch">0°</span></div>
          <input type="range" id="s-pitch" min="-89" max="89" value="0" step="1" oninput="onSlider()">
        </div>
        <div class="ctrl">
          <div class="ctrl-row"><label>Radius</label><span class="val" id="v-radius">auto</span></div>
          <input type="range" id="s-radius" min="-1" max="800" value="-1" step="1" oninput="onSlider()">
        </div>
      </div>
    </div>



    <div class="divider"></div>

    <div class="btn-group">
      <button onclick="resetCam()">↺  Reset camera</button>
      <button class="primary" onclick="toggleTurntable()" id="tt-btn">▶  Turntable</button>
      <button onclick="saveFrame()">⬇  Save PNG</button>
    </div>

    <div class="divider"></div>

    <div class="info-text">
      <kbd>drag</kbd> orbit &nbsp;<kbd>scroll</kbd> zoom<br>
      Turntable spins full 360°.<br>
      Save PNG captures current view.
    </div>
  </div>
</div>

<script>
let yaw = 0, pitch = 0, radius = -1;
let busy = false;
let dragging = false;
let lastX = 0, lastY = 0;
let ttTimer = null;

function setStatus(state, text) {
  document.getElementById('dot').className = 'dot ' + state;
  document.getElementById('status-text').textContent = text;
}
function setLoading(on) {
  document.getElementById('ring').classList.toggle('active', on);
}

function fetchFrame() {
  if (busy) return;
  busy = true;
  setLoading(true);
  const r = Math.round(radius);
  const url = '/render?yaw=' + Math.round(yaw) +
              '&pitch=' + Math.round(pitch) +
              '&radius=' + r +
              '&t=' + Date.now();
  const tmp = new Image();
  tmp.onload = function() {
    const img = document.getElementById('face-img');
    img.src = tmp.src;
    img.style.display = 'block';
    document.getElementById('placeholder').style.display = 'none';
    setLoading(false);
    setStatus('ok', 'yaw ' + Math.round(yaw) + '°  pitch ' + Math.round(pitch) + '°  r ' + (r < 0 ? 'auto' : r));
    busy = false;
  };
  tmp.onerror = function() {
    setLoading(false);
    setStatus('err', 'render failed — is the server running?');
    busy = false;
  };
  tmp.src = url;
}

function syncUI() {
  document.getElementById('s-yaw').value    = yaw;
  document.getElementById('s-pitch').value  = pitch;
  document.getElementById('s-radius').value = radius;
  document.getElementById('v-yaw').textContent   = Math.round(yaw) + '°';
  document.getElementById('v-pitch').textContent = Math.round(pitch) + '°';
  document.getElementById('v-radius').textContent = radius < 0 ? 'auto' : Math.round(radius);
}

function onSlider() {
  yaw    = parseFloat(document.getElementById('s-yaw').value);
  pitch  = parseFloat(document.getElementById('s-pitch').value);
  radius = parseFloat(document.getElementById('s-radius').value);
  syncUI();
  if (!busy) fetchFrame();
}

// Drag to orbit
function startDrag(e) {
  e.preventDefault();
  if (e.button !== 0) return;
  dragging = true;
  lastX = e.clientX; lastY = e.clientY;
  document.getElementById('viewport').classList.add('dragging');
}
function onDrag(e) {
  if (!dragging) return;
  const dx = e.clientX - lastX;
  const dy = e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY;
  yaw   = ((yaw - dx * 0.4) % 360 + 540) % 360 - 180;
  pitch = Math.max(-89, Math.min(89, pitch + dy * 0.3));
  syncUI();
  if (!busy) fetchFrame();
}
function endDrag() {
  dragging = false;
  document.getElementById('viewport').classList.remove('dragging');
}

// Scroll to zoom
document.getElementById('viewport').addEventListener('wheel', function(e) {
  e.preventDefault();
  if (radius < 0) radius = 300;
  radius = Math.max(50, Math.min(800, radius + e.deltaY * 0.4));
  syncUI();
  if (!busy) fetchFrame();
}, { passive: false });

// Touch orbit
let lastTX = 0, lastTY = 0, touching = false;
document.getElementById('viewport').addEventListener('touchstart', function(e) {
  if (e.touches.length !== 1) return;
  lastTX = e.touches[0].clientX; lastTY = e.touches[0].clientY;
  touching = true;
}, { passive: true });
document.getElementById('viewport').addEventListener('touchmove', function(e) {
  if (!touching || e.touches.length !== 1) return;
  const dx = e.touches[0].clientX - lastTX;
  const dy = e.touches[0].clientY - lastTY;
  lastTX = e.touches[0].clientX; lastTY = e.touches[0].clientY;
  yaw   = ((yaw - dx * 0.4) % 360 + 540) % 360 - 180;
  pitch = Math.max(-89, Math.min(89, pitch + dy * 0.3));
  syncUI();
  if (!busy) fetchFrame();
  e.preventDefault();
}, { passive: false });
document.getElementById('viewport').addEventListener('touchend', function() { touching = false; });

// Buttons
function resetCam() {
  yaw = 0; pitch = 0; radius = -1;
  syncUI(); fetchFrame();
}

function toggleTurntable() {
  const btn = document.getElementById('tt-btn');
  if (ttTimer) {
    clearInterval(ttTimer); ttTimer = null;
    btn.textContent = '▶  Turntable';
    btn.className = 'primary';
    return;
  }
  btn.textContent = '■  Stop';
  btn.className = 'danger';
  ttTimer = setInterval(function() {
    if (busy) return;
    yaw = ((yaw + 2) % 360 + 540) % 360 - 180;
    syncUI(); fetchFrame();
  }, 100);
}

function saveFrame() {
  const a = document.createElement('a');
  a.href = '/render?yaw=' + Math.round(yaw) + '&pitch=' + Math.round(pitch) +
           '&radius=' + Math.round(radius);
  a.download = 'face_yaw' + Math.round(yaw) + '_pitch' + Math.round(pitch) + '.png';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// Boot
syncUI();
setStatus('busy', 'loading model…');
setTimeout(fetchFrame, 400);
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "glb": current_glb, "size": current_size})


@app.route("/render")
def render_view():
    yaw    = float(request.args.get("yaw",    0))
    pitch  = float(request.args.get("pitch",  0))
    radius = float(request.args.get("radius", -1))

    renderer.set_camera(yaw=yaw, pitch=pitch, radius=radius)
    pixels = renderer.render()

    img = Image.fromarray(pixels, "RGBA")
    bg  = Image.new("RGBA", img.size, (255, 255, 255, 255))
    final = Image.alpha_composite(bg, img).convert("RGB")

    buf = io.BytesIO()
    final.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_renderer(size):
    return FaceRenderer(size, size, "filament_dist")


def _build_glb(obj_in, obj_out, glb_out):
    obj_in  = Path(obj_in)
    obj_out = Path(obj_out)
    glb_out = Path(glb_out)

    if glb_out.exists():
        print(f"Using cached GLB: {glb_out}")
        return str(glb_out)

    print("Building head-only OBJ...")
    mask = build_head_face_mask_by_y(str(obj_in), keep_top_percent=0.13)
    make_head_only_obj(str(obj_in), str(obj_out), mask)
    print(f"  OK OBJ: {obj_out}")

    print("Converting OBJ -> GLB...")
    obj_to_glb(str(obj_out), str(glb_out))
    print(f"  OK GLB: {glb_out}")
    return str(glb_out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filament face viewer server")
    parser.add_argument("--obj",     default=DEFAULT_OBJ,     help="Input full-body OBJ")
    parser.add_argument("--obj-out", default=DEFAULT_OBJ_OUT, help="Head-only OBJ output path")
    parser.add_argument("--glb",     default=DEFAULT_GLB,     help="GLB path (built if missing)")
    parser.add_argument("--port",    default=DEFAULT_PORT, type=int)
    parser.add_argument("--size",    default=512, type=int,   help="Render resolution")
    parser.add_argument("--preview", default="out_face_milestone3/preview.png",
                        help="Path to save the startup preview image")
    args = parser.parse_args()

    # ── Step 1: build head-only OBJ + GLB (cached if already exists) ──────────
    current_glb = _build_glb(args.obj, args.obj_out, args.glb)

    # ── Step 2: create renderer and load model ────────────────────────────────
    print(f"Creating renderer ({args.size}x{args.size})...")
    current_size = args.size
    renderer = _make_renderer(args.size)
    renderer.load_model(current_glb)
    print("Renderer ready")

    # ── Step 3: save a preview.png at yaw=0, pitch=0 (same as test_renderer) ──
    preview_path = Path(args.preview)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving preview -> {preview_path}")
    renderer.set_camera(yaw=0.0, pitch=0.0, radius=-1.0)
    pixels = renderer.render()
    img = Image.fromarray(pixels, "RGBA")
    bg  = Image.new("RGBA", img.size, (255, 255, 255, 255))
    Image.alpha_composite(bg, img).convert("RGB").save(str(preview_path))
    print(f"  Saved: {preview_path}")

    # ── Step 4: start the live viewer server ──────────────────────────────────
    print(f"\n  Open in browser:  http://localhost:{args.port}\n")
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=False)