FinalBevel is an operator addon that tries to bake accurate bevels based on the meshes bevel weights.
The bevel modifier handles intersecting edges using different bevel weights pretty poorly. 
FinalBevel bevels edges with varying bevel weights sequentially to generate a result that ought to be in line with the users expectations.

This initial submit is pretty bare-bones. It's a simple operator with few settings that's appallingly slow compared to the built-in bevel modifier.
However, it generates a cleaner result and allows the user to use bevel weights without worrying about odd intersections.

Ideally, this kind of behaviour should be part of the built-in modifier, if at all feasible.

Here's a bunch of things I'd like to add to future versions of this:

A proper UI
More settings to give users more control
An option to read values from an existing bevel modifier and replace it with "baked" bevels
An option to save and retrieve the original mesh after the bevels have been made

A bunch of comparison shots between the bevel modifier (left) and the result from FinalBevel(right)
