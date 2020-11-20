# ---------------------------------------------------------------------------
# workflow_HW.py
# Version: ArcPro / Python 3+
# Creation Date: 2020-07-06
# Last Edit: 2020-11-17
# Creator: Kirsten R. Hazler
#
# Summary: 
# This sets up Watershed Protection Model processing and serves as a record of inputs and outputs
# ---------------------------------------------------------------------------

# Import modules
import prioritizeHW
from prioritizeHW import *

### Inputs/Outputs
outGDB = r"N:\HealthyWaters\hwProducts_20201117.gdb" # I change this frequently as I proceed with running lines of code

# Masks and bounding polygons
BoundPoly = r"Y:\SpatialData\HealthyWatersWork\HW_templateRaster_Feature\HW_templateFeature.shp"
procMask = r"Y:\SpatialData\SnapMasks\procMask50_conus.tif"
MaskNoWater = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\mskNoWater_2016"
consMask = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\consMask"
restMask = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\restMask"
mgmtMask = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\mgmtMask"

# Soil Sensitivity Score Inputs/Outputs
## Note: runoffVol_bare and soilLoss_bare rasters were created with functions in procSSURGO.py.
runoffVol_bare = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffVol_bare"
soilLoss_bare = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\rusleRKSC_bare"
runoffScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\runoff_Score_bare"
soilLossScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\soilLoss_Score_bare"
SoilSensScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\soilSens_Score_bare"

# Landscape Position Score Inputs/Outputs
## Note: FlowLength raster was derived from set of NHDPlus_HR fdroverland rasters (David processed these)
FlowLines = r"Y:\DavidData\From_David\VA_HydroNetHR.gdb\HydroNet\NHDFlowline"
Catchments = r"Y:\DavidData\From_David\VA_HydroNetHR.gdb\NHDPlusCatchment"
FlowLength = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\overlandFlowLength"
Headwaters = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\Hdwtrs"
FlowScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\FlowScore"
KarstPolys = r"Y:\SpatialData\USGS\USKarstMap\USKarstMap.gdb\Contiguous48\Carbonates48"
SinkPolys = r"Y:\SpatialData\DMME\Sinkholes_VaDMME_2020SeptCurrent\Sinkholes_VaDMME.shp"
SinkScore = outGDB + os.sep + "sinkScore"
KarstScore = outGDB + os.sep + "KarstScore"
PositionScore = outGDB + os.sep + "PositionScore"

# Impact, Importance, and Priority Scores Inputs/Outputs
ImpactScore = outGDB + os.sep + "ImpactScore"


### Specify function(s) to run
# Create the specified outGDB if it doesn't already exist
createFGDB(outGDB) 

# # Create additional processing masks
# (consMask, restMask, mgmtMask) = makeLandcoverMasks(MaskNoWater, outGDB)

# # Get Soil Sensitivity Score
# calcSoilSensScore(soilLoss_bare, runoffVol_bare, outGDB, "bare", MaskNoWater)

# # Get Landscape Position Score
# makeHdwtrsIndicator(FlowLines, Catchments, BoundPoly, MaskNoWater, Headwaters)
# calcFlowScore(FlowLength, FlowScore, Headwaters)
# calcKarstScore(KarstPolys, MaskNoWater, KarstScore, KarstPoints, karstGDB)
# calcSinkScore(SinkPolys, "SqMeters", procMask, MaskNoWater, outGDB, searchRadius = 5000)
calcKarstScore(KarstPolys, procMask, MaskNoWater, outGDB, SinkScore, minDist = 100, maxDist = 5000)
calcPositionScore(FlowScore, KarstScore, PositionScore)
arcpy.env.workspace = outGDB
ras = ["SinkScore", "KarstScore", "PositionScore"]
arcpy.BatchBuildPyramids_management(ras, "", "", "", "", "", "SKIP_EXISTING")

# Get Impact Score
calcImpactScore(PositionScore, SoilSensScore, ImpactScore)

# Importance, and Priority Scores

   
