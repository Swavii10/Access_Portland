# =============================================================
# AccessPortland - Accessibility Score Script v3
# Course: GEOG 4046 - Web GIS
# Author: Swabhiman
# University of Idaho - Spring 2026
# =============================================================
# WHAT THIS SCRIPT DOES:
# Step 1: Read stop_features.txt and pivot to wide format
# Step 2: Calculate accessibility score per stop
# Step 3: Categorize: High / Medium / Low
# Step 4: Join scores to Stops_With_Neighborhoods layer
# Step 5: Export final layer to 03_FinalLayers
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

arcpy.env.workspace      = gdb
arcpy.env.overwriteOutput = True

# =============================================================
# STEP 1: Read stop_features.txt
# Build dictionary: stop_id → list of features
# =============================================================
print("=" * 55)
print("Accessibility Score Script v3")
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
# STEP 2: Define scoring system
# Higher weight = more critical for accessibility
# =============================================================
print("\nStep 2: Calculating accessibility scores...")

# Scoring weights
scoring = {
    "curb ramp near stop"    : 3,   # wheelchair essential
    "sidewalk at stop"       : 3,   # pedestrian essential
    "audio signage"          : 2,   # visually impaired
    "tactile paving"         : 2,   # visually impaired
    "audible pedestrian signal": 2, # visually impaired
    "shelter"                : 1,   # comfort/weather
    "bench near stop"        : 1,   # elderly/mobility
    "schedule display"       : 1,   # information access
    "lighting"               : 1,   # night safety
    "garbage can"            : 0,   # not accessibility
    "crosswalk near stop"    : 1,   # pedestrian safety
    "pavement at front door" : 1,   # surface access
    "pavement at back door"  : 1,   # surface access
    "traffic signal"         : 1,   # pedestrian safety
}

# Maximum possible score
max_score = sum([3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1])  # = 19

# Calculate score per stop
stop_scores = {}
for sid, features in stop_features.items():
    score = 0
    for feat in features:
        score += scoring.get(feat, 0)
    stop_scores[sid] = score

# Print score distribution
scores = list(stop_scores.values())
print(f"  Stops with features data: {len(stop_scores)}")
print(f"  Max score found:          {max(scores)}")
print(f"  Min score found:          {min(scores)}")
avg = sum(scores) / len(scores)
print(f"  Average score:            {avg:.1f}")

# =============================================================
# STEP 3: Categorize scores
# High / Medium / Low based on thirds
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

print(f"  High Accessibility   (8+):  {high} stops")
print(f"  Medium Accessibility (4-7): {medium} stops")
print(f"  Low Accessibility   (0-3):  {low} stops")

# =============================================================
# STEP 4: Add score fields to Stops_With_Neighborhoods
# =============================================================
print("\nStep 4: Adding score fields to stops layer...")

# Add fields if they don't exist
existing_fields = [f.name for f in arcpy.ListFields(stops_fc)]

if "acc_score" not in existing_fields:
    arcpy.management.AddField(stops_fc, "acc_score", "SHORT")
    print("  Added field: acc_score")

if "acc_level" not in existing_fields:
    arcpy.management.AddField(stops_fc, "acc_level", "TEXT", field_length=10)
    print("  Added field: acc_level")

if "feat_count" not in existing_fields:
    arcpy.management.AddField(stops_fc, "feat_count", "SHORT")
    print("  Added field: feat_count")

# Update scores using stop_id
matched   = 0
unmatched = 0

with arcpy.da.UpdateCursor(stops_fc, ["stop_id", "acc_score", "acc_level", "feat_count"]) as cursor:
    for row in cursor:
        sid = str(row[0]).strip()
        if sid in stop_scores:
            score      = stop_scores[sid]
            feat_count = len(stop_features[sid])
            row[1] = score
            row[2] = categorize(score)
            row[3] = feat_count
            matched += 1
        else:
            row[1] = 0
            row[2] = "No Data"
            row[3] = 0
            unmatched += 1
        cursor.updateRow(row)

print(f"  Matched stops:   {matched}")
print(f"  Unmatched stops: {unmatched} (marked as No Data)")

# =============================================================
# STEP 5: Export updated layer to 03_FinalLayers
# =============================================================
print("\nStep 5: Exporting final layer...")

out_shp = os.path.join(final, "Stops_Accessibility_Final.shp")
arcpy.management.CopyFeatures(stops_fc, out_shp)
count = arcpy.management.GetCount(out_shp)[0]
print(f"  Exported: Stops_Accessibility_Final.shp ({count} features)")

# =============================================================
# DONE!
# =============================================================
print("\n" + "=" * 55)
print("ACCESSIBILITY SCORE COMPLETE!")
print("=" * 55)
print("\nNew fields added to stops layer:")
print("  acc_score  = numeric score (0-19)")
print("  acc_level  = High / Medium / Low / No Data")
print("  feat_count = number of features at stop")
print("\nFile ready for ArcGIS Online:")
print("  Stops_Accessibility_Final.shp")
print("\nIn ArcGIS Online - symbolize by:")
print("  acc_level field (High=Green, Medium=Yellow, Low=Red)")
print("=" * 55)
