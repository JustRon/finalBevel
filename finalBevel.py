import bpy, time
from bpy.props import *

bl_info = {
    "name": "Final Bevel",
    "description": "Bakes accurate bevels into an object based on their bevel weights.",
    "author": "Ron Frölich",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Object > FinalBevel",
    "support": "COMMUNITY",
    "category": "Object"
}

class FinalBevel(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.final_bevel"
    bl_label = "Final Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    #Properties
    bevelWidth = FloatProperty(
        name = "Bevel Width",
        description = "How wide a bevel with a weight of 1 should be (cm)",
        default = 1,
        min = 0.001,
        max = 1000
    )

    bevelProfile = FloatProperty(
        name = "Bevel Profile",
        description = "The profile with which the edges are beveled",
        default = 0.5,
        min = 0.0,
        max = 1.0
    )

    primaryBevelSegments = IntProperty(
        name = "Primary Bevel Segments",
        description = "How many segments to use for the edges with the highest bevel weight",
        default = 6,
        min = 2,
        max = 100
    )

    secondaryBevelSegments = IntProperty(
        name = "Secondary Bevel Segments",
        description = "How many segments to use for the edges with the second highest bevel weight",
        default = 4,
        min = 2,
        max = 100
    )

    tertiaryBevelSegments = IntProperty(
        name = "Tertiary Bevel Segments",
        description = "How many segments to use for the remaining edges",
        default = 2,
        min = 2,
        max = 100
    )

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'OBJECT')

    def execute(self, context):

        so = bpy.context.active_object
        edges = so.data.edges
        verts = so.data.vertices
        so.data.use_customdata_edge_bevel = True
        bevelWeights = []

        for e in edges:
            if e.bevel_weight != 0.0:
                e.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

        for e in edges:
            if e.bevel_weight != 0.0:
                if bevelWeights.count(e.bevel_weight) == 0:
                    bevelWeights.append(e.bevel_weight)

        bevelWeights.sort(reverse=True)


        for i in range(len(bevelWeights)):

           #Fill up newly created edges with their appropriate bevel weights - We skip this for the first iteration

            if i != 0:
                currentBevelWeightEdgesVerticesIndices = []
                higherBevelWeightEdgesVerticesIndices = []
                overlappingVerticesIndices = []

                for e in edges:
                    if e.bevel_weight == bevelWeights[i]:
                        for v in e.vertices:
                            if currentBevelWeightEdgesVerticesIndices.count(v) == 0:
                                currentBevelWeightEdgesVerticesIndices.append(v)
                    elif e.bevel_weight > bevelWeights[i]:
                        for v in e.vertices:
                            higherBevelWeightEdgesVerticesIndices.append(v)

                for v in currentBevelWeightEdgesVerticesIndices:
                    if(higherBevelWeightEdgesVerticesIndices.count(v) >0):
                        overlappingVerticesIndices.append(v)

                #Finding Vertex Pairs for overlapping vertices

                for o in range(len(overlappingVerticesIndices)):
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_mode(type="VERT")
                    bpy.ops.object.mode_set(mode='OBJECT')

                    verts[overlappingVerticesIndices[o]].select = True

                    if higherBevelWeightEdgesVerticesIndices.count(overlappingVerticesIndices[o]+1) > 0:
                        verts[overlappingVerticesIndices[o]+1].select = True
                    elif higherBevelWeightEdgesVerticesIndices.count(overlappingVerticesIndices[o]-1) > 0:
                        verts[overlappingVerticesIndices[o]-1].select = True

                    bpy.ops.object.mode_set(mode='EDIT')
                    r = bpy.ops.mesh.shortest_path_select()
                    bpy.ops.object.mode_set(mode='OBJECT')
                    for edge in edges:
                        if edge.select:
                            edge.bevel_weight=bevelWeights[i]
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='DESELECT')
                    bpy.ops.mesh.select_mode(type="EDGE")
                    bpy.ops.object.mode_set(mode='OBJECT')

            #Find all edges with the current iterations bevel weight and bevel them

            for e in edges:
                if e.bevel_weight == bevelWeights[i]:
                    e.select = True

            bpy.ops.object.mode_set(mode='EDIT')
            if i == 0:
                bpy.ops.mesh.bevel(offset = (self.bevelWidth * .01) * bevelWeights[i], segments = self.primaryBevelSegments, profile = self.bevelProfile, miter_outer='ARC')
            elif i == 1:
                bpy.ops.mesh.bevel(offset = (self.bevelWidth * .01) * bevelWeights[i], segments = self.secondaryBevelSegments, profile = self.bevelProfile, miter_outer='ARC')
            else:
                bpy.ops.mesh.bevel(offset = (self.bevelWidth * .01) * bevelWeights[i], segments = self.tertiaryBevelSegments, profile = self.bevelProfile, miter_outer='ARC')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

def mesh_object_menu_draw(self, context):
    self.layout.operator('object.final_bevel')

def register():
    bpy.utils.register_class(FinalBevel)
    bpy.types.VIEW3D_MT_object.append(mesh_object_menu_draw)


def unregister():
    bpy.utils.unregister_class(FinalBevel)
    bpy.types.VIEW3D_MT_object.remove(mesh_object_menu_draw)
