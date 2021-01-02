import bpy, time
from bpy.props import FloatProperty, IntProperty,BoolProperty, PointerProperty
from bpy.types import Operator,Panel,PropertyGroup

bl_info = {
    "name": "Final Bevel",
    "description": "Bakes accurate bevels into an object based on their bevel weights.",
    "author": "Ron Frölich",
    "version": (0, 3),
    "blender": (2, 80, 0),
    "location": "3D View > Sidebar",
    "support": "COMMUNITY",
    "category": "Object"
}

def updatePanelValues(self, context):
    if bpy.context.active_object.finalBevel.finalBevelActive:
        bpy.ops.object.stop_final_bevel()
        bpy.ops.object.final_bevel()

def saveBackupMesh():
    so = bpy.context.active_object
    meshBackup = bpy.data.meshes.new_from_object(so)
    meshBackup.name = so.name + "(FinalBevelBackup)"

    so['finalBevelBackup'] = meshBackup

def retrieveBackupMesh():
    so = bpy.context.active_object
    oldName = so.data.name
    oldData = so.data
    so.data = so['finalBevelBackup']
    bpy.data.meshes.remove(oldData)
    so.data.name = oldName
    del so['finalBevelBackup']

class FB_Addon_Props(PropertyGroup):

    bevelWidth: FloatProperty(
        name = "Bevel Width",
        description = "How wide a bevel with a weight of 1 should be (cm)",
        default = 20,
        min = 0.001,
        max = 1000,
        update=updatePanelValues
    )

    bevelProfile: FloatProperty(
        name = "Bevel Profile",
        description = "The profile with which the edges are beveled",
        default = 0.5,
        min = 0.0,
        max = 1.0,
        update=updatePanelValues
    )

    primaryBevelSegments: IntProperty(
        name = "Primary Bevel Segments",
        description = "How many segments to use for the edges with the highest bevel weight",
        default = 4,
        min = 2,
        max = 100,
        update=updatePanelValues
    )

    clampOverlap: BoolProperty(
        name = "Clamp Overlap",
        description = "Whether to use clamp overlap on any bevel iteration",
        default = False,
        update=updatePanelValues
    )

    finalBevelActive: BoolProperty(
        name = "Final Bevel Active",
        description = "Whether Final Bevel is active at the moment. Necessary to define UI and figure out what to do",
        default = False,
    )

class ToggleFinalBevel(bpy.types.Operator):
    bl_idname = 'object.toggle_final_bevel'
    bl_label = "Final Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'OBJECT')
        
    def execute(self, context):

        if bpy.context.active_object.finalBevel.finalBevelActive:
            bpy.ops.object.stop_final_bevel()
        else:
            bpy.ops.object.final_bevel()

        return {'FINISHED'} 

class StopFinalBevel(bpy.types.Operator):
    bl_idname = 'object.stop_final_bevel'
    bl_label = "Stop Final Bevel"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'OBJECT')

    def execute(self, context):
        so = bpy.context.active_object
        fb = so.finalBevel

        fb.finalBevelActive = False
        retrieveBackupMesh()
        return {'FINISHED'} 

