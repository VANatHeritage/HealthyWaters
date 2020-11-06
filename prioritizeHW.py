# ---------------------------------------------------------------------------
# prioritizeHW.py
# Version: ArcPro / Python 3+
# Creation Date: 2020-07-06
# Last Edit: 2020-11-06
# Creator: Kirsten R. Hazler
#
# Summary: Functions for a watershed approach to prioritizing lands for conservation or restoration, with the purpose of maintaining documented "Healthy Waters", as well as for the ConservationVision Watershed Model.
#
# Adapted from the 2017 edition of the ConservationVision Watershed Model, and from information about the OpenNSPECT tool.
# For background references and formulas, see: 
# - Virginia ConservationVision Watershed Model, 2017 Edition (NHTR 18-16; 2018)
# - Technical Guide for OpenNSPECT, Version 1.1 (2012)
# - Predicting soil erosion by water: a guide to conservation planning with the revised universal soil loss equation (RUSLE) (USDA Agriculture Handbook 703; 1997)

# NOTE: Landcover used in these functions should be a hybrid NLCD/CCAP product. Where CCAP is coded 19 (unconsolidated shore), the NLCD data should be recoded from code 31 (barren land) to code 32.

# NOTE: To set up inputs/outputs and string a series of functions together, use a separate workflow script that imports the functions from this one.
# ---------------------------------------------------------------------------

# Import modules
import HelperPro
from HelperPro import *

def calcDW_PopServed():
   '''Calculates an estimate of the population served by drinking water intakes
   '''
   print("Nothing to see here yet, if ever.")

def makeLandcoverMasks(in_LC, out_GDB):
   '''From input land NLCD landcover, creates three processing masks: one for conservation, one for restoration, and one for stormwater management.
   
   Parameter:
   - in_LC: Input classified land cover raster, using standard NLCD land cover codes (updated with CCAP for code 32 = unconsolidated shore)
   - out_GDB: geodatabase for storing outputs
   '''
   
   # Set up query strings for SetNull function
   qryCons = "Value not in (32, 41, 42, 43, 52, 71, 90, 95)"
   qryRest = "Value not in (21, 31, 81, 82)"
   qryMgmt = "Value not in (22, 23, 24)"
   
   # Make masks
   print("Making conservation mask...")
   consMask = SetNull(in_LC, in_LC, qryCons)
   consMask.save(out_GDB + os.sep + "consMask")
   
   print("Making restoration mask...")
   restMask = SetNull(in_LC, in_LC, qryRest)
   restMask.save(out_GDB + os.sep + "restMask")
   
   print("Making stormwater management mask...")
   mgmtMask = SetNull(in_LC, in_LC, qryMgmt)
   mgmtMask.save(out_GDB + os.sep + "mgmtMask")
   
   return (consMask, restMask, mgmtMask)
   
def getTruncVals(in_Raster, in_Mask = "NONE", numSD = 3):
   '''Based on raster statistics, calculates lower and upper cutoff values to be used for rescaling purposes.
   
   Parameters:
   in_Raster: The input raster to be analyzed
   in_Mask: Mask raster used to define the portion of the input raster to be analyzed
   numSD: The number of standard deviations used to determine the cutoff values
   '''
   
   if in_Mask == "NONE":
      r = Raster(in_Raster)
   else:
      r = Con(Raster(in_Mask), Raster(in_Raster))
   rMin = r.minimum
   rMax = r.maximum
   rMean = r.mean
   rSD = r.standardDeviation
   TruncMin = max(rMin,(rMean - numSD*rSD))
   TruncMax = min(rMax,(rMean + numSD*rSD))
   
   return (TruncMin, TruncMax)

