import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SECO"] = "1"
import moodle_abertos
moodle_abertos.main()
