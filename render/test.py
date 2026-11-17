import bpy, time, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
print('engine', sc.render.engine)
c = sc.cycles
c.device = 'CPU'
c.samples = 48
c.use_denoising = True
try:
    c.denoiser = 'OPENIMAGEDENOISE'
    print('denoiser ok')
except Exception as e:
    print('denoiser fail', e)
sc.render.resolution_x = 640; sc.render.resolution_y = 640
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0,0,1), segments=64, ring_count=32)
ob = bpy.context.object
bpy.ops.object.shade_smooth()
m = bpy.data.materials.new('steel'); m.use_nodes = True
b = m.node_tree.nodes['Principled BSDF']
b.inputs['Metallic'].default_value = 1; b.inputs['Roughness'].default_value = 0.18
b.inputs['Base Color'].default_value = (0.8,0.8,0.82,1)
ob.data.materials.append(m)
bpy.ops.mesh.primitive_plane_add(size=30)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.9,0.9,0.9,1)
bpy.ops.object.light_add(type='AREA', location=(3,-3,5)); L = bpy.context.object; L.data.energy = 800; L.data.size = 4
import mathutils
L.rotation_euler = (mathutils.Vector((0,0,1)) - L.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(4,-5,3)); cam = bpy.context.object
cam.rotation_euler = (mathutils.Vector((0,0,1)) - cam.location).to_track_quat('-Z','Y').to_euler()
sc.camera = cam
sc.render.filepath = sys.argv[-1]
sc.render.image_settings.file_format = 'PNG'
t = time.time(); bpy.ops.render.render(write_still=True); print('render s', round(time.time()-t,1))