def calcSoilSensScore(in_SoilLoss, in_Runoff, out_GDB, nameTag = "", in_Mask = "NONE"):
   '''Creates a "Soil Sensitivity Score" raster, representing relative potential for impacts due to soil loss and rain runoff, on a scale from 1 (low sensitivity) to 100 (high sensitivity). 
   
   NOTE: The input rasters representing potential for soil loss and runoff should be based on a "worst case scenario" land cover type, e.g., bare soil. These should have been created using functions in the procSSURGO.py script.
   
   Parameters:
   - in_SoilLoss: input raster representing relative potential for soil loss under "worst case" land cover conditions
   - in_Runoff: input raster representing relative potential for runoff under "worst case" land cover conditions
   - out_GDB: geodatabase to store outputs
   - nameTag: a string to add to the output names
   - in_Mask: Mask raster used to define the processing area
   '''
   
   # Set processing environment
   if in_Mask != "NONE":
      arcpy.env.mask = in_Mask
   
   # Set up outputs
   soilLossScore = out_GDB + os.sep + "soilLoss_Score_%s"%nameTag
   runoffScore = out_GDB + os.sep + "runoff_Score_%s"%nameTag
   sensScore = out_GDB + os.sep + "soilSens_Score_%s"%nameTag

   # Get truncation values
   print("Calculating raster cutoff values...")
   (slTruncMin, slTruncMax) = getTruncVals(in_SoilLoss, in_Mask)
   (roTruncMin, roTruncMax) = getTruncVals(in_Runoff, in_Mask)

   # Rescale the SoilLoss raster
   print("Rescaling soil loss potential...")
   Fx = TfLinear ("", "", slTruncMin, 1, slTruncMax, 100) 
   slScore = RescaleByFunction(in_SoilLoss, Fx, 1, 100)
   # print("Saving...")
   slScore.save(soilLossScore)
   
   # Rescale the Runoff raster
   print("Rescaling runoff potential...")
   Fx = TfLinear ("", "", roTruncMin, 1, roTruncMax, 100) 
   roScore = RescaleByFunction(in_Runoff, Fx, 1, 100)
   print("Saving...")
   roScore.save(runoffScore)

   # Take the average of the rescaled values
   print("Calculating soil sensitivity score...")
   sens = (slScore + roScore)/2
   print("Saving...")
   
   sens.save(sensScore)
   
   print("Mission accomplished.")

def makeHdwtrsIndicator(in_FlowLines, in_Catchments, in_BoundPoly, in_Mask, out_Hdwtrs):
   '''Creates a "Headwaters Indicator" raster, representing presence in a headwater (1) or non-headwater (0) catchment. This is a component of the Landscape Position Score.
   
   NOTE: Flowlines and catchments are assumed to come from NHDPlus-HR, which includes fields to identify headwater streams and link them to their corresponding catchments. It assumes that the field indicating headwater status is already attached to the NHDPlus feature class. If this is not the case this needs to be done first.
   
   Parameters:
   - in_FlowLines: Input NHDPlus Flowlines (line features)
   - in_Catchments: Input NHDPlus Catchments (polygon features)
   - in_BoundPoly: Input polygon feature class delimiting the area of interest
   - in_Mask: Input raster used to define the processing area, cell size, and alignment
   - out_Hdwtrs: Output raster representing headwater status
   '''
   
   # Set environment variables
   arcpy.env.snapRaster = in_Mask
   arcpy.env.cellSize = in_Mask
   arcpy.env.mask = in_Mask
   
   scratchGDB = arcpy.env.scratchGDB

   # Select the catchments intersecting in_BoundPoly, and save them to a temp feature class
   print
   tmpCatch = scratchGDB + os.sep + "tmpCatch"
   print("Selecting catchments within area of interest...")
   arcpy.MakeFeatureLayer_management(in_Catchments, "catch_lyr")
   arcpy.SelectLayerByLocation_management("catch_lyr", "intersect", in_BoundPoly)
   print("Copying subset...")
   arcpy.CopyFeatures_management("catch_lyr", tmpCatch)
   
   # Attach the headwaters indicator field to the catchment subset, then rasterize
   fldID = "NHDPlusID"
   fldHead = "StartFlag"
   print("Joining headwaters indicator field to catchments...")
   arcpy.JoinField_management(tmpCatch, fldID, in_FlowLines, fldID, fldHead)
   print("Rasterizing...")
   PolyToRaster(tmpCatch, fldHead, in_Mask, out_Hdwtrs) 
   
   print("Mission complete.")
   
   return out_Hdwtrs