class FinalBevel(bpy.types.Operator):
    """Tooltip"""
    bl_idname = 'object.final_bevel'
    bl_label = "Final Bevel"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'OBJECT')

    def execute(self, context):
        # then = time.time() #Time before the operations start

        saveBackupMesh()        

        # Setup stuff
        so = bpy.context.active_object
        fb = so.finalBevel
        faces = so.data.polygons
        edges = so.data.edges
        verts = so.data.vertices
        so.data.use_customdata_edge_bevel = True
        so.data.use_customdata_vertex_bevel = True

        fb.finalBevelActive = True

        currentBevelSegments = fb.primaryBevelSegments

        #Everything needs to be deselected
        faces.foreach_set("select", (False,) * len(faces))
        edges.foreach_set("select", (False,) * len(edges))
        verts.foreach_set("select", (False,) * len(verts))

        #Putting our mesh into edge mode, making sure no faces are hidden and selecting all non-manifold edges while we're at it
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.reveal(select = False)
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.object.mode_set(mode='OBJECT')

        #Saving all our different bevel weights into a list
        bevelWeights = []
        for e in edges:
            if e.bevel_weight != 0.0:
                if bevelWeights.count(e.bevel_weight) == 0:
                    bevelWeights.append(e.bevel_weight)

        #Removing bevel weights from non-manifold edges to avoid edge case issues and performance impacts. Non-manifold edges cannot be beveled anyway.
        nonManifoldEdges = [e for e in edges if e.select == True]
        for edge in nonManifoldEdges:
            edge.bevel_weight = 0.0  

        #Deselecting everything again
        faces.foreach_set("select", (False,) * len(faces))
        edges.foreach_set("select", (False,) * len(edges))
        verts.foreach_set("select", (False,) * len(verts))

        #Let's make sure our bevel weights are sorted largest to smallest
        bevelWeights.sort(reverse=True)
        
        #Iterating through the mesh based on the amount of bevel weights we have
        for i in range(len(bevelWeights)):

            #Let's select all edges with the current bevel weight assigned and bevel them
            currentBevelWeightEdges = [e for e in edges if e.bevel_weight == bevelWeights[i]]
            for edge in currentBevelWeightEdges:
                edge.select = True
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.bevel(offset = (fb.bevelWidth * .01) * bevelWeights[i], segments = currentBevelSegments, profile = fb.bevelProfile,clamp_overlap=fb.clampOverlap, miter_outer='ARC')
            bpy.ops.mesh.region_to_loop()   #There are edges cases where not all newly created edges are assigned the same bevel weight as the edges had previously, this tries to compensate for these edge cases. Could potentially cause other edges cases.
            bpy.ops.object.mode_set(mode='OBJECT')
            
            boundaryEdges = [e for e in edges if e.select == True and e.bevel_weight == 0.0]
            for e in boundaryEdges:
                e.bevel_weight = bevelWeights[i]

            #Deselect everything again
            faces.foreach_set("select", (False,) * len(faces))
            edges.foreach_set("select", (False,) * len(edges))
            verts.foreach_set("select", (False,) * len(verts))

            #This is the part where we find all the newly created edges that need their bevel weights assigned before we can bevel again

            if i < (len(bevelWeights) - 1):

                for v in verts:
                    v.bevel_weight = 0.0

                newCurrentBevelWeightEdges = [e for e in edges if e.bevel_weight >= bevelWeights[i]]
                for edge in newCurrentBevelWeightEdges:
                    for v in edge.vertices:
                        if edge.bevel_weight > verts[v].bevel_weight:
                            verts[v].bevel_weight = edge.bevel_weight #Assigning all the vertices that make up the edges of the previous bevel weight the same bevel weight to find them more easily later

                nextBevelWeightEdges = [e for e in edges if e.bevel_weight == bevelWeights[i+1]]
                for edge in nextBevelWeightEdges:
                    for v in edge.vertices:
                        if verts[v].bevel_weight > bevelWeights[i+1]:
                            verts[v].select = True

                extendBevelWeightVerticesIndices = [v.index for v in verts if v.select] #Saving all vertices that may need to be used to extend bevel weights

                for vI in extendBevelWeightVerticesIndices:
                    if verts[(vI - 1)] and verts[(vI - 1)].bevel_weight >= bevelWeights[i]: 
                        verts[(vI - 1)].select = True
                        for o in range(fb.primaryBevelSegments-1):
                            verts[(vI+1+(o))].select = True
                    elif verts[(vI + 1)] and verts[(vI + 1)].bevel_weight >= bevelWeights[i]: 
                        verts[(vI + 1)].select = True
                        for o in range(fb.primaryBevelSegments-1):
                            verts[(vI+2+(o))].select = True
                    else: 
                        verts[vI].select = False

                possibleExtendBevelWeightEdges = [e for e in edges if verts[e.vertices[0]].select == True and verts[e.vertices[1]].select == True and e.bevel_weight == 0.0]


                # #Deselect everything again
                faces.foreach_set("select", (False,) * len(faces))
                edges.foreach_set("select", (False,) * len(edges))
                verts.foreach_set("select", (False,) * len(verts))

                if len(possibleExtendBevelWeightEdges) == 0:
                    continue

                for e in possibleExtendBevelWeightEdges:
                    verts[e.vertices[0]].select = True
                    verts[e.vertices[1]].select = True
                extendBevelWeightVerticesIndices = [v.index for v in verts if v.select] #Saving all vertices that may need to be used to extend bevel weights

                faces.foreach_set("select", (False,) * len(faces))
                edges.foreach_set("select", (False,) * len(edges))
                verts.foreach_set("select", (False,) * len(verts))

                # Here's where we really extend the edges bevel weights
                lastFoundVertexIndex = -1
                extendRevisions = 0
                for vI in extendBevelWeightVerticesIndices:
                    extendRevisions+=1
                    if vI == lastFoundVertexIndex or verts[vI].bevel_weight == 0.0:
                        continue
                    verts[vI].select = True
                    if verts[(vI + 1)].bevel_weight >= bevelWeights[i]:
                        verts[(vI + 1)].select = True
                        lastFoundVertexIndex = vI + 1
                        for o in range(currentBevelSegments-1):    #Selecting n adjacent vertices by index. n is the amount of bevel segments-1, since that is how many new vertices are created during the bevel
                            verts[(vI+2+(o))].select = True
                    else:
                        verts[(vI - 1)].select = True
                        lastFoundVertexIndex = vI - 1
                        for o in range(currentBevelSegments-1):
                            verts[(vI+1+(o))].select = True                           
                    for e in possibleExtendBevelWeightEdges:
                        if verts[e.vertices[0]].select == True and verts[e.vertices[1]].select == True:
                            e.bevel_weight = bevelWeights[i+1]
                    for vI_deselect in range(currentBevelSegments+3):
                        verts[vI-2+vI_deselect].select = False
                

        # print("The whole script took: ", time.time()-then, " seconds")
        # print("Extend revisions: ", extendRevisions)

        return {'FINISHED'}

