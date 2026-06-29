# =============================================================
# AccessPortland - Accessibility Score Script v3 FIXED
# Course: GEOG 4046 - Web GIS
# Author: Swabhiman
# University of Idaho - Spring 2026
# =============================================================

import arcpy
import os
import csv
from collections import defaultdict

# =============================================================
# PATHS
# =============================================================
raw_data   = r"C:\Users\reule\OneDrive - University of Idaho\Uidaho Spring 2026\AccessPortland\01_RawData"
processing = r"C:\Users\reule\OneDrive - University of Idaho\Uidaho Spring 2026\AccessPortland\02_Processing"
final      = r"C:\Users\reule\OneDrive - University of Idaho\Uidaho Spring 2026\AccessPortland\03_FinalLayers"

stop_features_txt = os.path.join(raw_data, "stop_features.txt")
gdb               = os.path.join(processing, "AccessPortland.gdb")
stops_fc          = os.path.join(gdb, "Stops_With_Neighborhoods")

arcpy.env.workspace       = gdb
arcpy.env.overwriteOutput = True

# =============================================================
# STEP 1: Read stop_features.txt
# =============================================================
print("=" * 55)
print("Accessibility Score Script v3 FIXED")
print("=" * 55)
print("\nStep 1: Reading stop_features.txt...")

stop_features = defaultdict(list)

with open(stop_features_txt, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        sid     = str(row["stop_id"]).strip()
        feature = str(row["feature_name"]).strip().lower()
        stop_features[sid].append(feature)

print(f"  Loaded features for {len(stop_features)} unique stops")

# =============================================================
# STEP 2: Scoring system
# =============================================================
print("\nStep 2: Calculating accessibility scores...")

scoring = {
    "curb ramp near stop"      : 3,
    "sidewalk at stop"         : 3,
    "audio signage"            : 2,
    "tactile paving"           : 2,
    "audible pedestrian signal": 2,
    "shelter"                  : 1,
    "bench near stop"          : 1,
    "schedule display"         : 1,
    "lighting"                 : 1,
    "crosswalk near stop"      : 1,
    "pavement at front door"   : 1,
    "pavement at back door"    : 1,
    "traffic signal"           : 1,
    "garbage can"              : 0,
}

stop_scores = {}
for sid, features in stop_features.items():
    score = sum(scoring.get(feat, 0) for feat in features)
    stop_scores[sid] = score

scores = list(stop_scores.values())
print(f"  Stops with feature data: {len(stop_scores)}")
print(f"  Max score: {max(scores)}")
print(f"  Min score: {min(scores)}")
print(f"  Average:   {sum(scores)/len(scores):.1f}")

# =============================================================
# STEP 3: Categorize
# =============================================================
print("\nStep 3: Categorizing accessibility levels...")

def categorize(score):
    if score >= 8:
        return "High"
    elif score >= 4:
        return "Medium"
    else:
        return "Low"

high   = sum(1 for s in scores if s >= 8)
medium = sum(1 for s in scores if 4 <= s < 8)
low    = sum(1 for s in scores if s < 4)

print(f"  High   (8+):  {high} stops")
print(f"  Medium (4-7): {medium} stops")
print(f"  Low   (0-3):  {low} stops")

# =============================================================
# STEP 4: Update fields — using correct field name TM_Stops_stop_id
# =============================================================
print("\nStep 4: Updating accessibility scores in stops layer...")

matched   = 0
unmatched = 0

# ✅ FIXED: using TM_Stops_stop_id instead of stop_id
with arcpy.da.UpdateCursor(stops_fc, ["TM_Stops_stop_id", "acc_score", "acc_level", "feat_count"]) as cursor:
    for row in cursor:
        sid = str(row[0]).strip()
        if sid in stop_scores:
            row[1] = stop_scores[sid]
            row[2] = categorize(stop_scores[sid])
            row[3] = len(stop_features[sid])
            matched += 1
        else:
            row[1] = 0
            row[2] = "No Data"
            row[3] = 0
            unmatched += 1
        cursor.updateRow(row)

print(f"  Matched stops:   {matched}")
print(f"  Unmatched stops: {unmatched} (marked No Data)")

# =============================================================
# STEP 5: Export to 03_FinalLayers
# =============================================================
print("\nStep 5: Exporting final layer...")

out_shp = os.path.join(final, "Stops_Accessibility_Final.shp")
arcpy.management.CopyFeatures(stops_fc, out_shp)
count = arcpy.management.GetCount(out_shp)[0]
print(f"  Exported: Stops_Accessibility_Final.shp ({count} features)")

# =============================================================
# DONE
# =============================================================
print("\n" + "=" * 55)
print("ACCESSIBILITY SCORE COMPLETE!")
print("=" * 55)
print("\nNew fields in final layer:")
print("  acc_score  = numeric score (0-19)")
print("  acc_level  = High / Medium / Low / No Data")
print("  feat_count = number of features at stop")
print("\nArcGIS Online ma symbolize by acc_level:")
print("  High   = Green  🟢")
print("  Medium = Yellow 🟡")
print("  Low    = Red    🔴")
print("  No Data = Gray  ⚪")
print("=" * 55)