def calcFlowScore(in_FlowLength, out_FlowScore, in_Hdwtrs = "NONE", minDist = 50, maxDist = 500, discount = 0.9):
   '''Creates a "Flow Distance Score" raster, in which cells within a specified flow distance to water are scored 100, and cells farther than a specified flow distance are scored 1. A headwaters indicator raster may optionally be used to "discount" cells not within headwater catchments. This is a component of the Landscape Position Score.
   
   NOTE: The FlowLength raster must have been derived from an overland flow direction raster (e.g., provided by NHDPlus.) 
   
   Parameters:
   - in_FlowLength: Input raster representing the overland flow distance to water
   - out_FlowScore: Output raster in which flow lengths have been converted to scores
   - in_Hdwtrs: Input raster indicating whether cells are within a headwater catchment (1) or not (0), used to "discount" non-headwater values. Can be set to "NONE" if no discount is desired.
   - minDist: The flow distance threshold below which the (non-discounted) score is set to 100.
   - maxDist: The flow distance threshold above which the (non-discounted) score is set to 1.
   - discount: A value multiplied by the initial score to get the final score (ignored if no headwaters raster is specified). If the initial score is 100, but the cell is not in a headwater catchment and the discount value is 0.9, the final score will be 90.
   '''
   
   # Set environment variables
   if in_Hdwtrs != "NONE":
      arcpy.env.mask = in_Hdwtrs
   
   # Rescale the flow length raster to scores 
   print("Rescaling flow lengths to scores...")
   Fx = TfLinear ("", "", minDist, 100, maxDist, 1) 
   flowScore = RescaleByFunction(in_FlowLength, Fx, 100, 1)
   
   # Discount scores
   if in_Hdwtrs == "NONE":
      finScore = flowScore
   else:
      print("Discounting non-headwater scores...")
      finScore = Con(Raster(in_Hdwtrs)==0, discount*flowScore, flowScore)
   print("Saving...")
   finScore.save(out_FlowScore)
   
   return finScore

def calcKarstScore(in_KarstPolys, in_Mask, out_KarstScore, in_KarstPoints = "NONE", scratchGDB = arcpy.env.scratchGDB):
   '''Creates a "Karst Score" raster, representing prevalence of karst as a score from 0 (no karst nearby) to 100.
   
     Parameters:
   - in_KarstPolys: Polygons representing sinkhole features
   - in_Mask: Mask raster used to define the processing area, cell size, and alignment
   - out_KarstScore: Output raster with scores ranging from 0 to 100
   - in_KarstPoints: Points within sinkhole polygons. These should have been previously generated from the polygon features (see tech report for Watershed Model 2017 edition.) May be omitted for a simpler karst score based only on distance.
   - scratchGDB: An optional geodatabase for storing intermediate products
   '''
   # Create scratchGDB if needed
   if scratchGDB != arcpy.env.scratchGDB:
      createFGDB(scratchGDB)
   
   # Set environment variables
   arcpy.env.mask = in_Mask
   arcpy.env.snapRaster = in_Mask
   arcpy.env.cellSize = in_Mask
   
   # Set up intermediate outputs
   sink_KernDens = scratchGDB + os.sep + "sink_KernDens" # provide a default value if unspecified
   sink_DensityScore = scratchGDB + os.sep + "sink_DensityScore"
   sink_Raster = scratchGDB + os.sep + "sink_Raster"
   sink_EucDist = scratchGDB + os.sep + "sink_EucDist" 
   sink_DistanceScore = scratchGDB + os.sep + "sink_DistanceScore" 

   # Convert sink features to raster
   print("Converting sink features to raster...")
   PolyToRaster(in_KarstPolys, "OBJECTID", in_Mask, sink_Raster)

   # Get Euclidean Distance and Distance Score
   print("Getting Euclidean distance to sinks...")
   edist = EucDistance(sink_Raster, "", arcpy.env.cellSize)
   print("Saving...")
   edist.save(sink_EucDist)
   print("Converting distances to scores...")
   minDist = 500
   maxDist = 10000
   Fx = TfLinear ("", "", minDist, 100, maxDist, 0) 
   edistScore = RescaleByFunction(edist, Fx, 100, 0)
 
   if in_KarstPoints != "NONE":
      print("Saving...")
      edistScore.save(sink_DistanceScore)
      # Get Kernel Density and Density Score
      print("Getting kernel density of sink points...")
      searchRadius = 10000
      popFld = "NONE"
      kdens = KernelDensity(in_KarstPoints, popFld, in_Mask, searchRadius, "SQUARE_KILOMETERS", "DENSITIES", "PLANAR")
      print("Saving...")
      kdens.save(sink_KernDens)
      print("Converting densities to scores...")
      minDens = 0
      maxDens = 250
      Fx = TfLinear ("", "", minDens, 0, maxDens, 100) 
      kdensScore = RescaleByFunction(kdens, Fx, 0, 100)
      print("Saving...")
      kdensScore.save(sink_DensityScore)

      # Get final Karst Score
      print("Calculating final Karst Score...")
      combinedScore = CellStatistics([kdensScore, edistScore], "MEAN", "DATA")
      print("Saving...")
      combinedScore.save(out_KarstScore)
      return combinedScore
   
   else:
      print("Karst score is based only on Euclidean distance. Saving...")
      edistScore.save(out_KarstScore)
      return edistScore

