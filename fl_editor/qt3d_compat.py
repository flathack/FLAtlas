"""Qt3D Kompatibilitäts-Schicht.

Importiert alle benötigten Qt3D-Klassen über ``getattr``-basierte
Namensraum-Auflösung, da PySide6-Versionen unterschiedliche Modul-Layouts
verwenden.  Stellt ``QT3D_AVAILABLE`` als zentrale Prüfvariable bereit.
"""

from __future__ import annotations

from PySide6.QtGui import QVector3D, QQuaternion  # noqa: F401 – Re-Export

# -- Versuche Qt3D zu laden ------------------------------------------------
try:
    import PySide6.Qt3DCore as Qt3DCore
    import PySide6.Qt3DRender as Qt3DRender
    import PySide6.Qt3DExtras as Qt3DExtras

    _qt3d_core_ns = getattr(Qt3DCore, "Qt3DCore", Qt3DCore)
    _qt3d_render_ns = getattr(Qt3DRender, "Qt3DRender", Qt3DRender)
    _qt3d_extras_ns = getattr(Qt3DExtras, "Qt3DExtras", Qt3DExtras)

    QEntity3D = getattr(_qt3d_core_ns, "QEntity", None)
    QMesh3D = getattr(_qt3d_render_ns, "QMesh", None)
    QDirectionalLight3D = getattr(_qt3d_render_ns, "QDirectionalLight", None)
    Qt3DWindow3D = getattr(_qt3d_extras_ns, "Qt3DWindow", None)
    QOrbitCameraController3D = getattr(_qt3d_extras_ns, "QOrbitCameraController", None)
    QPhongMaterial3D = getattr(_qt3d_extras_ns, "QPhongMaterial", None)
    QSphereMesh3D = getattr(_qt3d_extras_ns, "QSphereMesh", None)
    QCuboidMesh3D = getattr(_qt3d_extras_ns, "QCuboidMesh", None)
    QConeMesh3D = getattr(_qt3d_extras_ns, "QConeMesh", None)
    QCylinderMesh3D = getattr(_qt3d_extras_ns, "QCylinderMesh", None)
    QExtrudedTextMesh3D = getattr(_qt3d_extras_ns, "QExtrudedTextMesh", None)
    QPhongAlphaMaterial3D = getattr(_qt3d_extras_ns, "QPhongAlphaMaterial", None)
    QTransform3D = getattr(_qt3d_core_ns, "QTransform", None)
    QObjectPicker3D = getattr(_qt3d_render_ns, "QObjectPicker", None)

    QT3D_AVAILABLE: bool = all([
        QEntity3D,
        QMesh3D,
        QDirectionalLight3D,
        Qt3DWindow3D,
        QOrbitCameraController3D,
        QPhongMaterial3D,
        QSphereMesh3D,
        QCuboidMesh3D,
        QConeMesh3D,
        QCylinderMesh3D,
        QExtrudedTextMesh3D,
        QPhongAlphaMaterial3D,
        QTransform3D,
        QObjectPicker3D,
    ])

except Exception:
    QT3D_AVAILABLE = False
    Qt3DCore = None       # type: ignore[assignment]
    Qt3DRender = None     # type: ignore[assignment]
    Qt3DExtras = None     # type: ignore[assignment]
    QEntity3D = None
    QMesh3D = None
    QDirectionalLight3D = None
    Qt3DWindow3D = None
    QOrbitCameraController3D = None
    QPhongMaterial3D = None
    QSphereMesh3D = None
    QCuboidMesh3D = None
    QConeMesh3D = None
    QCylinderMesh3D = None
    QExtrudedTextMesh3D = None
    QPhongAlphaMaterial3D = None
    QTransform3D = None
    QObjectPicker3D = None
