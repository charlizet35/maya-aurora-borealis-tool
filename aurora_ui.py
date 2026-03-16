import maya.cmds as cmds
import maya.OpenMayaUI as omui

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance

import importlib
import aurora_core
importlib.reload(aurora_core)  

def _maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)

class AuroraWindow(QtWidgets.QDialog):
    WINDOW_TITLE = "Aurora Builder"

    def __init__(self, parent=_maya_main_window()):
        super(AuroraWindow, self).__init__(parent)

        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(340)
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.Tool
        )

        self._curve_shape = None   
        self._last_mesh = None
        self._build_ui()
        self._connect_signals()


    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        title = QtWidgets.QLabel("Aurora Borealis")
        title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #7fffd4;"
        )
        root.addWidget(title)

        root.addWidget(_divider())

        # curve picker
        root.addWidget(_section_label("Input Curve"))

        pick_row = QtWidgets.QHBoxLayout()

        self.curve_field = QtWidgets.QLineEdit()
        self.curve_field.setPlaceholderText(
            "Type name or load from selection…"
        )
        self.curve_field.setAcceptDrops(True)
        self.curve_field.installEventFilter(self)  
        pick_row.addWidget(self.curve_field)

        self.load_btn = QtWidgets.QPushButton("Load")
        self.load_btn.setFixedWidth(72)
        self.load_btn.setToolTip(
            "Click a NURBS curve in the viewport, then press this"
        )
        pick_row.addWidget(self.load_btn)

        root.addLayout(pick_row)

        # status indicator
        self.status_label = QtWidgets.QLabel("No curve loaded")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        root.addWidget(self.status_label)

        root.addWidget(_divider())

        #ribbon parameters
        root.addWidget(_section_label("Ribbon Settings"))

        form = QtWidgets.QFormLayout()
        form.setSpacing(6)

        self.height_spin = _float_spin(1.0, 50.0, 5.0, step=0.5)
        self.samples_spin = _int_spin(10, 200, 80)

        form.addRow("Height", self.height_spin)
        form.addRow("Curve samples", self.samples_spin)
        root.addLayout(form)

        root.addWidget(_divider())

        # shader controls
        root.addWidget(_section_label("Brightness"))

        shader_form = QtWidgets.QFormLayout()
        shader_form.setSpacing(6)

        # R slider — starts at 6, range 0-20
        self.incan_r = _labeled_slider(0, 200, 60)   #stored as int but divide by 10
        self.incan_g = _labeled_slider(0, 200, 60)
        self.incan_b = _labeled_slider(0, 200, 80)

        shader_form.addRow("R", self.incan_r)
        shader_form.addRow("G", self.incan_g)
        shader_form.addRow("B", self.incan_b)
        root.addLayout(shader_form)

        # color swatch — shows current RGB as a preview
        self.color_swatch = QtWidgets.QLabel()
        self.color_swatch.setFixedHeight(16)
        self.color_swatch.setStyleSheet("border-radius: 3px;")
        root.addWidget(self.color_swatch)
        self._update_swatch()

        root.addWidget(_divider())

        #animation controls
        root.addWidget(_section_label("Animation"))

        anim_form = QtWidgets.QFormLayout()
        anim_form.setSpacing(6)

        #speed: 0-50 mapped to 0.000-0.050, default 5 = 0.005
        self.speed_slider = _labeled_slider(0, 50, 5)
        self.speed_label  = QtWidgets.QLabel("0.005")
        self.speed_label.setStyleSheet("color: #888; font-size: 11px;")

        speed_row = QtWidgets.QHBoxLayout()
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_label)
        anim_form.addRow("Speed", speed_row)
        root.addLayout(anim_form)

        root.addWidget(_divider())

        #action buttons
        self.build_btn = QtWidgets.QPushButton("Build Ribbon")
        self.build_btn.setFixedHeight(34)

        self.build_btn.setEnabled(False)
        root.addWidget(self.build_btn)

        self.update_btn = QtWidgets.QPushButton("Update")
        self.update_btn.setFixedHeight(28)
        self.update_btn.setEnabled(False)
        self.update_btn.setToolTip(
            "Rebuild mesh in-place — faster than a full rebuild"
        )
        root.addWidget(self.update_btn)

        self.save_btn = QtWidgets.QPushButton("Save Aurora")
        self.save_btn.setFixedHeight(28)
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Rename WIP to aurora_mesh_001 etc, locks it")
        root.addWidget(self.save_btn)

        self.delete_btn = QtWidgets.QPushButton("Delete Aurora")
        self.delete_btn.setFixedHeight(24)
        self.delete_btn.setStyleSheet("color: #c06060;")
        root.addWidget(self.delete_btn)

        root.addStretch()

    def _connect_signals(self):
        self.load_btn.clicked.connect(self._on_load_selection)
        self.curve_field.editingFinished.connect(self._on_field_edited)
        self.build_btn.clicked.connect(self._on_build)
        self.update_btn.clicked.connect(self._on_update)
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        self.incan_r.valueChanged.connect(self._on_incan_changed)
        self.incan_g.valueChanged.connect(self._on_incan_changed)
        self.incan_b.valueChanged.connect(self._on_incan_changed)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)

    def eventFilter(self, obj, event):
        if obj is self.curve_field:
            if event.type() == QtCore.QEvent.DragEnter:
                if event.mimeData().hasText():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QtCore.QEvent.Drop:
                text = event.mimeData().text().strip()
                text = text.replace("file://", "").strip()
                self.curve_field.setText(text)
                self._validate_curve(text)
                return True
        return super(AuroraWindow, self).eventFilter(obj, event)  #lets window do normal thing for other events, important!!!!


    #is dropped item a curve
    def _validate_curve(self, name):
        name = name.strip()
        shape = aurora_core.resolve_curve(name)
        if shape:
            self._curve_shape = shape
            display = name if name == shape else f"{name} → {shape}"
            self.status_label.setText("✓  {}".format(display))
            self.status_label.setStyleSheet(
                "color: #7fffd4; font-size: 11px;"
            )
            self.build_btn.setEnabled(True)
            self.update_btn.setEnabled(cmds.objExists(aurora_core.MESH_NAME))
        else:
            self._curve_shape = None
            if name:
                self.status_label.setText(
                    "X  \"{}\" is not a NURBS curve".format(name)
                )
                self.status_label.setStyleSheet(
                    "color: #c06060; font-size: 11px;"
                )
            else:
                self.status_label.setText("No curve loaded")
                self.status_label.setStyleSheet(
                    "color: #888; font-size: 11px;"
                )
            self.build_btn.setEnabled(False)
            self.update_btn.setEnabled(False)


    def _on_load_selection(self):
        sel = cmds.ls(selection=True) or []
        if not sel:
            self._show_warning("Nothing selected. Select a NURBS curve first.")
            return
        name = sel[0]
        self.curve_field.setText(name)
        self._validate_curve(name)

    def _on_field_edited(self):
        self._validate_curve(self.curve_field.text())

    def _on_build(self):
        if not self._curve_shape:
            return
        try:
            mesh = aurora_core.build_ribbon(
                self._curve_shape,
                height=self.height_spin.value(),
                sample_count=self.samples_spin.value(),
            )
            self._last_mesh = mesh
            self._set_status_ok("Built  →  {}".format(mesh))
            self.update_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            #reapply current slider values to the new built shader
            self._on_incan_changed()
            self._on_speed_changed(self.speed_slider.value())
        except Exception as e:
            self._show_warning("Build failed:\n{}".format(str(e)))

    def _on_update(self):
        if not self._curve_shape:
            return
        try:
            aurora_core.update_ribbon(
                self._curve_shape,
                height=self.height_spin.value(),
                sample_count=self.samples_spin.value(),
            )
            self._set_status_ok("Updated")
        except Exception as e:
            self._show_warning("Update failed:\n{}".format(str(e)))

    def _on_save(self):
        new_name = aurora_core.save_ribbon()
        if new_name:
            self._last_mesh = None
            self.update_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self._set_status_ok("Saved  →  {}  (locked)".format(new_name))

    def _on_delete(self):
        for node in cmds.ls("aurora_mesh_*", type="transform") or []:
            if cmds.objExists(node):
                cmds.delete(node)
        for node in [aurora_core.SHADER_NAME, aurora_core.SG_NAME]:
            if cmds.objExists(node):
                cmds.delete(node)
        self._last_mesh = None
        self.update_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.status_label.setText("All auroras deleted")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")

    def _on_speed_changed(self, int_val):
        speed = int_val / 1000.0   
        self.speed_label.setText("{:.3f}".format(speed))
        aurora_core.set_noise_speed(speed)

    def _on_incan_changed(self, _=None):
        r = self.incan_r.value() / 10.0
        g = self.incan_g.value() / 10.0
        b = self.incan_b.value() / 10.0
        aurora_core.set_incan_rgb(r, g, b)
        self._update_swatch()

    def _update_swatch(self):
        r = min(255, int(self.incan_r.value() / 200.0 * 255))
        g = min(255, int(self.incan_g.value() / 200.0 * 255))
        b = min(255, int(self.incan_b.value() / 200.0 * 255))
        self.color_swatch.setStyleSheet(
            "background-color: rgb({},{},{}); border-radius: 3px;".format(r, g, b)
        )

    def _set_status_ok(self, msg):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(
            "color: #7fffd4; font-size: 11px;"
        )

    def _show_warning(self, msg):
        QtWidgets.QMessageBox.warning(self, "Aurora", msg)

def _labeled_slider(min_val, max_val, default):
    s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    s.setRange(min_val, max_val)
    s.setValue(default)
    return s


def _section_label(text):
    lbl = QtWidgets.QLabel(text)
    lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
    return lbl

def _divider():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setStyleSheet("color: #444;")
    return line

def _float_spin(min_val, max_val, default, step=1.0):
    sp = QtWidgets.QDoubleSpinBox()
    sp.setRange(min_val, max_val)
    sp.setValue(default)
    sp.setSingleStep(step)
    sp.setDecimals(2)
    return sp

def _int_spin(min_val, max_val, default):
    sp = QtWidgets.QSpinBox()
    sp.setRange(min_val, max_val)
    sp.setValue(default)
    return sp


_window_instance = None


def show():
    global _window_instance
    try:
        _window_instance.close()
        _window_instance.deleteLater()
    except Exception:
        pass
    _window_instance = AuroraWindow()
    _window_instance.show()