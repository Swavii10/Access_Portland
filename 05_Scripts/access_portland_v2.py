# =============================================================
# AccessPortland - ArcPy Processing Script v2
# Course: GEOG 4046 - Web GIS
# Author: Swabhiman
# University of Idaho - Spring 2026
# =============================================================
# WHAT THIS SCRIPT DOES:
# Step 1: Import tm_stops.shp (TriMet official stops shapefile)
# Step 2: Join wheelchair_boarding from GTFS stops.txt
# Step 3: Add accessibility category field
# Step 4: Clip stops to Portland Neighborhood boundary
# Step 5: Spatial Join with Neighborhoods (adds neighborhood name)
# Step 6: Import Rail Lines, Rail Stops, Routes
# Step 7: Export final layers to 03_FinalLayers (ready for ArcGIS Online)
# =============================================================
# AFTER SCRIPT RUNS - YOU WILL HAVE:
# 03_FinalLayers/
#   Stops_With_Neighborhoods.shp  <- Main layer: all stops + accessibility + neighborhood
#   TriMet_Rail_Lines.shp         <- MAX + Streetcar lines
#   TriMet_Rail_Stops.shp         <- Rail stop locations
#   TriMet_Routes.shp             <- Bus + rail routes
# =============================================================

import arcpy
import os

# =============================================================
# PATHS
# =============================================================
raw_data   = r"C:\Users\reule\OneDrive - University of Idaho\Uidaho Spring 2026\AccessPortland\01_RawData"
processing = r"C:\Users\reule\OneDrive - University of Idaho\Uidaho Spring 2026\AccessPortland\02_Processing"
final      = r"C:\Users\reule\OneDrive - University of Idaho\Uidaho Spring 2026\AccessPortland\03_FinalLayers"

# Input files
stops_txt          = os.path.join(raw_data, "stops.txt")           # GTFS - has wheelchair_boarding
tm_stops_shp       = os.path.join(raw_data, "tm_stops.shp")        # TriMet official stops shapefile
neighborhood_shp   = os.path.join(raw_data, "Neighborhood_Boundaries.shp")
tm_rail_lines_shp  = os.path.join(raw_data, "tm_rail_lines.shp")
tm_rail_stops_shp  = os.path.join(raw_data, "tm_rail_stops.shp")
tm_routes_shp      = os.path.join(raw_data, "tm_routes.shp")

# Geodatabase
gdb = os.path.join(processing, "AccessPortland.gdb")

# =============================================================
# SETUP
# =============================================================
print("=" * 55)
print("AccessPortland - ArcPy Processing Script v2")
print("=" * 55)
print("\nSetting up workspace...")

if not os.path.exists(gdb):
    arcpy.management.CreateFileGDB(processing, "AccessPortland.gdb")
    print("  Created: AccessPortland.gdb")
else:
    print("  Geodatabase already exists - continuing...")

arcpy.env.workspace = gdb
arcpy.env.overwriteOutput = True

# =============================================================
# STEP 1: Import tm_stops.shp to GDB
# =============================================================
print("\nStep 1: Importing tm_stops.shp...")

tm_stops_fc = os.path.join(gdb, "TM_Stops")
arcpy.management.CopyFeatures(tm_stops_shp, tm_stops_fc)
count = arcpy.management.GetCount(tm_stops_fc)[0]
print(f"  Imported {count} stops from tm_stops.shp")

# Check existing fields in tm_stops
fields = [f.name for f in arcpy.ListFields(tm_stops_fc)]
print(f"  Fields in tm_stops: {fields}")

# =============================================================
# STEP 2: Join wheelchair_boarding from GTFS stops.txt
# Match on stop_id field
# =============================================================
print("\nStep 2: Joining wheelchair_boarding from GTFS stops.txt...")

# Check if wheelchair_boarding already exists in tm_stops
if "wheelchair" in [f.name.lower() for f in arcpy.ListFields(tm_stops_fc)]:
    print("  wheelchair field already exists in tm_stops - skipping join")
    stops_joined = tm_stops_fc
else:
    # Join GTFS stops.txt to tm_stops using stop_id
    stops_joined = os.path.join(gdb, "TM_Stops_Joined")
    arcpy.management.MakeFeatureLayer(tm_stops_fc, "tm_stops_lyr")
    arcpy.management.AddJoin(
        in_layer_or_view  = "tm_stops_lyr",
        in_field          = "stop_id",
        join_table        = stops_txt,
        join_field        = "stop_id",
        join_type         = "KEEP_ALL"
    )
    arcpy.management.CopyFeatures("tm_stops_lyr", stops_joined)
    print("  wheelchair_boarding field joined from GTFS")

# =============================================================
# STEP 3: Add accessibility category field
# =============================================================
print("\nStep 3: Adding accessibility category field...")

# Add access_cat field
arcpy.management.AddField(stops_joined, "access_cat", "TEXT", field_length=20)

