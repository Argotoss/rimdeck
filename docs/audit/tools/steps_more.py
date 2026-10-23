import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("sf", str(pathlib.Path(__file__).with_name("steps_full.py")))
sf = importlib.util.module_from_spec(spec); spec.loader.exec_module(sf)
STEPS = [("40_clean", 3, sf.close_popups)] + [s for s in sf.STEPS if s[0][:2] in ("26","27","28","29","30","31","32","33")]
