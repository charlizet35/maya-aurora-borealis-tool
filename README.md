# Aurora Borealis Generator
A procedural aurora borealis generator for Autodesk Maya

## Description
The aurora borealis tool is a procedural system that creates geometry and shaders based on user-defined curves. The curve is first turned into a procedurally generated ribbon, in which a utility-node-based shader is implemented onto the ribbon mesh. Dynamic vertical straks are applied with UV-stretching, and the animation is created through a noise time function.

* **Key Feature 1:** Procedural ribbon generation.
* **Key Feature 2:** Custom utility-node-based shader (no external textures).
* **Key Feature 3:** Dynamic vertical streak system with UV-stretching.

---

## ⚙️ Installation
1. Open install.py and replace the commented code on line 4 to your Aurora Tool folder path.
2. Copy the code in install.py into the python script editor in Autodesk Maya and run it.
4. Restart Maya.
5. Run the following in a new tab in the Maya Python Script Editor:

    ```python
   import aurora_ui
   aurora_ui.show()

---

## Usage
1. **Prepare Input:** Create a NURBS curve in your scene. 
2. **Load Curve** Select a curve in the graph editor and click Load, drag and drop a selected curve, or type in the name of a curve and press Enter. Click Build Ribbon to generate aurora.
3. Adjust samples for more vertices to match the curve and change height to liking. Press Update to see changes
4. Adjust R, G, B incandescence to increase/decrease illumination for each color channel.
5. Press play to see animation. Scroll slider to test animation speeds.
6. Press Save Aurora to save mesh separately. A new curve will be able for generation.
7. Press Delete to delete all existing Auora
