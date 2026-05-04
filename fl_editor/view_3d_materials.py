from __future__ import annotations

from typing import Any


def build_torus_mesh(mesh_cls, *, radius: float, minor: float, rings: int = 52, slices: int = 24):
    if mesh_cls is None:
        return None
    mesh = mesh_cls()
    try:
        mesh.setRadius(float(radius))
        mesh.setMinorRadius(float(minor))
        mesh.setRings(int(rings))
        mesh.setSlices(int(slices))
    except Exception:
        return None
    return mesh


def make_phong_material(material_cls, color, *, ambient_lighter: int = 155):
    mat = material_cls()
    mat.setDiffuse(color)
    try:
        mat.setAmbient(color.lighter(ambient_lighter))
    except Exception:
        pass
    return mat


def make_alpha_material(material_cls, color, *, alpha: float):
    mat = material_cls()
    if hasattr(mat, "setAlpha"):
        mat.setAlpha(float(alpha))
    mat.setDiffuse(color)
    try:
        mat.setAmbient(color)
    except Exception:
        pass
    return mat


def material_always_on_top_refs(material, render_ns) -> list[Any]:
    refs: list[Any] = []
    try:
        render_api = getattr(render_ns, "Qt3DRender", render_ns)
        depth_cls = getattr(render_api, "QDepthTest", None)
        if depth_cls is None:
            return refs
        no_depth_mask_cls = getattr(render_api, "QNoDepthMask", None)
        effect = material.effect() if hasattr(material, "effect") else None
        if effect is None:
            return refs
        techniques = effect.techniques() if hasattr(effect, "techniques") else []
        for tech in list(techniques):
            passes = tech.renderPasses() if hasattr(tech, "renderPasses") else []
            for rpass in list(passes):
                depth_state = depth_cls(rpass)
                depth_fn = getattr(depth_cls, "Always", None)
                if depth_fn is None:
                    enum_cls = getattr(depth_cls, "DepthFunction", None)
                    depth_fn = getattr(enum_cls, "Always", None) if enum_cls is not None else None
                if depth_fn is not None and hasattr(depth_state, "setDepthFunction"):
                    depth_state.setDepthFunction(depth_fn)
                if hasattr(rpass, "addRenderState"):
                    rpass.addRenderState(depth_state)
                    refs.append(depth_state)
                    if no_depth_mask_cls is not None:
                        ndm = no_depth_mask_cls(rpass)
                        rpass.addRenderState(ndm)
                        refs.append(ndm)
    except Exception:
        return refs
    return refs


def material_no_depth_write_refs(material, render_ns) -> list[Any]:
    refs: list[Any] = []
    try:
        render_api = getattr(render_ns, "Qt3DRender", render_ns)
        no_depth_mask_cls = getattr(render_api, "QNoDepthMask", None)
        if no_depth_mask_cls is None:
            return refs
        effect = material.effect() if hasattr(material, "effect") else None
        if effect is None:
            return refs
        techniques = effect.techniques() if hasattr(effect, "techniques") else []
        for tech in list(techniques):
            passes = tech.renderPasses() if hasattr(tech, "renderPasses") else []
            for rpass in list(passes):
                if hasattr(rpass, "addRenderState"):
                    ndm = no_depth_mask_cls(rpass)
                    rpass.addRenderState(ndm)
                    refs.append(ndm)
    except Exception:
        return refs
    return refs


def material_no_alpha_write_refs(material, render_ns) -> list[Any]:
    refs: list[Any] = []
    try:
        render_api = getattr(render_ns, "Qt3DRender", render_ns)
        color_mask_cls = getattr(render_api, "QColorMask", None)
        if color_mask_cls is None:
            return refs
        effect = material.effect() if hasattr(material, "effect") else None
        if effect is None:
            return refs
        techniques = effect.techniques() if hasattr(effect, "techniques") else []
        for tech in list(techniques):
            passes = tech.renderPasses() if hasattr(tech, "renderPasses") else []
            for rpass in list(passes):
                if not hasattr(rpass, "addRenderState"):
                    continue
                mask = color_mask_cls(rpass)
                if hasattr(mask, "setRedMasked"):
                    mask.setRedMasked(True)
                if hasattr(mask, "setGreenMasked"):
                    mask.setGreenMasked(True)
                if hasattr(mask, "setBlueMasked"):
                    mask.setBlueMasked(True)
                if hasattr(mask, "setAlphaMasked"):
                    mask.setAlphaMasked(False)
                rpass.addRenderState(mask)
                refs.append(mask)
    except Exception:
        return refs
    return refs


def material_no_cull_refs(material, render_ns) -> list[Any]:
    refs: list[Any] = []
    try:
        render_api = getattr(render_ns, "Qt3DRender", render_ns)
        cull_cls = getattr(render_api, "QCullFace", None)
        if cull_cls is None:
            return refs
        effect = material.effect() if hasattr(material, "effect") else None
        if effect is None:
            return refs
        techniques = effect.techniques() if hasattr(effect, "techniques") else []
        for tech in list(techniques):
            passes = tech.renderPasses() if hasattr(tech, "renderPasses") else []
            for rpass in list(passes):
                if not hasattr(rpass, "addRenderState"):
                    continue
                cull = cull_cls(rpass)
                mode = getattr(cull_cls, "NoCulling", None)
                if mode is None:
                    enum_cls = getattr(cull_cls, "CullingMode", None)
                    mode = getattr(enum_cls, "NoCulling", None) if enum_cls is not None else None
                if mode is not None and hasattr(cull, "setMode"):
                    cull.setMode(mode)
                rpass.addRenderState(cull)
                refs.append(cull)
    except Exception:
        return refs
    return refs
