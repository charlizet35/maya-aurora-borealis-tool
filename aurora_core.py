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
    verts, face_counts, face_connects = _build_mesh_data(base_pts, height)
    mesh_transform = _create_mesh(verts, face_counts, face_connects,
                                  cols=sample_count)
    _apply_basic_shader(mesh_transform)
    setup_transparency_ramps()
    setup_noise_animation()
    return mesh_transform


def update_ribbon(curve_shape, height=5.0, sample_count=80):
    if not cmds.objExists(MESH_NAME):
        return build_ribbon(curve_shape, height, sample_count)

    expected_verts = 2 * sample_count
    sel = om.MSelectionList()
    sel.add(MESH_NAME)
    dag = sel.getDagPath(0)
    fn = om.MFnMesh(dag)

    if fn.numVertices != expected_verts:
        return build_ribbon(curve_shape, height, sample_count)

    base_pts = sample_curve(curve_shape, sample_count)
    verts, _, _ = _build_mesh_data(base_pts, height)

    pts = om.MPointArray()
    for v in verts:
        pts.append(om.MPoint(v[0], v[1], v[2]))

    fn.setPoints(pts, om.MSpace.kWorld)
    fn.updateSurface()
    return MESH_NAME


def _build_mesh_data(base_pts, height):
    cols = len(base_pts)
    verts = []
    for bx, by, bz in base_pts:
        verts.append((bx, by, bz))
    for bx, by, bz in base_pts:
        verts.append((bx, by + height, bz))

    #math
    face_counts   = []
    face_connects = []
    for col in range(cols - 1):
        v0 = col      #bottom left
        v1 = col + 1   # bottom right
        v2 = cols + col + 1   #top right
        v3 = cols + col    #top left
        face_counts.append(4)
        face_connects.extend([v0, v1, v2, v3])

    return verts, face_counts, face_connects


def _create_mesh(verts, face_counts, face_connects, cols):
    pts = om.MPointArray()
    for v in verts:
        pts.append(om.MPoint(v[0], v[1], v[2]))

    fn = om.MFnMesh()
    mesh_obj = fn.create(pts, face_counts, face_connects)

    u_array = om.MFloatArray()
    v_array = om.MFloatArray()
    for row in range(2):
        v_val = float(row)          # 0.0 = bottom, 1.0 = top
        for col in range(cols):
            u_array.append(col / float(cols - 1))
            v_array.append(v_val)

    fn.setUVs(u_array, v_array)

    uv_counts = om.MIntArray()
    uv_ids    = om.MIntArray()
    for col in range(cols - 1):
        uv_counts.append(4)
        uv_ids.append(col)
        uv_ids.append(col + 1)
        uv_ids.append(cols + col + 1)
        uv_ids.append(cols + col)

    fn.assignUVs(uv_counts, uv_ids)

    dag = om.MFnDagNode(mesh_obj)
    raw_name = dag.fullPathName().split("|")[1]
    transform = cmds.rename(raw_name, MESH_NAME)
    cmds.sets(transform, e=True, forceElement="initialShadingGroup")
    return transform


def _apply_basic_shader(mesh_transform):
    if not cmds.objExists(SHADER_NAME):
        shader = cmds.shadingNode(
            "surfaceShader", asShader=True, name=SHADER_NAME
        )
        sg = cmds.sets(
            renderable=True, noSurfaceShader=True,
            empty=True, name=SG_NAME
        )
        cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader")
        cmds.setAttr(shader + ".outColor", 0.0, 1.0, 0.35, type="double3")
        cmds.setAttr(shader + ".outTransparency", 0.5, 0.5, 0.5, type="double3")

    if cmds.objExists(SG_NAME):
        cmds.sets(mesh_transform, e=True, forceElement=SG_NAME)

#make nodes

def _make_ramp(name, place_name, keys):
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=place_name)
    ramp  = cmds.shadingNode("ramp", asTexture=True, name=name)
    cmds.connectAttr(place + ".outUV",           ramp + ".uv")
    cmds.connectAttr(place + ".outUvFilterSize", ramp + ".uvFilterSize")
    cmds.setAttr(ramp + ".type", 0)
    for i, (pos, col) in enumerate(keys):
        cmds.setAttr("{}.colorEntryList[{}].position".format(ramp, i), pos)
        cmds.setAttr("{}.colorEntryList[{}].color".format(ramp, i),
                     col[0], col[1], col[2], type="double3")
    return ramp


def _make_mult(name, operation, input2):
    #1 mult, 3 for power
    node = cmds.shadingNode("multiplyDivide", asUtility=True, name=name)
    cmds.setAttr(node + ".operation", operation)
    cmds.setAttr(node + ".input2", input2[0], input2[1], input2[2], type="double3")
    return node


