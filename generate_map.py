#!/usr/bin/env python3
"""Build the Instamart + Zepto rationalisation map.

The model treats every dark store as a 3 km service circle. Two stores are
considered overlapping enough for rationalisation when the overlapping area of
their equal-radius circles is greater than 70% of one store's service area.
For 3 km circles that is equivalent to centres being less than 1.427 km apart.

For the merged Instamart + Zepto estate, the retained stores are computed as a
minimum dominating set on the >70% overlap graph: every removed store has at
least one retained merged-entity store with >70% coverage overlap.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

SERVICE_RADIUS_KM = 3.0
OVERLAP_CUTOFF = 0.70
EARTH_RADIUS_KM = 6371.0088
ROOT = Path(__file__).resolve().parent


Store = Dict[str, object]


def overlap_ratio(distance_km: float, radius_km: float = SERVICE_RADIUS_KM) -> float:
    """Return equal-circle overlap as a share of one circle's area."""
    if distance_km <= 0:
        return 1.0
    if distance_km >= 2 * radius_km:
        return 0.0
    return (
        2 * radius_km * radius_km * math.acos(distance_km / (2 * radius_km))
        - 0.5 * distance_km * math.sqrt(4 * radius_km * radius_km - distance_km * distance_km)
    ) / (math.pi * radius_km * radius_km)


def distance_for_overlap(target_overlap: float = OVERLAP_CUTOFF) -> float:
    """Solve the centre-distance threshold for an equal-circle overlap ratio."""
    low, high = 0.0, 2 * SERVICE_RADIUS_KM
    for _ in range(80):
        mid = (low + high) / 2
        if overlap_ratio(mid) > target_overlap:
            low = mid
        else:
            high = mid
    return low


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def read_stores(path: str, brand: str) -> List[Store]:
    stores: List[Store] = []
    with (ROOT / path).open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            stores.append(
                {
                    "brand": brand,
                    "id": row["id"],
                    "lat": float(row["lat"]),
                    "lng": float(row["lng"]),
                    "name": row.get("name") or row.get("locality") or "",
                    "city": row.get("city", ""),
                    "state": row.get("state", ""),
                }
            )
    return stores


def build_overlap_graph(stores: Sequence[Store], threshold_km: float) -> List[Set[int]]:
    """Build a graph linking stores whose 3 km circles overlap by >70%."""
    cell_degrees = threshold_km / 111.0
    buckets: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for index, store in enumerate(stores):
        buckets[(int(float(store["lat"]) / cell_degrees), int(float(store["lng"]) / cell_degrees))].append(index)

    adjacency = [{index} for index in range(len(stores))]
    for index, store in enumerate(stores):
        bucket_lat = int(float(store["lat"]) / cell_degrees)
        bucket_lng = int(float(store["lng"]) / cell_degrees)
        for lat_offset in range(-2, 3):
            for lng_offset in range(-2, 3):
                for other_index in buckets.get((bucket_lat + lat_offset, bucket_lng + lng_offset), []):
                    if other_index <= index:
                        continue
                    other = stores[other_index]
                    distance = haversine_km(
                        float(store["lat"]),
                        float(store["lng"]),
                        float(other["lat"]),
                        float(other["lng"]),
                    )
                    if distance < threshold_km:
                        adjacency[index].add(other_index)
                        adjacency[other_index].add(index)
    return adjacency


def connected_components(adjacency: Sequence[Set[int]]) -> List[List[int]]:
    seen = [False] * len(adjacency)
    components: List[List[int]] = []
    for start in range(len(adjacency)):
        if seen[start]:
            continue
        stack = [start]
        seen[start] = True
        component: List[int] = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node]:
                if not seen[neighbor]:
                    seen[neighbor] = True
                    stack.append(neighbor)
        components.append(component)
    return components


def greedy_dominating_set(neighborhoods: Sequence[int]) -> List[int]:
    all_nodes = (1 << len(neighborhoods)) - 1
    uncovered = all_nodes
    chosen: List[int] = []
    while uncovered:
        best = max(range(len(neighborhoods)), key=lambda node: (neighborhoods[node] & uncovered).bit_count())
        chosen.append(best)
        uncovered &= ~neighborhoods[best]
    return chosen