def calcLandscapeScore(in_FlowScore, in_KarstScore, out_LandscapeScore):
   '''Creates a "Landscape Position Score" raster, representing relative importance to stream health based on position in the landscape. It is the maximum of the Karst Score and the Flow Distance Score.

   Parameters:
   - in_FlowScore: Input raster representing the Flow Distance Score
   - in_KarstScore: Input raster representing the Karst Score
   - out_LandscapeScore: Output raster representing the Landscape Position Score
   '''
   
   # Calculate score
   print("Calculating Landscape Position Score...")
   score = CellStatistics([in_FlowScore, in_KarstScore], "MAXIMUM", "DATA")
   print("Saving...")
   score.save(out_LandscapeScore)
   
   print("Mission accomplished.")
   return score
   
def calcImportanceScore(in_raList, in_Snap, out_Raster):
   '''Calculates an Importance Score, based on polygon features identifying areas impacting resources of interest (e.g., catchments for Healthy Waters sites, assessment zones for drinking water intakes, or a Stream Conservation Site delineation).
   
   TO DO (?): Add a weighting field for individual features (e.g., count of EOs in SCS, number served by drinking water sources.) Will then also need to rescale each input, or else require rescale prior to input.
   
   Parameters:
   - in_raList: Input list of tuples. Each tuple consists of a polygon feature class representing the impact areas (which may overlap) and the weight assigned to those features.
   - in_Snap: An input raster used to set output cell size and alignment
   - out_Raster: Output raster representing the importance for protection/restoration
   
   NOTE: Areas of the output raster not covered by any polygon will be null. This could be appropriate if you are ONLY interested in the drainage areas of specific resources (e.g., for Healthy Waters prioritization). If you want a non-null, non-zero value throughout the "background" cells of the study area (e.g., for a seamless statewide Watershed Model), you can add a bounding polygon to cover the entire area; typically it would make sense to give a weight of 1 to this layer.
   '''
   
   # Set environment
   scratchGDB = arcpy.env.scratchGDB
   
   procList = list()
   for t in in_raList:
      (polys, weight) = t
      nameTag = os.path.basename(polys)
      print("Working on %s..."%nameTag)
      outCount = scratchGDB + os.sep + "polyCounts_%s"%nameTag
      countRast = scratchGDB + os.sep + "countRast_%s"%nameTag
      weightRast = scratchGDB + os.sep + "weightRast_%s"%nameTag
      
      # Count the overlapping features
      print("Counting overlaps...")
      arcpy.CountOverlappingFeatures_analysis(polys, outCount)
      
      # Rasterize
      print("Rasterizing...")
      PolyToRaster(outCount, "COUNT_", in_Snap, countRast)
      
      # Multiply by weight
      if weight != 1:
         print("Weighting...")
         wtCt = weight*Raster(countRast)
         wtCt.save(weightRast)
      else:
         wtCt = countRast
      
      # Append to processing list
      procList.append(str(wtCt))
   
   # Get weighted sum of resources
   if len(procList) > 1:
      print("Calculating weighted sum of resources...")
      wtSum = CellStatistics(procList, "SUM", "DATA")
   else:
      wtSum = Raster(procList[0])
      
   # Rescale weighted sums to scores
   rMax = wtSum.maximum
   
   print("Rescaling to scores...")
   score = 100.0*wtSum/rMax
   
   print("Saving...")
   score.save(out_Raster)
   
   print("Mission complete.")
   return out_Raster

