# Aurora Borealis Generator
A procedural aurora borealis generator for Autodesk Maya

## Description
Artists draw a NURBS curve to define the shape and position of the aurora. The tool generates a ribbon mesh along the curve, applies a fully procedural shader network with animated vertical streaks, and outputs a render-ready result with no external textures or plugins required. All parameters — height, color, brightness, and animation speed — are controllable through a custom UI panel.

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
6. Press Save Aurora to save mesh separately. A new curve will be available for generation.
7. Press Delete to delete all existing Auora
8. Press Export to export as USD in file location of choice.

## Demo
![render_aurora](https://github.com/user-attachments/assets/5c188a47-c12e-4d58-89ea-d10f9ccb24f2)

[https://youtu.be/G5a8kWYNRfc](https://youtu.be/X2EnPphHqcw)



