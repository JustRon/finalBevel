import bpy, time
from bpy.props import FloatProperty, IntProperty,BoolProperty

bl_info = {
    "name": "Final Bevel",
    "description": "Bakes accurate bevels into an object based on their bevel weights.",
    "author": "Ron Frölich",
    "version": (0, 2),
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
    bevelWidth: FloatProperty(
        name = "Bevel Width",
        description = "How wide a bevel with a weight of 1 should be (cm)",
        default = 20,
        min = 0.001,
        max = 1000
    )

    bevelProfile: FloatProperty(
        name = "Bevel Profile",
        description = "The profile with which the edges are beveled",
        default = 0.5,
        min = 0.0,
        max = 1.0
    )

    primaryBevelSegments: IntProperty(
        name = "Primary Bevel Segments",
        description = "How many segments to use for the edges with the highest bevel weight",
        default = 4,
        min = 2,
        max = 100
    )

    # secondaryBevelSegments: IntProperty(
    #     name = "Secondary Bevel Segments",
    #     description = "How many segments to use for the edges with the second highest bevel weight",
    #     default = 3,
    #     min = 2,
    #     max = 100
    # )

    # tertiaryBevelSegments: IntProperty(
    #     name = "Tertiary Bevel Segments",
    #     description = "How many segments to use for the remaining edges",
    #     default = 2,
    #     min = 2,
    #     max = 100
    # )

    clampOverlap: BoolProperty(
        name = "Clamp Overlap",
        description = "Whether to use clamp overlap on any bevel iteration",
        default = False
    )

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'OBJECT')

    def execute(self, context):
        # then = time.time() #Time before the operations start
        # Making sure we're in edge mode before we start

        # Setup stuff
        so = bpy.context.active_object
        faces = so.data.polygons
        edges = so.data.edges
        verts = so.data.vertices
        so.data.use_customdata_edge_bevel = True
        so.data.use_customdata_vertex_bevel = True

        currentBevelSegments = self.primaryBevelSegments
        # bevelSegmentsList = [self.primaryBevelSegments, self.secondaryBevelSegments, self.tertiaryBevelSegments]
        
        #Saving all our different bevel weights into a list
        bevelWeights = []
        for e in edges:
            if e.bevel_weight != 0.0:
                if bevelWeights.count(e.bevel_weight) == 0:
                    bevelWeights.append(e.bevel_weight)

        #Everything needs to be deselected
        faces.foreach_set("select", (False,) * len(faces))
        edges.foreach_set("select", (False,) * len(edges))
        verts.foreach_set("select", (False,) * len(verts))

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.reveal(False)
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.object.mode_set(mode='OBJECT')

        nonManifoldEdges = [e for e in edges if e.select == True]
        for edge in nonManifoldEdges:
            edge.bevel_weight = 0.0  

        faces.foreach_set("select", (False,) * len(faces))
        edges.foreach_set("select", (False,) * len(edges))
        verts.foreach_set("select", (False,) * len(verts))



        #Let's make sure our bevel weights are sorted largest to smallest
        bevelWeights.sort(reverse=True)
        
        #Iterating through the mesh based on the amount of bevel weights we have
        for i in range(len(bevelWeights)):

            # if i == 1:
            #     currentBevelSegments = self.secondaryBevelSegments
            # elif i > 1:
            #     currentBevelSegments = self.tertiaryBevelSegments

            #Let's select all edges with the current bevel weight assigned and bevel them
            currentBevelWeightEdges = [e for e in edges if e.bevel_weight == bevelWeights[i]]
            for edge in currentBevelWeightEdges:
                edge.select = True
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.bevel(offset = (self.bevelWidth * .01) * bevelWeights[i], segments = currentBevelSegments, profile = self.bevelProfile,clamp_overlap=self.clampOverlap, miter_outer='ARC')
            bpy.ops.object.mode_set(mode='OBJECT')

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
                        for o in range(self.primaryBevelSegments-1):
                            verts[(vI+1+(o))].select = True
                    elif verts[(vI + 1)] and verts[(vI + 1)].bevel_weight >= bevelWeights[i]: 
                        verts[(vI + 1)].select = True
                        for o in range(self.primaryBevelSegments-1):
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

def register():
    bpy.utils.register_class(FinalBevel)
    bpy.types.VIEW3D_MT_object.append(mesh_object_menu_draw)


def unregister():
    bpy.utils.unregister_class(FinalBevel)
    bpy.types.VIEW3D_MT_object.remove(mesh_object_menu_draw)
