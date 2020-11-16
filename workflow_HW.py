# ---------------------------------------------------------------------------
# workflow_HW.py
# Version: ArcPro / Python 3+
# Creation Date: 2020-07-06
# Last Edit: 2020-11-13
# Creator: Kirsten R. Hazler
#
# Summary: 
# This sets up Watershed Model and Healthy Waters prioritization processing and serves as a record of inputs and outputs

# NOTE (11/6/2020): Old karst data were used in the July run. Functions using karst data will need to be run with the updated data. This has not yet been done. Dave Boyd is checking with DMME to make sure the dataset is correct, since there is an obvious shift between old and new.
# ---------------------------------------------------------------------------

# Import modules
import prioritizeHW
from prioritizeHW import *

### Inputs/Outputs
outGDB = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20201113.gdb" # I change this frequently as I proceed with running lines of code
karstGDB = r"Y:\SpatialData\HealthyWatersWork\karstProc_20200716.gdb"

# Masks and bounding polygons
BoundPoly = r"Y:\SpatialData\HealthyWatersWork\HW_templateRaster_Feature\HW_templateFeature.shp"
procMask = r"Y:\SpatialData\SnapMasks\procMask50_conus.tif"
MaskNoWater = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\mskNoWater_2016"
consMask = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\consMask"
restMask = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\restMask"
mgmtMask = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\mgmtMask"

# Soil Sensitivity Score Inputs/Outputs
runoffVol_bare = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffVol_bare"
soilLoss_bare = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\rusleRKSC_bare"
runoffVol_dfor = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffVol_dfor"
soilLoss_dfor = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\rusleRKSC_dfor"
runoffVol = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffVol_2016"
soilLoss = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\RKSC_2016"
SoilSensScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\soilSens_Score_bare"

# Landscape Position Score Inputs/outputs
FlowLines = r"Y:\DavidData\From_David\VA_HydroNetHR.gdb\HydroNet\NHDFlowline"
Catchments = r"Y:\DavidData\From_David\VA_HydroNetHR.gdb\NHDPlusCatchment"
FlowLength = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\overlandFlowLength"
Headwaters = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\Hdwtrs"
FlowScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200716.gdb\FlowScore"
KarstPolys = r"Y:\SpatialData\USGS\USKarstMap\USKarstMap.gdb\Contiguous48\Carbonates48"
SinkPolys = r"Y:\SpatialData\DMME\Sinkholes_VaDMME_2020SeptCurrent\Sinkholes_VaDMME.shp"
SinkScore = outGDB + os.sep + "SinkScore"
KarstScore = outGDB + os.sep + "KarstScore"
LandscapeScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\LandscapeScore"

# Impact Inputs/Outputs
hwResourceAreas = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceAreas"
hwRA10k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceAreas_10km"
hwRA5k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceAreas_5km"
hwRA3k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceAreas_3km"
hwRA2k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceAreas_2km"
hwResourceScore = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceScore"
hwResourceScore10k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceScore10k"
hwResourceScore2k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceScore2k"
hwResourceScoreCombo = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\hwResourceScoreCombo"
hwResourceScore10kCombo = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200721.gdb\hwResourceScore10kCombo"
ImpactScore_base = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\ImpactScore_base"
ImpactScore_hw = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\ImpactScore_hw"
ImpactScore_hw2k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\ImpactScore_hw2k"
ImpactScore_hw10k = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\ImpactScore_hw10k"
ImpactScore_hwCombo = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200720.gdb\ImpactScore_hwCombo"
ImpactScore_hw10kCombo = r"Y:\SpatialData\HealthyWatersWork\hwProducts_20200721.gdb\ImpactScore_hw10kCombo"

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
calcSinkScore(SinkPolys, "SqMeters", procMask, MaskNoWater, outGDB, searchRadius = 10000)
calcKarstScore(KarstPolys, procMask, MaskNoWater, out_GDB, minDist = 500, maxDist = 10000, SinkScore)
calcLandscapeScore(FlowScore, KarstScore, LandscapeScore)

# Get Impact, Importance, and Priority Scores
# in_raList = [(hwResourceAreas,1)]
# calcImportanceScore(in_raList, MaskNoWater, hwResourceScore)
# calcImpactScore(LandscapeScore, SoilSensScore, ImpactScore_base, "NONE")
# calcImpactScore(LandscapeScore, SoilSensScore, ImpactScore_hw, hwResourceScore)

# list2k = [(hwRA2k,1)]
# calcImportanceScore(list2k, MaskNoWater, hwResourceScore2k)
# calcImpactScore(LandscapeScore, SoilSensScore, ImpactScore_hw2k, hwResourceScore2k)

# list10k = [(hwRA10k,1)]
# calcImportanceScore(list10k, MaskNoWater, hwResourceScore10k)
# calcImpactScore(LandscapeScore, SoilSensScore, ImpactScore_hw10k, hwResourceScore10k)

# listCombo = [(hwRA2k,1),(hwRA3k,1),(hwRA5k,1),(hwRA10k,1),(hwResourceAreas,1)]
# calcImportanceScore(listCombo, MaskNoWater, hwResourceScoreCombo)
# calcImpactScore(LandscapeScore, SoilSensScore, ImpactScore_hwCombo, hwResourceScoreCombo)

# list10kCombo = [(hwRA2k,1),(hwRA3k,1),(hwRA5k,1),(hwRA10k,1)]
# calcImportanceScore(list10kCombo, MaskNoWater, hwResourceScore10kCombo)
# calcImpactScore(LandscapeScore, SoilSensScore, ImpactScore_hw10kCombo, hwResourceScore10kCombo)

# calcPriorityScores(ImpactScore_hwCombo, consMask, restMask, mgmtMask, outGDB, "SLICE", 10, "hwCombo")
# calcPriorityScores(ImpactScore_hw10kCombo, consMask, restMask, mgmtMask, outGDB, "SLICE", 10, "hw10kCombo")

   