def _make_noise(name, place_name, repeat_u, repeat_v, settings):
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=place_name)
    cmds.setAttr(place + ".repeatU", repeat_u)
    cmds.setAttr(place + ".repeatV", repeat_v)
    noise = cmds.shadingNode("noise", asTexture=True, name=name)
    cmds.connectAttr(place + ".outUV",           noise + ".uv")
    cmds.connectAttr(place + ".outUvFilterSize", noise + ".uvFilterSize")
    for attr, val in settings.items():
        cmds.setAttr("{}.{}".format(noise, attr), val)
    return noise


def setup_transparency_ramps():
    nodes = ["aurora_ramp_transp",   "aurora_place2d_transp",
             "aurora_ramp_incan",    "aurora_place2d_incan",
             "aurora_mult_transp",   "aurora_mult_incan",
             "aurora_place2d_noise", "aurora_noise",
             "aurora_mult_noise",    "aurora_mult_combine"]

    for n in nodes:
        if cmds.objExists(n):
            cmds.delete(n)

    incan_keys = [
        (0.0,                (0.43130001425743103, 1.0,                  0.6305000185966492)),
        (0.15479876101016998,(0.0,                 0.5530999898910522,   0.0869000032544136)),
        (0.3684210479259491, (0.5531914830207825,  0.37779349088668823,  0.16580049693584442)),
        (0.5108358860015869, (1.0,                 0.27230000495910645,  0.23520000278949738)),
        (0.6811145544052124, (0.4708999991416931,  0.12919999659061432,  0.31929999589920044)),
        (0.8761609792709351, (0.060100000351667404,0.0,                  0.003700000001117587)),
        (1.0,                (0.0,                 0.0,                  0.0)),
    ]

    transp_keys = [
        (0.0,                (0.8723404407501221, 0.8723404407501221, 0.8723404407501221)),
        (0.02476780116558075,(0.6028369069099426, 0.6028369069099426, 0.6028369069099426)),
        (0.33746129274368286,(0.631205677986145,  0.631205677986145,  0.631205677986145)),
        (0.6687306761741638, (0.8865247964859009, 0.8865247964859009, 0.8865247964859009)),
        (0.801857590675354,  (0.9503546357154846, 0.9503546357154846, 0.9503546357154846)),
        (1.0,                (1.0,                1.0,                1.0)),
    ]

    noise_settings = {
        "threshold":     0.322,
        "amplitude":     0.469,
        "ratio":         0.203,
        "frequencyRatio":6.916,
        "depthMax":      3,
        "frequency":     8.0,
        "noiseType":     0,
    }

    #build nodes
    ramp_i  = _make_ramp("aurora_ramp_incan",   "aurora_place2d_incan",  incan_keys)
    mult_i  = _make_mult("aurora_mult_incan",   1, (6.0, 6.0, 8.0))

    ramp_t  = _make_ramp("aurora_ramp_transp",  "aurora_place2d_transp", transp_keys)
    mult_t  = _make_mult("aurora_mult_transp",  3, (2.0, 0.6, 2.0))

    noise   = _make_noise("aurora_noise", "aurora_place2d_noise", 7.0, 0.002, noise_settings)
    mult_n  = _make_mult("aurora_mult_noise",   1, (3.6, 1.3, 2.3))
    mult_3  = _make_mult("aurora_mult_combine", 1, (1.0, 1.0, 1.0))

    #connect nodes
    cmds.connectAttr(ramp_i + ".outColor",  mult_i + ".input1")
    cmds.connectAttr(mult_i + ".output",    SHADER_NAME + ".outColor", force=True)

    cmds.connectAttr(ramp_t + ".outColor",  mult_t + ".input1")
    cmds.connectAttr(noise  + ".outColor",  mult_n + ".input1")
    cmds.connectAttr(mult_n + ".output",    mult_3 + ".input1")
    cmds.connectAttr(mult_t + ".output",    mult_3 + ".input2")
    cmds.connectAttr(mult_3 + ".output",    SHADER_NAME + ".outTransparency", force=True)


def set_incan_rgb(r, g, b):
    if cmds.objExists("aurora_mult_incan"):
        cmds.setAttr("aurora_mult_incan.input2", r, g, b, type="double3")


def setup_noise_animation(speed=0.005):
    # extend timeline?
    cmds.playbackOptions(maxTime=100000, animationEndTime=100000)

    expr_name = "aurora_noise_anim"
    expr_str   = "aurora_noise.time = frame * {};".format(speed)

    if cmds.objExists(expr_name):
        cmds.expression(expr_name, e=True, s=expr_str)
    else:
        cmds.expression(s=expr_str, o="aurora_noise",
                        n=expr_name, ae=True, uc="all")


def set_noise_speed(speed):
    #rewrite the expression with a new speed value
    if cmds.objExists("aurora_noise"):
        setup_noise_animation(speed)