def mesh_object_menu_draw(self, context):
    self.layout.operator('object.final_bevel')

class VIEW3D_PT_final_bevel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Final Bevel"
    bl_label = "Final Bevel"    

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'OBJECT')    

    def draw(self,context):

        layout = self.layout
        scene = context.scene
        fb = context.active_object.finalBevel

        layout.prop(fb, "bevelWidth")
        layout.prop(fb, "bevelProfile")
        layout.prop(fb, "primaryBevelSegments")
        layout.prop(fb, "clampOverlap")

        if fb.finalBevelActive:
            self.layout.operator('object.toggle_final_bevel',text="Stop Final Bevel",depress=True)
        else:
            self.layout.operator('object.toggle_final_bevel',text="Run Final Bevel",depress=False)

def register():
    bpy.utils.register_class(FB_Addon_Props)
    bpy.utils.register_class(VIEW3D_PT_final_bevel)
    bpy.utils.register_class(FinalBevel)
    bpy.utils.register_class(StopFinalBevel)
    bpy.utils.register_class(ToggleFinalBevel)
    bpy.types.Object.finalBevel = PointerProperty(type=FB_Addon_Props)
    # bpy.types.VIEW3D_MT_object.append(mesh_object_menu_draw)


def unregister():
    bpy.utils.unregister_class(FB_Addon_Props)
    bpy.utils.unregister_class(VIEW3D_PT_final_bevel)
    bpy.utils.unregister_class(FinalBevel)    
    bpy.utils.unregister_class(StopFinalBevel)    
    bpy.utils.unregister_class(ToggleFinalBevel)    
    del bpy.types.Object.finalBevel
    # bpy.types.VIEW3D_MT_object.remove(mesh_object_menu_draw)
