"""Per-surface finish override resolution: merging a base variant's palette
with an optional override (variant swap and/or explicit colorHex/roughness),
and checking override target IDs against what is actually known to exist.
Pure Python; shared by Blender (build_interior.py), the UE editor
(study_controls.py), and the one-time UE import (import_study.py) -- the
color/roughness/pattern resolution logic lives here exactly once so all three
agree on what a given override actually means.
"""
from finish_settings import details_for_variant

KINDS = ('wall', 'floor', 'ceiling')


def resolve_finish(finish_document, study_variants, kind, base_variant, override=None):
    """dict(variant, colorHex, roughness, pattern, paletteRole) for `kind`
    under `base_variant`, with `override` (any subset of variant/colorHex/
    roughness) layered on top. No override -> identical to the plain base
    variant's own finish, so an un-overridden registered surface renders
    exactly like its surroundings."""
    override = override or {}
    variant = override.get('variant', base_variant)
    detail = dict(details_for_variant(finish_document, variant)[kind])
    palette_role = detail.get('paletteRole', kind)
    color_hex = override.get('colorHex', study_variants[variant][palette_role])
    roughness = override.get('roughness', detail['roughness'])
    return dict(variant=variant, colorHex=color_hex, roughness=roughness,
        pattern=detail.get('pattern'), paletteRole=palette_role)


def marker_material_name(kind, surface_id):
    # '.' is not used (GLB/UE material-name sanitization collapses it); kept
    # ASCII/underscore-safe so the name round-trips through GLB export and UE
    # Interchange import unchanged (surface ids are themselves plain ASCII).
    return f'Surf_{kind}_{surface_id}'


def resolve_overrides(overrides, bindings):
    """overrides: state['surfaceOverrides']. bindings: parsed
    surface-bindings.json (schemaVersion 1.0.0; surfaces: {id: {kind, roomId,
    status, meshes}}). Returns (usable, issues): usable is the subset of
    overrides whose target actually resolved to bound geometry; issues
    explains every excluded one (unknown id / no-surface). Never raises --
    a state carrying a stale/orphaned override must still be listable and
    explainable, not rejected outright. Callers about to *apply* a state
    (not just list it) should treat a non-empty issues list as a stop
    condition and not silently drop those overrides."""
    surfaces = bindings.get('surfaces', {})
    usable = {}
    issues = []
    for surface_id, override in overrides.items():
        entry = surfaces.get(surface_id)
        if entry is None:
            issues.append(dict(id=surface_id, reason=f'surfaceOverridesが参照する面{surface_id}は現在の登録にありません。'))
        elif entry.get('status') != 'bound':
            issues.append(dict(id=surface_id, reason=f'面{surface_id}には実在する仕上げ面がありません（no-surface）。上書きは適用できません。'))
        else:
            usable[surface_id] = override
    return usable, issues
