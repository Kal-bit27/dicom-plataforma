import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
print(RX(90) @ Vector((0, 1, 0, 0)), RZ(-28) @ Vector((0, 1, 0, 0)))
reset(100, 4)
b = box('b', 1, 1, 1)
place(b, T(0, 0, 16 * MM), RX(-90))
bpy.context.view_layer.update()
print(b.matrix_world)
