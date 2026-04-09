import maya.cmds as cmds
import maya.api.OpenMaya as om

MESH_NAME   = "aurora_mesh_WIP"
MESH_PREFIX = "aurora_mesh"
SHADER_NAME = "aurora_shader"
SG_NAME     = "aurora_SG"


def _next_mesh_name():
    i = 1
    while True:
        candidate = "{0}_{1:03d}".format(MESH_PREFIX, i)
        if not cmds.objExists(candidate):
            return candidate
        i += 1


def save_ribbon():
    if not cmds.objExists(MESH_NAME):
        return None
    new_name = _next_mesh_name()
    cmds.rename(MESH_NAME, new_name)
    return new_name


def resolve_curve(name):
    if not name or not cmds.objExists(name):
        return None
    if cmds.nodeType(name) == "nurbsCurve":
        return name
    shapes = cmds.listRelatives(name, shapes=True, type="nurbsCurve") or []
    if shapes:
        return shapes[0]
    return None


def sample_curve(curve_shape, sample_count=80):
    points = []
    for i in range(sample_count):
        t = i / float(sample_count - 1)
        pos = cmds.pointOnCurve(
            curve_shape, pr=t, turnOnPercentage=True, position=True
        )
        points.append((pos[0], pos[1], pos[2]))
    return points


def build_ribbon(curve_shape, height=5.0, sample_count=80):
    if cmds.objExists(MESH_NAME):
        cmds.delete(MESH_NAME)

    base_pts = sample_curve(curve_shape, sample_count)
    v_divs = 20
    verts, face_counts, face_connects = _build_mesh_data(base_pts, height, v_divs)
    mesh_transform = _create_mesh(
        verts, face_counts, face_connects, cols=sample_count, rows=v_divs + 1)
    _apply_basic_shader(mesh_transform)
    setup_transparency_ramps()
    setup_noise_animation()
    return mesh_transform


def update_ribbon(curve_shape, height=5.0, sample_count=80):
    if not cmds.objExists(MESH_NAME):
        return build_ribbon(curve_shape, height, sample_count)

    expected_verts = 21 * sample_count 
    sel = om.MSelectionList()
    sel.add(MESH_NAME)
    dag = sel.getDagPath(0)
    fn = om.MFnMesh(dag)

    if fn.numVertices != expected_verts:
        return build_ribbon(curve_shape, height, sample_count)

    base_pts = sample_curve(curve_shape, sample_count)
    verts, _, _ = _build_mesh_data(base_pts, height, v_divs=20)

    pts = om.MPointArray()
    for v in verts:
        pts.append(om.MPoint(v[0], v[1], v[2]))

    fn.setPoints(pts, om.MSpace.kWorld)
    fn.updateSurface()
    return MESH_NAME


def _build_mesh_data(base_pts, height, v_divs=20):
    cols = len(base_pts)
    verts = []
    for row in range(v_divs + 1):
        t = row / float(v_divs)
        y_offset = t * height
        for bx, by, bz in base_pts:
            verts.append((bx, by + y_offset, bz))

    face_counts = []
    face_connects = []
    for row in range(v_divs):
        for col in range(cols - 1):
            v0 = row * cols + col
            v1 = row * cols + col + 1
            v2 = (row + 1) * cols + col + 1
            v3 = (row + 1) * cols + col
            face_counts.append(4)
            face_connects.extend([v0, v1, v2, v3])

    return verts, face_counts, face_connects


def _create_mesh(verts, face_counts, face_connects, cols, rows):
    pts = om.MPointArray()
    for v in verts:
        pts.append(om.MPoint(v[0], v[1], v[2]))

    fn = om.MFnMesh()
    mesh_obj = fn.create(pts, face_counts, face_connects)

    u_array = om.MFloatArray()
    v_array = om.MFloatArray()
    for row in range(rows):
        v_val = row / float(rows - 1)   
        for col in range(cols):
            u_array.append(col / float(cols - 1))
            v_array.append(v_val)

    fn.setUVs(u_array, v_array)

    uv_counts = om.MIntArray()
    uv_ids    = om.MIntArray()
    for row in range(rows - 1):
        for col in range(cols - 1):
            uv_counts.append(4)
            uv_ids.append(row * cols + col)
            uv_ids.append(row * cols + col + 1)
            uv_ids.append((row + 1) * cols + col + 1)
            uv_ids.append((row + 1) * cols + col)

    fn.assignUVs(uv_counts, uv_ids)

    dag = om.MFnDagNode(mesh_obj)
    raw_name = dag.fullPathName().split("|")[1]
    transform = cmds.rename(raw_name, MESH_NAME)
    cmds.sets(transform, e=True, forceElement="initialShadingGroup")
    return transform


