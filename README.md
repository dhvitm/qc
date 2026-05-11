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



## Rationalisation cutoff sensitivity

The merged Instamart + Zepto estate starts with 2,127 stores. Re-running the rationalisation count at different overlap cutoffs gives the following retained dark-store counts:

| Overlap cutoff | Centre-distance threshold | Retained merged stores | Rationalised / cut stores | Retained Instamart | Retained Zepto |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50% | 2.424 km | 848 | 1,279 | 582 | 266 |
| 60% | 1.918 km | 1,030 | 1,097 | 685 | 345 |
| 70% | 1.427 km | 1,290 | 837 | 843 | 447 |
| 80% | 0.946 km | 1,569 | 558 | 976 | 593 |

## Standalone overlap calibration

For calibration, the script also computes standalone same-brand overlap. The most useful headline is the **average nearest-neighbour overlap**: for each store, find the same-brand store with the largest 3 km service-area overlap, then average those per-store maxima.

| Brand | Stores | Avg nearest-neighbour overlap | Avg positive pair overlap | 75th percentile nearest-neighbour overlap | Overlapping pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Blinkit | 1,954 | 51.8% | 25.7% | 71.2% | 10,505 |
| Swiggy Instamart | 1,038 | 45.2% | 24.6% | 62.9% | 3,268 |
| Zepto | 1,089 | 55.3% | 25.1% | 70.6% | 5,712 |

## Methodology

- Each Instamart and Zepto dark store is modelled as a 3 km radius circle.
- The equal-circle overlap formula is solved to convert the 70% overlap rule into a centre-distance threshold of 1.427 km.
- Stores within that threshold are connected in an overlap graph.
- The retained merged network is the exact minimum dominating set of that graph: every cut store has at least one retained merged-entity store with more than 70% service-area overlap.
- Blinkit locations are not rationalised; they are plotted as a reference competitor layer.
- Rationalisation cutoff sensitivity is reported for 50%, 60%, 70%, and 80% overlap cutoffs.
- Standalone overlap statistics are reported to help calibrate the rationalisation threshold against current same-brand network density.

## Files

- `index.html` is the original uploaded dark-store map and is left unchanged.
- `rationalisation_map.html` is the Leaflet map of retained merged stores, all Blinkit stores, and a toggleable layer for cut merged stores.
- `generate_map.py` recomputes the rationalisation analysis and regenerates `rationalisation_map.html` and `rationalisation_summary.json`.
- `rationalisation_summary.json` contains the headline counts and modelling assumptions.
- The source location files are the three CSVs in the repository root.

## Regenerate

```bash
python generate_map.py
```

Open `rationalisation_map.html` in a browser to view the rationalisation map.