def exact_minimum_dominating_set(component: Sequence[int], adjacency: Sequence[Set[int]]) -> List[int]:
    """Find the minimum stores to keep so all component stores are covered."""
    local_index = {node: index for index, node in enumerate(component)}
    neighborhoods: List[int] = []
    for node in component:
        mask = 0
        for neighbor in adjacency[node]:
            if neighbor in local_index:
                mask |= 1 << local_index[neighbor]
        neighborhoods.append(mask)

    all_nodes = (1 << len(component)) - 1
    initial = greedy_dominating_set(neighborhoods)
    best_count = len(initial)
    best_mask = sum(1 << node for node in initial)
    memo: Dict[int, int] = {}

    def lower_bound(uncovered: int) -> int:
        """Greedy packing lower bound using vertices more than two hops apart."""
        count = 0
        remaining = uncovered
        while remaining:
            leaf = remaining & -remaining
            node = leaf.bit_length() - 1
            count += 1
            dominated_by_candidates = 0
            candidates = neighborhoods[node]
            while candidates:
                candidate_leaf = candidates & -candidates
                candidate = candidate_leaf.bit_length() - 1
                dominated_by_candidates |= neighborhoods[candidate]
                candidates -= candidate_leaf
            remaining &= ~dominated_by_candidates
        return count

    def search(chosen_count: int, covered: int, chosen_mask: int) -> None:
        nonlocal best_count, best_mask
        if chosen_count >= best_count:
            return
        if covered == all_nodes:
            best_count = chosen_count
            best_mask = chosen_mask
            return
        if memo.get(covered, len(component) + 1) <= chosen_count:
            return
        memo[covered] = chosen_count

        uncovered = all_nodes & ~covered
        if chosen_count + lower_bound(uncovered) >= best_count:
            return

        # Branch on the still-uncovered store with the fewest remaining keep choices.
        scan = uncovered
        branch_node = 0
        fewest_options = len(component) + 1
        while scan:
            leaf = scan & -scan
            node = leaf.bit_length() - 1
            options = (neighborhoods[node] & ~chosen_mask).bit_count()
            if options < fewest_options:
                branch_node = node
                fewest_options = options
            scan -= leaf

        candidates: List[int] = []
        scan = neighborhoods[branch_node] & ~chosen_mask
        while scan:
            leaf = scan & -scan
            candidate = leaf.bit_length() - 1
            candidates.append(candidate)
            scan -= leaf
        candidates.sort(key=lambda node: (neighborhoods[node] & uncovered).bit_count(), reverse=True)

        for candidate in candidates:
            search(chosen_count + 1, covered | neighborhoods[candidate], chosen_mask | (1 << candidate))

    search(0, 0, 0)
    return [component[index] for index in range(len(component)) if (best_mask >> index) & 1]


def rationalise(stores: Sequence[Store], adjacency: Sequence[Set[int]]) -> Set[int]:
    retained: Set[int] = set()
    for component in connected_components(adjacency):
        retained.update(exact_minimum_dominating_set(component, adjacency))
    return retained


def to_feature(store: Store, status: str = "retained") -> Dict[str, object]:
    return {
        "brand": store["brand"],
        "id": store["id"],
        "name": store["name"],
        "city": store["city"],
        "state": store["state"],
        "lat": round(float(store["lat"]), 7),
        "lng": round(float(store["lng"]), 7),
        "status": status,
    }