def _apply_basic_shader(mesh_transform):
    if not cmds.objExists(SHADER_NAME):
        shader = cmds.shadingNode(
            "aiStandardSurface", asShader=True, name=SHADER_NAME
        )
        sg = cmds.sets(
            renderable=True, noSurfaceShader=True,
            empty=True, name=SG_NAME
        )
        cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader")

        cmds.setAttr(shader + ".base",             0.776)
        cmds.setAttr(shader + ".baseColor",        1.0, 1.0, 1.0, type="double3")

        cmds.setAttr(shader + ".sheenColor",       0.203, 0.203, 0.204, type="double3")

        cmds.setAttr(shader + ".specular",         1.0)
        cmds.setAttr(shader + ".specularRoughness", 0.161)
        cmds.setAttr(shader + ".specularIOR",      1.5)

        cmds.setAttr(shader + ".emission",         14.685)

        cmds.setAttr(shader + ".thinFilmThickness", 83.916)
        cmds.setAttr(shader + ".thinFilmIOR",       2.014)

        cmds.setAttr(shader + ".thinWalled",        1)

    if cmds.objExists(SG_NAME):
        cmds.sets(mesh_transform, e=True, forceElement=SG_NAME)


def _make_ramp(name, place_name, keys, ramp_type=0):
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=place_name)
    ramp  = cmds.shadingNode("ramp", asTexture=True, name=name)
    cmds.connectAttr(place + ".outUV",           ramp + ".uv")
    cmds.connectAttr(place + ".outUvFilterSize", ramp + ".uvFilterSize")
    cmds.setAttr(ramp + ".type", ramp_type)
    for i, (pos, col) in enumerate(keys):
        cmds.setAttr("{}.colorEntryList[{}].position".format(ramp, i), pos)
        cmds.setAttr("{}.colorEntryList[{}].color".format(ramp, i),
                     col[0], col[1], col[2], type="double3")
    return ramp


def _make_mult(name, operation, input2):
    node = cmds.shadingNode("multiplyDivide", asUtility=True, name=name)
    cmds.setAttr(node + ".operation", operation)
    cmds.setAttr(node + ".input2", input2[0], input2[1], input2[2], type="double3")
    return node


def _make_noise(name, place_name, place_attrs, noise_settings):
    """
    place_attrs  – dict of attrs to set on the place2dTexture node
    noise_settings – dict of attrs to set on the noise node
    """
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=place_name)
    for attr, val in place_attrs.items():
        if isinstance(val, (list, tuple)):
            cmds.setAttr("{}.{}".format(place, attr), *val)
        else:
            cmds.setAttr("{}.{}".format(place, attr), val)

    noise = cmds.shadingNode("noise", asTexture=True, name=name)
    cmds.connectAttr(place + ".outUV",           noise + ".uv")
    cmds.connectAttr(place + ".outUvFilterSize", noise + ".uvFilterSize")
    for attr, val in noise_settings.items():
        if isinstance(val, (list, tuple)):
            cmds.setAttr("{}.{}".format(noise, attr), *val)
        else:
            cmds.setAttr("{}.{}".format(noise, attr), val)
    return noise

