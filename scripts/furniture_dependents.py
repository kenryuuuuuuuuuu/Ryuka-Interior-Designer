"""Resolve optional visual records against the current furniture placements.

Bindings and decorations describe attachments to furniture, not placements of
their own. A removed furniture item makes its attachments inactive; the source
records remain available if that furniture ID is restored later.
"""


def resolve(items, bindings, decor):
    present = {item['id'] for item in items}
    active_bindings = [b for b in bindings['bindings'] if b.get('furnitureId') in present]
    active_decor = [d for d in decor['items'] if 'furnitureId' not in d or d['furnitureId'] in present]
    inactive = [dict(sourceFile='data/visual/asset-bindings.json', sourceId=b.get('assetId'),
                     furnitureId=b.get('furnitureId')) for b in bindings['bindings']
                if b.get('furnitureId') not in present]
    inactive += [dict(sourceFile='data/visual/guest-decor.json', sourceId=d.get('id'),
                      furnitureId=d.get('furnitureId')) for d in decor['items']
                 if 'furnitureId' in d and d['furnitureId'] not in present]
    return (dict(bindings, bindings=active_bindings), dict(decor, items=active_decor), inactive)