def calcImpactScore(in_LandscapeScore, in_SoilSensScore, out_Raster, in_ImportanceScore = "NONE"):
   '''Creates a raster representing Impact Importance Score, based on landscape position and soil sensitivity, and optionally weighted by a score based on downstream resources of interest that would potentially be impacted. 
   
   Parameters:
   - in_LandscapeScore: Input raster representing relative importance based on landscape position
   - in_SoilSensScore: Input raster representing relative importance based on soil sensitivity
   - out_Raster: The output raster representing either the Impact Score (if there is no input Importance Score) or the General Priority Score (if there is an input Importance Score used to adjust the Impact Score).
   - in_ImportanceScore: Input raster representing relative importance based on the number of resources of interest that could be impacted by changes at each location
   '''
   
   if in_ImportanceScore != "NONE":
      print("Calculating General Priority Score...")
      score = Raster(in_ImportanceScore)/100.0 * (CellStatistics([in_LandscapeScore, in_SoilSensScore], "MEAN", "DATA"))
   else:
      print("Calculating Impact Score"...")
      score = CellStatistics([in_LandscapeScore, in_SoilSensScore], "MEAN", "DATA")
      
   print("Saving...")
   score.save(out_Raster)
   
   print("Mission accomplished.")
   return out_Raster

def ScenarioScore(in_Case, in_WorstCase, in_BestCase, priorType, out_Score, in_Mask = "NONE"):
   '''Creates a raster representing a "Scenario Score", depending on how the values in the input raster compare to best- and worst-case scenarios for the same variable. 
   
   *** Not sure I will ever use this function.
   
   Parameters:
   - in_Case: Input raster representing the values of a particular variable of interest
   - in_WorstCase: Input raster representing the "worst case" scenario of the variable of interest
   - in_BestCase: Input raster representing the "best case" scenario of the variable of interest
   - priorType: Indicates whether the score is developed from a conservation (CONS) or restoration/stormwater management (REST) perspective
   - out_Score: Output raster representing a score for the variable of interest
   - in_Mask: Mask raster used to define the processing area
   '''
   
   # Set processing environment
   if in_Mask != "NONE":
      arcpy.env.mask = in_Mask
   
   # Make raster objects
   Case = Raster(in_Case)
   WorstCase = Raster(in_WorstCase)
   BestCase = Raster(in_BestCase)
   
   # Calculate
   if priorType == "CONS":
      print("Calculating scenario score for conservation...")
      score = 100.0*(WorstCase - Case)/(WorstCase - BestCase)
   else:
      print("Calculating scenario score for restoration or management...")
      score = 100.0*(Case - BestCase)/(WorstCase - BestCase)
   
   adjScore = Con(score > 100, 100, Con(score < 0, 0, score))
   adjScore.save(out_Score)

def calcPriorityScores(in_ImpactScore, in_ConsMask, in_RestMask, in_MgmtMask, out_GDB, rescale = "SLICE", slice = 10, nameTag = ""):
   '''Calculates priorities for conservation, restoration, and stormwater management, depending on landcover type.
   
   Parameters:
   - in_ImpactScore: Input raster representing potential impact (x importance)
   - in_ConsMask: Input raster representing lands that should get conservation priorities
   - in_RestMask: Input raster representing lands that should get restoration priorities
   - in_MgmtMask: Input raster representing lands that should get stormwater management priorities
   - out_GDB: Geodatabase to hold final outputs
   - rescale: Indicates whether to first rescale the Impact Score raster. Options: "SLICE" (to slice into specified number of quantiles), "STANDARD" (to do a standard linear rescale), or "NONE" (to use the raw impact scores).
   - slice: If the SLICE option is used for rescaling, the number of slices (i.e, quantiles)
   - nameTag: String to add as a suffix to standard output names
   '''
   
   # Set up outputs
   cPrior = out_GDB + os.sep + "consPriority_%s"%nameTag
   rPrior = out_GDB + os.sep + "restPriority_%s"%nameTag
   mPrior = out_GDB + os.sep + "mgmtPriority_%s"%nameTag
   bName = os.path.basename(in_ImpactScore)
   
   # Rescale the impact scores, if specified
   if rescale == "SLICE":
      print("Slicing impact scores into quantiles...")
      score = Slice(in_ImpactScore, slice, "EQUAL_AREA", 1)
      outPath = out_GDB + os.sep + bname + "_slice"
      score.save(outPath)
   elif rescale == "STANDARD":
      print("Calculating minimum and maximum impact scores...")
      r = Raster(in_ImpactScore)
      rMin = r.minimum
      rMax = r.maximum
      print("Rescaling...")
      Fx = TfLinear ("", "", rmin, 1, rmax, 100) 
      score = RescaleByFunction(r, Fx, 1, 100)
      outPath = out_GDB + os.sep + bname + "_rscl"
      score.save(outPath)
   else:
      score = Raster(in_ImpactScore)
      
   # Create priority rasters
   print("Creating conservation priority raster...")
   cons = Con(in_ConsMask, score)
   cons.save(cPrior)
   
   print("Creating restoration priority raster...")
   rest = Con(in_RestMask, score)
   rest.save(rPrior)
   
   print("Creating stormwater management priority raster...")
   mgmt = Con(in_MgmtMask, score)
   mgmt.save(mPrior)
   
   print("Mission accomplished.")
   return (cons, rest, mgmt)  
