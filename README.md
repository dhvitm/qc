# Quick-commerce dark store rationalisation

This repository maps a potential Instamart + Zepto merger rationalisation against Blinkit's dark-store network in India.

## Result

Using a 3 km service radius per dark store, two stores have more than 70% service-area overlap when their centres are within **1.427 km**. Applying that threshold to the combined Instamart + Zepto network leaves **1,290 retained dark stores** after rationalising **837** overlapping stores from the original **2,127** merged-entity locations.

| Metric | Count |
| --- | ---: |
| Instamart starting stores | 1,038 |
| Zepto starting stores | 1,089 |
| Starting merged stores | 2,127 |
| Retained merged stores after rationalisation | 1,290 |
| Rationalised / cut merged stores | 837 |
| Blinkit reference stores on the map | 1,954 |

## Methodology

- Each Instamart and Zepto dark store is modelled as a 3 km radius circle.
- The equal-circle overlap formula is solved to convert the 70% overlap rule into a centre-distance threshold of 1.427 km.
- Stores within that threshold are connected in an overlap graph.
- The retained merged network is the exact minimum dominating set of that graph: every cut store has at least one retained merged-entity store with more than 70% service-area overlap.
- Blinkit locations are not rationalised; they are plotted as a reference competitor layer.

## Files

- `index.html` is the Leaflet map of retained merged stores, all Blinkit stores, and a toggleable layer for cut merged stores.
- `generate_map.py` recomputes the rationalisation analysis and regenerates `index.html` and `rationalisation_summary.json`.
- `rationalisation_summary.json` contains the headline counts and modelling assumptions.
- The source location files are the three CSVs in the repository root.

## Regenerate

```bash
python generate_map.py
```

Open `index.html` in a browser to view the map.