def js_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def render_html(
    retained_merged: Sequence[Dict[str, object]],
    cut_merged: Sequence[Dict[str, object]],
    blinkit: Sequence[Dict[str, object]],
    stats: Dict[str, object],
) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Instamart + Zepto Rationalised Dark Stores vs Blinkit</title>
  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css\" />
  <script src=\"https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js\"></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    body {{ font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; }}
    .summary {{
      position: absolute;
      z-index: 1000;
      top: 16px;
      left: 16px;
      max-width: 390px;
      padding: 16px 18px;
      border-radius: 14px;
      background: rgba(255,255,255,0.94);
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.22);
      color: #172033;
      backdrop-filter: blur(4px);
    }}
    .summary h1 {{ font-size: 18px; margin: 0 0 8px; line-height: 1.25; }}
    .summary p {{ margin: 6px 0; font-size: 13px; line-height: 1.4; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 12px 0; }}
    .metric {{ border-radius: 10px; padding: 9px; background: #f3f6fb; }}
    .metric strong {{ display: block; font-size: 20px; color: #0f172a; }}
    .metric span {{ display: block; font-size: 11px; color: #475569; }}
    .legend-row {{ display: flex; align-items: center; gap: 8px; font-size: 12px; margin: 5px 0; }}
    .swatch {{ width: 13px; height: 13px; border-radius: 50%; display: inline-block; opacity: 0.85; }}
    .leaflet-tooltip {{ font-size: 12px; }}
    @media (max-width: 700px) {{
      .summary {{ left: 8px; right: 8px; top: 8px; max-width: none; padding: 12px; }}
      .summary h1 {{ font-size: 15px; }}
      .summary p {{ font-size: 11px; }}
      .metric strong {{ font-size: 16px; }}
    }}
  </style>
</head>
<body>
  <div id=\"map\"></div>
  <aside class=\"summary\">
    <h1>Instamart + Zepto rationalisation vs Blinkit</h1>
    <p>A merged Instamart + Zepto network has <strong>{stats['retained_total']:,}</strong> retained dark stores after cutting stores whose 3 km service circles are covered by another merged-entity store at &gt;70% overlap.</p>
    <div class=\"metric-grid\">
      <div class=\"metric\"><strong>{stats['starting_total']:,}</strong><span>starting merged stores</span></div>
      <div class=\"metric\"><strong>{stats['cut_total']:,}</strong><span>rationalised stores</span></div>
      <div class=\"metric\"><strong>{stats['blinkit_total']:,}</strong><span>Blinkit stores</span></div>
    </div>
    <p>3 km circles overlap by 70% when centres are within <strong>{stats['overlap_threshold_km']:.3f} km</strong>. The retained set is an exact minimum dominating set of the overlap graph.</p>
    <div class=\"legend-row\"><span class=\"swatch\" style=\"background:#2563eb\"></span>Retained Instamart + Zepto stores</div>
    <div class=\"legend-row\"><span class=\"swatch\" style=\"background:#16a34a\"></span>Blinkit stores</div>
    <div class=\"legend-row\"><span class=\"swatch\" style=\"background:#dc2626\"></span>Cut merged stores (toggleable layer)</div>
  </aside>
  <script>
    const serviceRadiusMeters = {int(SERVICE_RADIUS_KM * 1000)};
    const retainedMergedStores = {js_json(retained_merged)};
    const cutMergedStores = {js_json(cut_merged)};
    const blinkitStores = {js_json(blinkit)};

    const map = L.map('map', {{ preferCanvas: true }}).setView([22.5, 79], 5);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      maxZoom: 20,
      attribution: '&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors &copy; <a href=\"https://carto.com/attributions\">CARTO</a>'
    }}).addTo(map);

    function tooltip(store) {{
      const place = [store.city, store.state].filter(Boolean).join(', ');
      return `<strong>${{store.brand}}</strong><br>ID: ${{store.id}}${{store.name ? `<br>${{store.name}}` : ''}}${{place ? `<br>${{place}}` : ''}}${{store.status === 'cut' ? '<br><em>Rationalised / cut</em>' : ''}}`;
    }}

    function addCircleLayer(stores, color, fillOpacity, weight) {{
      const layer = L.layerGroup();
      stores.forEach((store) => {{
        L.circle([store.lat, store.lng], {{
          radius: serviceRadiusMeters,
          color,
          weight,
          opacity: 0.78,
          fillColor: color,
          fillOpacity
        }}).bindTooltip(tooltip(store), {{ sticky: true }}).addTo(layer);
      }});
      return layer;
    }}

    const retainedLayer = addCircleLayer(retainedMergedStores, '#2563eb', 0.13, 1.3).addTo(map);
    const blinkitLayer = addCircleLayer(blinkitStores, '#16a34a', 0.10, 1.0).addTo(map);
    const cutLayer = addCircleLayer(cutMergedStores, '#dc2626', 0.06, 0.8);

    L.control.layers(null, {{
      'Retained Instamart + Zepto ({stats['retained_total']:,})': retainedLayer,
      'Blinkit ({stats['blinkit_total']:,})': blinkitLayer,
      'Cut merged stores ({stats['cut_total']:,})': cutLayer
    }}, {{ collapsed: false }}).addTo(map);
  </script>
</body>
</html>
"""


def main() -> None:
    instamart = read_stores("swiggy-darkstores (1).csv", "Instamart")
    zepto = read_stores("zepto-darkstores (1).csv", "Zepto")
    blinkit = read_stores("blinkit-darkstores (2).csv", "Blinkit")
    merged = instamart + zepto

    threshold_km = distance_for_overlap()
    adjacency = build_overlap_graph(merged, threshold_km)
    retained_indexes = rationalise(merged, adjacency)

    retained_merged = [to_feature(store, "retained") for index, store in enumerate(merged) if index in retained_indexes]
    cut_merged = [to_feature(store, "cut") for index, store in enumerate(merged) if index not in retained_indexes]
    blinkit_features = [to_feature(store, "reference") for store in blinkit]

    retained_counts = Counter(store["brand"] for store in retained_merged)
    cut_counts = Counter(store["brand"] for store in cut_merged)
    stats = {
        "starting_total": len(merged),
        "instamart_starting": len(instamart),
        "zepto_starting": len(zepto),
        "retained_total": len(retained_merged),
        "cut_total": len(cut_merged),
        "retained_instamart": retained_counts["Instamart"],
        "retained_zepto": retained_counts["Zepto"],
        "cut_instamart": cut_counts["Instamart"],
        "cut_zepto": cut_counts["Zepto"],
        "blinkit_total": len(blinkit),
        "overlap_threshold_km": threshold_km,
        "service_radius_km": SERVICE_RADIUS_KM,
        "overlap_cutoff": OVERLAP_CUTOFF,
    }

    (ROOT / "rationalisation_summary.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    (ROOT / "index.html").write_text(render_html(retained_merged, cut_merged, blinkit_features, stats), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