def setup_transparency_ramps():
    nodes = [
        #emission branch
        "aurora_place2d_incan1_5", "ramp1",
        "multiplyDivide1",
        "aurora_place2d_incan1",   "aurora_ramp_incan1",
        "aurora_mult_incan1",
        #opacity branch
        "aurora_place2d_transp1",  "aurora_ramp_transp1",
        "aurora_mult_transp1",
        "aurora_mult_combine1",
        #noise1 branch
        "place2dTexture1",         "noise1",
        "aurora_mult_noise1",
        #noise3 branch
        "place2dTexture3",         "noise3",
    ]

    for n in nodes:
        if cmds.objExists(n):
            cmds.delete(n)

    ramp1_keys = [
        (0.0000, (1.0000, 1.0000, 1.0000)),
        (0.5284, (0.1895, 0.1895, 0.1895)),
        (0.1433, (0.3137, 0.3137, 0.3137)),
        (0.4090, (0.2288, 0.2288, 0.2288)),
        (0.7522, (0.0784, 0.0784, 0.0784)),
    ]
    ramp1 = _make_ramp("ramp1", "aurora_place2d_incan1_5", ramp1_keys)

    mult_d1 = _make_mult("multiplyDivide1", 1, (2.0, 2.0, 2.0))
    cmds.connectAttr(ramp1 + ".outColor", mult_d1 + ".input1")

    #aurora_ramp_incan1 
    incan_keys = [
        (0.0000, (0.1564, 1.0000, 0.4852)),
        (0.9045, (0.7248, 0.7093, 0.8824)),
        (0.6328, (0.6578, 0.4346, 0.8577)),
    ]
    ramp_i1 = _make_ramp("aurora_ramp_incan1", "aurora_place2d_incan1", incan_keys)
    cmds.setAttr("aurora_ramp_incan1.interpolation", 4) 

    #aurora_mult_incan1
    mult_i1 = cmds.shadingNode("multiplyDivide", asUtility=True, name="aurora_mult_incan1")
    cmds.setAttr(mult_i1 + ".operation", 1)
    cmds.connectAttr(ramp_i1  + ".outColor", mult_i1 + ".input1")
    cmds.connectAttr(mult_d1  + ".output",   mult_i1 + ".input2")

    #aurora_mult_incan1 -> emission color
    cmds.connectAttr(mult_i1 + ".output", SHADER_NAME + ".emissionColor", force=True)

    #aurora_ramp_transp1
    transp_keys = [
        (1.0000, (0.0000, 0.0000, 0.0000)),
        (0.1224, (0.0131, 0.0131, 0.0131)),
        (0.0746, (0.0000, 0.0000, 0.0000)),
        (0.1493, (0.0131, 0.0131, 0.0131)),
    ]
    ramp_t1 = _make_ramp("aurora_ramp_transp1", "aurora_place2d_transp1", transp_keys)
    cmds.setAttr("aurora_ramp_transp1.noiseFreq", 0.277)

    noise1_place_attrs = {
        "repeatU": 7.0,
        "repeatV": 0.002,
        "wrapU":   1,
        "wrapV":   1,
    }
    noise1_settings = {
        "threshold":     0.0,
        "amplitude":     1.0,
        "ratio":         0.361,
        "frequencyRatio":2.742,
        "depthMax":      3,
        "implode":       0.432,
        "implodeCenter": (0.0, 1.0),
        "noiseType":     0,          
        "frequency":     8.0,
    }
    noise1 = _make_noise("noise1", "place2dTexture1", noise1_place_attrs, noise1_settings)

    noise3_place_attrs = {
        "rotateFrame": 180.0,
        "wrapU":       1,
        "wrapV":       1,
        "repeatU":     1.5,
        "repeatV":     0.05,
    }
    noise3_settings = {
        "threshold":     0.378,
        "amplitude":     1.0,
        "ratio":         0.639,
        "frequencyRatio":2.568,
        "depthMax":      3,
        "implode":       0.0,
        "implodeCenter": (0.5, 0.5),
        "noiseType":     0,         
        "frequency":     3.226,
    }
    noise3 = _make_noise("noise3", "place2dTexture3", noise3_place_attrs, noise3_settings)

    #aurora_mult_transp1
    mult_t1 = cmds.shadingNode("multiplyDivide", asUtility=True, name="aurora_mult_transp1")
    cmds.setAttr(mult_t1 + ".operation", 3)  
    cmds.connectAttr(ramp_t1 + ".outColor", mult_t1 + ".input1")
    cmds.connectAttr(noise3  + ".outColor", mult_t1 + ".input2")

    #aurora_mult_noise1
    mult_n1 = _make_mult("aurora_mult_noise1", 1, (0.5, 0.5, 0.5))
    cmds.connectAttr(noise1 + ".outColor", mult_n1 + ".input1")

    #aurora_mult_combine1
    mult_c1 = cmds.shadingNode("multiplyDivide", asUtility=True, name="aurora_mult_combine1")
    cmds.setAttr(mult_c1 + ".operation", 1)
    cmds.connectAttr(mult_t1 + ".output", mult_c1 + ".input1")
    cmds.connectAttr(mult_n1 + ".output", mult_c1 + ".input2")

    cmds.connectAttr(mult_c1 + ".output", SHADER_NAME + ".opacity", force=True)

def export_usd(mesh_name, folder):
    import os
    if not cmds.objExists(mesh_name):
        raise RuntimeError("Mesh '{}' does not exist.".format(mesh_name))
 
    filepath = os.path.join(folder, mesh_name + ".usd").replace("\\", "/")
 
    cmds.select(mesh_name, replace=True)
    cmds.mayaUSDExport(
        file=filepath,
        selection=True,
        exportUVs=True,
        shadingMode="useRegistry",
        convertMaterialsTo="UsdPreviewSurface",
        exportDisplayColor=False,
        mergeTransformAndShape=True,
        stripNamespaces=True,
    )
    cmds.select(clear=True)
    return filepath


def set_incan_rgb(r, g, b):
    if cmds.objExists("multiplyDivide1"):
        cmds.setAttr("multiplyDivide1.input2", r, g, b, type="double3")


def setup_noise_animation(speed=0.005):
    cmds.playbackOptions(maxTime=100000, animationEndTime=100000)

    expr_name = "aurora_noise_anim"
    expr_str = (
        "noise1.time = frame * {0};\n"
        "noise3.time = frame * {0};"
    ).format(speed)

    if cmds.objExists(expr_name):
        cmds.expression(expr_name, e=True, s=expr_str)
    else:
        cmds.expression(s=expr_str, n=expr_name, ae=True, uc="all")


def set_noise_speed(speed):
    if cmds.objExists("noise1"):
        setup_noise_animation(speed)