# Find the wheelchair_boarding field name (may vary after join)
all_fields = [f.name for f in arcpy.ListFields(stops_joined)]
wb_field = None
for f in all_fields:
    if "wheelchair" in f.lower():
        wb_field = f
        break

if wb_field:
    print(f"  Found wheelchair field: {wb_field}")
    accessible     = 0
    not_accessible = 0
    unknown        = 0

    with arcpy.da.UpdateCursor(stops_joined, [wb_field, "access_cat"]) as cursor:
        for row in cursor:
            val = str(row[0]).strip() if row[0] is not None else "0"
            if val == "1":
                row[1] = "Accessible"
                accessible += 1
            elif val == "2":
                row[1] = "Not Accessible"
                not_accessible += 1
            else:
                row[1] = "Unknown"
                unknown += 1
            cursor.updateRow(row)

    print(f"  Accessible:     {accessible} stops")
    print(f"  Not Accessible: {not_accessible} stops")
    print(f"  Unknown:        {unknown} stops")
else:
    print("  WARNING: wheelchair_boarding field not found!")
    print("  Marking all stops as Unknown")
    with arcpy.da.UpdateCursor(stops_joined, ["access_cat"]) as cursor:
        for row in cursor:
            row[0] = "Unknown"
            cursor.updateRow(row)

# =============================================================
# STEP 4: Reproject to Oregon State Plane North (NAD83)
# =============================================================
print("\nStep 4: Reprojecting to Oregon State Plane North...")

stops_projected = os.path.join(gdb, "TM_Stops_Projected")
arcpy.management.Project(
    in_dataset      = stops_joined,
    out_dataset     = stops_projected,
    out_coor_system = arcpy.SpatialReference(2269)  # NAD83 Oregon State Plane North (ft)
)
print("  Reprojected successfully.")

# =============================================================
# STEP 5: Clip Stops to Portland Neighborhood Boundary
# =============================================================
print("\nStep 5: Clipping stops to Portland boundary...")

stops_clipped = os.path.join(gdb, "Stops_Portland")
arcpy.analysis.Clip(
    in_features       = stops_projected,
    clip_features     = neighborhood_shp,
    out_feature_class = stops_clipped
)
count = arcpy.management.GetCount(stops_clipped)[0]
print(f"  {count} stops within Portland boundary")

# =============================================================
# STEP 6: Spatial Join - Add Neighborhood Name to Each Stop
# =============================================================
print("\nStep 6: Joining neighborhood names to stops...")

stops_final = os.path.join(gdb, "Stops_With_Neighborhoods")
arcpy.analysis.SpatialJoin(
    target_features   = stops_clipped,
    join_features     = neighborhood_shp,
    out_feature_class = stops_final,
    join_operation    = "JOIN_ONE_TO_ONE",
    join_type         = "KEEP_ALL",
    match_option      = "WITHIN"
)
print("  Neighborhood name added to each stop.")

# =============================================================
# STEP 7: Import Rail Lines, Rail Stops, Routes
# =============================================================
print("\nStep 7: Importing TriMet rail and route layers...")

rail_lines_fc = os.path.join(gdb, "TriMet_Rail_Lines")
rail_stops_fc = os.path.join(gdb, "TriMet_Rail_Stops")
routes_fc     = os.path.join(gdb, "TriMet_Routes")

arcpy.management.CopyFeatures(tm_rail_lines_shp, rail_lines_fc)
print("  TriMet Rail Lines imported.")
arcpy.management.CopyFeatures(tm_rail_stops_shp, rail_stops_fc)
print("  TriMet Rail Stops imported.")
arcpy.management.CopyFeatures(tm_routes_shp, routes_fc)
print("  TriMet Routes imported.")

# =============================================================
# STEP 8: Export Final Layers to 03_FinalLayers
# Ready to upload to ArcGIS Online
# =============================================================
print("\nStep 8: Exporting final layers to 03_FinalLayers...")

if not os.path.exists(final):
    os.makedirs(final)
    print("  Created 03_FinalLayers folder.")

exports = {
    "Stops_With_Neighborhoods" : stops_final,
    "TriMet_Rail_Lines"        : rail_lines_fc,
    "TriMet_Rail_Stops"        : rail_stops_fc,
    "TriMet_Routes"            : routes_fc,
}

for name, fc in exports.items():
    out_shp = os.path.join(final, f"{name}.shp")
    arcpy.management.CopyFeatures(fc, out_shp)
    count = arcpy.management.GetCount(out_shp)[0]
    print(f"  Exported: {name}.shp ({count} features)")

# =============================================================
# DONE!
# =============================================================
print("\n" + "=" * 55)
print("ALL STEPS COMPLETE!")
print("=" * 55)
print("\nFinal layers in 03_FinalLayers:")
print("  Stops_With_Neighborhoods.shp  <- Upload this first!")
print("  TriMet_Rail_Lines.shp")
print("  TriMet_Rail_Stops.shp")
print("  TriMet_Routes.shp")
print("\nNext Step:")
print("  Upload these shapefiles to ArcGIS Online")
print("  as Hosted Feature Layers.")
print("=" * 55)
