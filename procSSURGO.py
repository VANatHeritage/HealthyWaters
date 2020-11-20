# ---------------------------------------------------------------------------
# procSSURGO.py
# Version: ArcPro / Python 3+
# Creation Date: 2020-05-19
# Last Edit: 2020-11-19
# Creator: Kirsten R. Hazler
#
# Summary: Functions for processing SSURGO data and producing rasters representing soil conditions, as well as functions inspired by OpenNSPECT software to produce rasters representing interactions between soils, topography, and land cover.
#
# Adapted from toolbox tools and scripts used to produce the 2017 edition of the ConservationVision Watershed Model, and from information about the OpenNSPECT tool.
# For background references and formulas, see: 
# - Virginia ConservationVision Watershed Model, 2017 Edition (NHTR 18-16; 2018)
# - Technical Guide for OpenNSPECT, Version 1.1 (2012)
# - Predicting soil erosion by water: a guide to conservation planning with the revised universal soil loss equation (RUSLE) (USDA Agriculture Handbook 703; 1997)

# NOTE: Landcover used in these functions should be a hybrid NLCD/CCAP product. Where CCAP is coded 19 (unconsolidated shore), the NLCD data should be recoded from code 31 (barren land) to code 32.
# ---------------------------------------------------------------------------

# Import modules
import HelperPro
from HelperPro import *

def SSURGOtoRaster(in_gdbList, in_Fld, in_Snap, out_Raster):
   '''From one or more gSSURGO geodatabases, creates a raster representing values from a specified field in the MUPOLYGON feature class. 
   
   Parameters:
   in_gdbList: List of gSSURGO geodatabases containing added attributes
   in_Fld: field in MUPOLYGON feature class used to determine output raster values
   in_Snap: Input raster that determines output coordinate system, processing extent, cell size, and alignment
   out_Runoff: Output raster representing runoff score
   '''
   
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Specify scratch location
   scratchGDB = arcpy.env.scratchGDB
   
   # Empty list to contain raster paths
   rasterList = []
   
   # Work through loop converting polygons to rasters
   for gdb in in_gdbList:
      try:
         inPoly = gdb + os.sep + "MUPOLYGON"
         bname = os.path.basename(gdb).replace(".gdb","")
         print("Working on %s" %bname)
         outRast = scratchGDB + os.sep + bname
         PolyToRaster(inPoly, in_Fld, in_Snap, outRast)
         rasterList.append(outRast)
      except:
         print("Failed to rasterize %s" %bname)
   
   print("Finalizing output and saving...")
   finRast = CellStatistics(rasterList, "MAXIMUM", "DATA")
   finRast.save(out_Raster)
   
   print("Mission complete.")

def RunoffScore_vec(in_GDB):
   '''To the muaggatt table and the MUPOLYGON feature class, adds a field called "runoffScore", with scores from 0 (no runoff) to 100 (high runoff).
   Scores are based on drainage classes per Table 2, page 27 in NHTR 18-16.
   
   This function modifies the input data by adding new fields. It does not modify existing fields.
   Parameters:
   - in_GDB: input gSSURGO geodatabase
   '''

   # Specify some variables
   muaggatt = in_GDB + os.sep + "muaggatt"
   mupolygon = in_GDB + os.sep + "MUPOLYGON"
   bname = os.path.basename(in_GDB)
   print("Working on %s" %bname) 
   
   # Create a field in the muaggatt table to store the runoff score value, and calculate
   print("Adding runoffScore field...")
   arcpy.AddField_management(muaggatt, "runoffScore", "SHORT")
   codeblock = '''def score(drainclass):
      # Create a dictionary relating drainage classes to scores
      s = dict()
      s["Very poorly drained"] = 100
      s["Poorly drained"] = 90
      s["Somewhat poorly drained"] = 75
      s["Moderately well drained"] = 50
      s["Well drained"] = 25
      s["Somewhat excessively drained"] = 10
      s["Excessively drained"] = 0
      
      # Deal with nulls. Most nulls are either open water or developed. 
      # Open water doesn't matter since it will be masked out in the end. 
      # Developed areas tend to have high runoff, so assign score of 100.
      try: 
         score = s[drainclass]
      except:
         score = 100 
      
      return score
   '''
   expression = "score(!drclassdcd!)" 
   print("Calculating runoffScore field...")
   arcpy.CalculateField_management (muaggatt, "runoffScore", expression, 'PYTHON', codeblock)

   # Process: Join Runoff Score to MUPOLYGON
   # First check if field exists (due to prior processing) and delete if so
   fldList = arcpy.ListFields(mupolygon) 
   fldNames = [f.name for f in fldList]
   if "runoffScore" in fldNames:
      print("Deleting existing runoffScore field in MUPOLYGON...")
      arcpy.DeleteField_management (mupolygon, "runoffScore")
   print("Joining runoffScore field to MUPOLYGON...")
   arcpy.JoinField_management(mupolygon, "MUKEY", muaggatt, "mukey", "runoffScore")
   
   print("Mission complete for %s." %bname)

   return

def ErosionScore_vec(in_GDB):
   '''To the MUPOLYGON feature class, adds a field called "KFACTWS_DCD", containing the K-factor values extracted from gSSURGO. Also adds a field called "erosionScore", with scores from 0 (low erodibility) to 100 (high erodibility), derived from the K-factor value provided by gSSURGO. 
   
   This function modifies the input geodatabase by adding new tables and fields. It does not modify existing fields.
   
   Parameters:
   - in_GDB: input gSSURGO geodatabase
   
   K-factor values range from 0.02 to 0.69*. Erosion scores are derived as described on page 6 in NHTR 18-16, except that the maximum K-factor value of 0.69, not 0.55, obtains the maximum erosion score.
   
   * per https://dec.vermont.gov/sites/dec/files/wsm/stormwater/docs/StormwaterConstructionDischargePermits/sw_9020_Erodibility_%20Guidance.pdf

   IMPORTANT: Prior to running this function, new data must be created within the input geodatabase, using a tool in the Soil Data Development Toolbox. Tools in this toolbox can only be run from within ArcMap (not ArcPro) and I haven't figured out a way to automate this with a script, so you need to do it manually.
   
   The Soil Data Development Toolbox must be added to ArcToolbox in ArcMap, and is available from https://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/home/?cid=nrcs142p2_053628#tools.
   
   TO CREATE THE DATA NEEDED FOR THIS FUNCTION:
   - Within ArcMap, add the MUPOLYGON feature class as a layer. 
     - NOTE: If you will be working on data from multiple databases, it is recommended that you rename the layer in the map (e.g., MUPOLYGON_VA for the data from Virginia). Alternatively, remove the layer once you are done with it, before adding the next one.
   - From the Soil Data Development Toolbox, gSSURGO Mapping Toolset, open the "Create Soil Map" tool
   - In the tool, set the following parameters:
     - Map Unit Layer: MUPOLYGON [or renamed layer]
     - SDV Folder = "Soil Erosion Factors"
     - SDV Attribute = "K Factor, Whole Soil"
     - Aggregation Method = "Dominant Condition"
     - Top Depth (cm) = "0"
     - Bottom Depth (cm) = "10"
   - Run the tool. A new layer symbolized on the K-factor will appear.
   - Repeat as needed for MUPOLYGON data from different databases. 
   - Close ArcMap prior to attempting to run this function.
   
   The run of the above tool modifies the geodatabase by creating new tables with the prefix "SDV_". It does not modify existing tables.
   
   Given the above parameters, it creates a table named SDV_KfactWS_DCD_0to10, in which the field named KFACTWS_DCD contains the K-factor. If this is not the case, the function will fail.
   '''

   # Set up some variables
   mupolygon = in_GDB + os.sep + "MUPOLYGON"
   kfactTab = in_GDB + os.sep + "SDV_KfactWS_DCD_0to10"
   kfactFld = "KFACTWS_DCD"
   kMin = 0.02
   kMax = 0.69
   bname = os.path.basename(in_GDB)
   print("Working on %s" %bname) 
   
   # For some reason, the K-factor field created by the SSURGO toolbox is a string. 
   # Convert to double since this is needed for correct rasterization later.
   print("Converting string to double...")
   arcpy.AddField_management(kfactTab, "kFactor", "DOUBLE")
   expression = "float(!%s!)" %kfactFld
   arcpy.CalculateField_management (kfactTab, "kFactor", expression, 'PYTHON')
   kfactFld = "kFactor"
   
   # Process: Join K-factor value to MUPOLYGON
   # First check if field exists (due to prior processing) and delete if so
   fldList = arcpy.ListFields(mupolygon) 
   fldNames = [f.name for f in fldList]
   if kfactFld in fldNames:
      print("Deleting existing K-factor field in MUPOLYGON...")
      arcpy.DeleteField_management (mupolygon, kfactFld)
   print("Joining K-factor field to MUPOLYGON...")
   arcpy.JoinField_management(mupolygon, "MUKEY", kfactTab, "MUKEY", kfactFld)
   
   # Replace nulls in the K-factor field with the value 0.30, per the OpenNSPECT Technical Guide.
   print("Replacing nulls in K-factor field...")
   codeblock = '''def replaceNulls(fld):
      if fld == None:
         val = 0.3
      else:
         val = fld
      return val
   '''
   expression = "replaceNulls(!%s!)" %kfactFld
   arcpy.CalculateField_management (mupolygon, kfactFld, expression, 'PYTHON', codeblock)
   
   # Create a field in MUPOLYGON to store the erosion score value, and calculate
   print("Adding erosionScore field...")
   arcpy.AddField_management(mupolygon, "erosionScore", "SHORT")
   
   print("Calculating erosionScore field...")
   codeblock = '''def score(kfact, minThresh, maxThresh):
      if float(kfact) < minThresh:
         score = 0
      elif float(kfact) > maxThresh:
         score = 100
      else:
         score = 100*(float(kfact) - minThresh)/(maxThresh - minThresh)
      return score
   '''
   expression = "score(!%s!,%s, %s)" %(kfactFld, kMin, kMax)
   arcpy.CalculateField_management (mupolygon, "erosionScore", expression, 'PYTHON', codeblock)
   
   print("Mission complete for %s." %bname)

   return

def HydroGrp_vec(in_GDB):
   '''To the MUPOLYGON feature class, adds a field called "HYDROLGRP_DCD", containing the Hydrologic Soil Groups extracted from gSSURGO. Values range from A to D (with some compound classes possible, e.g., A/D). Also adds a field called "HydroGrpNum", which contains a numeric, simplified version of the hydrologic groups in which there are no compound groups and no nulls.
  
   This function modifies the input geodatabase by adding new tables and fields. It does not modify existing fields.
   
   Parameters:
   - in_GDB: input gSSURGO geodatabase
   
   Per OpenNSPECT guidance, numeric values for the groups are assigned as follows:
   - A = 1
   - B = 2
   - C = 3
   - D = 4
   
   Compound values (e.g., A/D) are assigned the latter group. Null values are assumed to be group D. 
   
   IMPORTANT: Prior to running this function, new data must be created within the input geodatabase, using a tool in the Soil Data Development Toolbox. Tools in this toolbox can only be run from within ArcMap (not ArcPro) and I haven't figured out a way to automate this with a script, so you need to do it manually.
   
   The Soil Data Development Toolbox must be added to ArcToolbox in ArcMap, and is available from https://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/home/?cid=nrcs142p2_053628#tools.
   
   TO CREATE THE DATA NEEDED FOR THIS FUNCTION:
   - Within ArcMap, add the MUPOLYGON feature class as a layer. 
     - NOTE: If you will be working on data from multiple databases, it is recommended that you rename the layer in the map (e.g., MUPOLYGON_VA for the data from Virginia). Alternatively, remove the layer once you are done with it, before adding the next one.
   - From the Soil Data Development Toolbox, gSSURGO Mapping Toolset, open the "Create Soil Map" tool
   - In the tool, set the following parameters:
     - Map Unit Layer: MUPOLYGON [or renamed layer]
     - SDV Folder = "Soil Qualities and Features"
     - SDV Attribute = "Hydrologic Soil Group"
     - Aggregation Method = "Dominant Condition"
   - Run the tool. A new layer symbolized on the Hydrologic Soil Group will appear.
   - Repeat as needed for MUPOLYGON data from different databases. 
   - Close ArcMap prior to attempting to run this function.
   
   The run of the above tool modifies the geodatabase by creating new tables with the prefix "SDV_". It does not modify existing tables.
   
   Given the above parameters, it creates a table named SDV_HydrolGrp_DCD, in which the field named HYDROLGRP_DCD contains the Hydrologic Soil Group code. If this is not the case, the function will fail.
   '''

   # Set up some variables
   mupolygon = in_GDB + os.sep + "MUPOLYGON"
   hydroTab = in_GDB + os.sep + "SDV_HydrolGrp_DCD"
   hydroFld = "HYDROLGRP_DCD"
   bname = os.path.basename(in_GDB)
   print("Working on %s" %bname) 
   
   # Process: Join Hydrologic Group value to MUPOLYGON
   # First check if field exists (due to prior processing) and delete if so
   fldList = arcpy.ListFields(mupolygon) 
   fldNames = [f.name for f in fldList]
   if hydroFld in fldNames:
      print("Deleting existing hydrologic group field in MUPOLYGON...")
      arcpy.DeleteField_management (mupolygon, hydroFld)
   print("Joining Hydrologic Group field to MUPOLYGON...")
   arcpy.JoinField_management(mupolygon, "MUKEY", hydroTab, "MUKEY", hydroFld)
   
   # Create and calculate a field in MUPOLYGON to store numeric version of hydrologic group, and calculate
   print("Adding numeric field for hydrologic group...")
   arcpy.AddField_management(mupolygon, "HydroGrpNum", "SHORT")
   
   print("Calculating HydroGrpNum field...")
   codeblock = '''def grpNum(fld):
      d = dict()
      d["A"] = 1
      d["B"] = 2
      d["C"] = 3
      d["D"] = 4
      
      if fld == None:
         key = "D"
      elif len(fld) > 1:
         key = fld[-1]
      else:
         key = fld   
      
      val = d[key]
      
      return val
   '''
   expression = "grpNum(!%s!)" %hydroFld
   arcpy.CalculateField_management (mupolygon, "HydroGrpNum", expression, 'PYTHON', codeblock)
   
   print("Mission complete for %s." %bname)

   return

def SlopeTrans(in_Raster, inputType, transType, out_Trans, out_Slope, zfactor = 1):
   '''From a raster representing slope, creates a new raster representing a transformed representation of slope, depending on the transformation type (transType) specified. 
   
   The transformation types that may be specified are:
   - TRUNCLIN: A truncated linear function. Flat and nearly level slopes less than or equal to 1 degree (~2%) are scored 0, extreme slopes greater than or equal to 30 degrees (~58%) are scored 100, and values are scaled linearly in between the threshold values. This is a modification of the transformation used to derived the Slope Score in the 2017 edition of the ConservationVision Watershed Model.
   - TRUNCSIN: A truncated sine function. The sine of the angle is multiplied by 200 to get the score, but values above 100 are truncated, which happens at 30 degrees.
   - RUSLE: A stepwise sine function used to derive the slope steepness factor (S) in the RUSLE equation. (See equations 4-4 and 4-5 on page 107 of the RUSLE handbook.)

   Parameters:
   - in_Raster: input raster representing slope or elevation
   - inputType: indicates whether the input raster is slope in degrees (DEG or DEGREES), slope as percent grade (PERC or PERCENT), or elevation (ELEV or ELEVATION)
   - transType: the transformation function used to produce the output raster
     permitted values: TRUNCLIN, TRUNCSIN, RUSLE
   - out_Trans: output raster representing transformed slope
   - out_Slope: output raster representing slope as percent grade (ignored if input is a slope raster)
   - zfactor: Number of ground x,y units in one surface z-unit (ignored if input is a slope raster)
   '''
   
   # Make sure user entered valid parameters, and report what they are.   
   if inputType in ("DEG", "DEGREES"):
      slopeType = "DEGREES"
      print("Input is slope in degrees.")
   elif inputType in ("PERC", "PERCENT"):
      slopeType = "PERCENT"
      print("Input is slope as percent grade.")
   elif inputType in ("ELEV", "ELEVATION"):
      slopeType = "PERCENT"
      print("Input is elevation.")
   else:
      print("Input type specification is invalid. Aborting.")
      sys.exit()
      
   if transType == "TRUNCLIN":
      print("Appying the truncated linear transformation.")
   elif transType == "TRUNCSIN":
      print("Applying the truncated sine transformation.")
   elif transType == "RUSLE":
      print("Applying the RUSLE transformation to get the S-factor.")
   else:
      print("Transformation specification is invalid. Aborting.")
      sys.exit()
      
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Set scratch output location
   scratchGDB = arcpy.env.scratchGDB
   
   # Identify the slope raster or create it if necessary
   if inputType in ("ELEV", "ELEVATION"):
      print("Calculating slope from elevation...")
      in_Slope = Slope(in_Raster, "PERCENT_RISE", zfactor) 
      in_Slope.save(out_Slope)
   else:   
      in_Slope = Raster(in_Slope)
   
   if transType == "TRUNCLIN":
   # Set flat and nearly level slopes (LTE 1 degree) to 0. Set extreme slopes (GTE 30 degrees) to 100. Use linear function to scale between those values.
      minSlope = 1.0
      maxSlope = 30.0
      if slopeType == "PERCENT":
         print("Calculating score...")
         minSlope = 100*math.tan(minSlope*math.pi/180)
         maxSlope = 100*math.tan(maxSlope*math.pi/180)
         outRaster = Con(in_Slope <= minSlope, 0, Con((in_Slope > maxSlope), 100, 100 * (in_Slope - minSlope) / (maxSlope - minSlope)))
      else: 
         print("Calculating score...")
         outRaster = Con(in_Slope <= minSlope, 0, Con((in_Slope > maxSlope), 100, 100 * (in_Slope - minSlope) / (maxSlope - minSlope)))
   
   elif transType == "TRUNCSIN":
   # Take the sine, multiply by 200, and integerize. Upper values are truncated at 100 (which happens at 30 degrees).
      if slopeType == "PERCENT":
         print("Converting percent grade to radians and calculating score...")
         outRaster = Min(100, Int(0.5 + 200*Sin(ATan(in_Slope/100))))
      else: 
         print("Converting degrees to radians and calculating score...")
         outRaster = Min(100, Int(0.5 + 200*Sin(in_Slope * math.pi/180.0)))
         
   else:
   # Use RUSLE transformation equations
      inflect = 9.0
      if slopeType == "PERCENT":
         print("Converting percent grade to radians and calculating S-factor...")
         outRaster = Con(in_Slope < inflect, (10.8*(Sin(ATan(in_Slope/100))) + 0.03), (16.8*(Sin(ATan(in_Slope/100))) - 0.50))
      else: 
         inflect = math.atan(inflect/100)*180/math.pi
         print("Converting degrees to radians and calculating S-factor...")
         outRaster = Con(in_Slope < inflect, (10.8*(Sin(in_Slope * math.pi/180.0)) + 0.03), (16.8*(Sin(in_Slope * math.pi/180.0)) - 0.50))
      
   print("Saving output...")
   outRaster.save(out_Trans)
   
   print("Mission complete")
   
   return

def SoilSensitivity(in_runoffScore, in_erosionScore, in_SlopeScore, out_SoilSens):
   '''From rasters representing scores for slope, runoff potential, and erosion potential, creates a raster representing soil sensitivity, ranging from 0 (low sensitivity) to 100 (high sensitivity; i.e. where land use practices will have the most impact, for better or worse). This is the Soil Sensitivity Score from the Watershed Model. Inputs must have been first generated by previous functions to produce the input rasters. 
   
   This functions assumes all inputs are in the same coordinate system and properly aligned with each other.

   Parameters:
   - in_RunoffScore: input raster representing runoff score
   - in_ErosionScore: input raster representing erosion score
   - in_SlopeScore: input raster representing slope score
   - out_SoilSens: output raster representing soil sensitivity
   '''
   
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Calculate soil sensitivity as average of three inputs, integerized
   print("Calculating soil sensitivity score...")
   sens = Int(0.5 + (in_RunoffScore + in_ErosionScore + in_SlopeScore)/float(3))
   
   print("Saving output...")
   sens.save(out_SoilSens)
   
   print("Mission complete.")
   
def soilLoss_RKS(in_Rfactor, in_Kfactor, in_Sfactor, out_RKS):
   '''Multiplies the rasters representing three of the factors in the Revised Universal Soil Loss Equation (RUSLE), to produce a relative measure of the propensity for soil loss. Does not include the cover management (C), slope length (L), or the  supporting practices (P) factors. Inputs must have been first generated by previous functions to produce the input rasters. 
   
   NOTE: The output can be multiplied by the year-specific C-factor (which depends on land cover) to obtain a relative measure of soil loss propensity. The output can be multiplied by a constant C-factor to obtain best-case and worst-case scenarios.
   
   This functions assumes all inputs are in the same coordinate system and properly aligned with each other.

   Parameters:
   - in_Rfactor: input raster representing the rainfall/runoff erosivity factor
   - in_Kfactor: input raster representing the soil erodibility factor
   - in_Sfactor: input raster representing the slope steepness factor
   - out_SoilSens: output raster representing soil sensitivity
   '''
   
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Calculate propensity for soil loss by multiplying the factors
   print("Calculating propensity for soil loss...")
   R = Raster(in_Rfactor)
   K = Raster(in_Kfactor)
   S = Raster(in_Sfactor)
   RKS = R*K*S
   
   print("Saving output...")
   RKS.save(out_RKS)
   
   print("Mission complete.")

def soilLoss_RKSC(in_RKS, in_Cfact, out_RKSC):
   '''Produces a raster representing relative soil loss, based on the RUSLE R-, K-, S-, and C-factors.
   
   Parameters:
   - in_Raster: input raster respresenting product of the RUSLE factors RKS
   - in_Cfact: input raster or constant (float) representing the RUSLE C-factor
   - out_RKSC: output raster respresenting product of the RUSLE factors RKSC
   '''
   
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Set up some variables
   in_RKS = Raster(in_RKS)
   try:
      in_Cfact = Raster(in_Cfact)
   except:
      pass
   
   # Perform calculation
   print("Multiplying RKS by C-factor...")
   RKSC = in_RKS*in_Cfact
   print("Saving...")
   RKSC.save(out_RKSC)
   
   print("Mission accomplished.")

def SedYld(in_Raster, in_CurvNum, nameTag, in_Slope, out_GDB, in_Cfact = "NONE", sdrType = "STD", cellArea = 0.0001):
   '''Produces a raster representing the annual sediment yield.
   
   NOTE: The "standard" calculation for Sediment Delivery Ratio SDR is from the OpenNSPECT tech manual. I also tracked down the original paper from 1977. The equation was developed for a specific area and it is highly questionable that it should be applied anywhere else. I'm also not sure I'm using percent slope correctly to obtain ZL, the relief-length ratio. Because of my doubts about the whole thing, I developed a much simpler equation for a proxy "alternate" SDR. I don't assume any particular units can be assigned to the final sediment yield; I view both RKSC (the product of the RUSLE soil loss factors) and the final sediment yield to be relative measures only. I also left out the L-factor in RUSLE soil loss equation b/c it is difficult to calculate and maybe (probably?) not worth it.
   
   This function assumes all inputs are in the same coordinate system and properly aligned with each other.

   Parameters:
   - in_Raster: input raster respresenting product of the RUSLE factors, RKSC or RKS
   - in_CurvNum: input raster or constant (integer) representing the SCS curve number
   - nameTag: tag to add to basenames (land cover year or a scenario-based tag)
   - in_Slope: input raster representing percent slope
   - out_GDB: geodatabase to store outputs
   - in_Cfact: input raster or constant (float) representing the RUSLE C-factor. Enter "NONE" if in_Raster is RKSC (i.e., C-factor already included)
   - sdrType: Type of SDR to calculate: STD (standard) or ALT (alternate)
   - cellArea: area of cells in Curve Number raster, in square kilometers; ignored if using alternate method for SDR calculation
   '''
   
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Set up some variables
   out_RKSC = out_GDB + os.sep + "RKSC_%s" %nameTag
   if sdrType == "STD":
      out_SDR = out_GDB + os.sep + "SDR_%s" %nameTag
      out_SedYld = out_GDB + os.sep + "SedYld_%s" %nameTag
   else:
      out_SDR = out_GDB + os.sep + "altSDR_%s" %nameTag
      out_SedYld = out_GDB + os.sep + "altSedYld_%s" %nameTag

   try:
      in_CurvNum = Raster(in_CurvNum)
   except:
      pass
      
   in_Slope = Raster(in_Slope)
   in_Raster = Raster(in_Raster)
   
   # Perform calculations
   if in_Cfact == "NONE":
      print("Input raster is RKSC...")
      RKSC = in_Raster
   else:
      print("Input raster is RKS; multiplying by C-factor...")
      try:
         in_Cfact = Raster(in_Cfact)
      except:
         pass
      RKSC = in_Raster*in_Cfact
      print("Saving...")
      RKSC.save(out_RKSC)
   
   if sdrType == "STD":
      print("Calculating standard sediment delivery ratio...")
      print("Calculating constant Alpha...")
      Alpha = 1.366*10**(-11)
      
      print("Calculating drainage area factor...")
      D = cellArea**(-0.0998)
      
      print("Calculating slope factor...")
      Z = (in_Slope/100000.0)**0.3629 
      
      print("Calculating curve number factor...")
      N = in_CurvNum**5.444 # This may be a raster or a constant depending on input type
       
      print("Calculating sediment delivery ratio...")
      SDR = Alpha*D*Z*N
    
   else:
      print("Calculating alternate sediment delivery ratio...")
      # Adjust slope values prior to multiplying
      adjSlope = Con(in_Slope > 100, 1.0, in_Slope/100.0)
      SDR = adjSlope*in_CurvNum/100.0
      
   print("Saving...")
   SDR.save(out_SDR)
    
   print("Calculating sediment yield...")
   sedYld = RKSC*SDR
   print("Saving...")
   sedYld.save(out_SedYld)
   
   print("Mission accomplished.")  

def coeffNSPECT(in_LC, coeffType, out_Coeff):
   '''From an input land cover raster, creates a new raster representing the NSPECT coefficient type specified (coeffType). Coefficient values are from the OpenNSPECT Technical Guide. The land cover codes in that table are CCAP codes, so assignments in this function are to the equivalent NLCD codes. 
   
   The coefficients that may be specified are:
   - CFACT: The cover factor (C-Factor in the RUSLE equation; a unitless ratio)
   - NPOLL: Nitrogen pollution factor (mg/L)
   - PPOLL: Phosphorus pollution factor (mg/L)
   - SPOLL: Suspended solids pollution factor (mg/L)
   
   C-factor values are assigned to land cover classes as specified in Table 4, page 22 of the OpenNSPECT Technical Guide. The pollution coefficients are specified in Appendix A, pages 42-43.
   
   This function modifies the input land cover attribute table, by adding and calculating a new field to store the desired coefficients.

   Parameters:
   - in_LC: Input classified land cover raster, using standard NLCD land cover codes (updated with CCAP for code 32 = unconsolidated shore)
   - coeffType: The coefficient set used to produce the output
   - out_Coeff: Output raster representing specified coefficient values
   '''
   
   # Make sure user entered valid parameters, and report what they are.   
   if coeffType not in ("CFACT", "NPOLL", "PPOLL", "SPOLL"):
      print("Input coefficient type specification is invalid. Aborting.")
      sys.exit()
   
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Initialize empty data dictionary
   d = dict()
   
   if coeffType == "NPOLL":
      fldName = "Nitrogen"
      msg = "Adding field to store nitrogen pollution values..."
      # Nitrogen pollution dictionary
      d[11] = 0.00
      d[21] = 1.25
      d[22] = 1.77
      d[23] = 2.29
      d[24] = 2.22
      d[31] = 0.97
      d[32] = 0.97
      d[41] = 1.25
      d[42] = 1.25
      d[43] = 1.25
      d[52] = 1.25
      d[71] = 1.25
      d[81] = 2.48
      d[82] = 2.68
      d[90] = 1.10
      d[95] = 1.10
   
   elif coeffType == "PPOLL":
      fldName = "Phosphorus"
      msg = "Adding field to store phosphorus pollution values..."
      # Phosphorus pollution dictionary
      d[11] = 0.00
      d[21] = 0.05
      d[22] = 0.18
      d[23] = 0.30
      d[24] = 0.47
      d[31] = 0.12
      d[32] = 0.12
      d[41] = 0.05
      d[42] = 0.05
      d[43] = 0.05
      d[52] = 0.05
      d[71] = 0.05
      d[81] = 0.48
      d[82] = 0.42
      d[90] = 0.20
      d[95] = 0.20   
   
   elif coeffType == "SPOLL":
      fldName = "Solids"
      msg = "Adding field to store suspended solids pollution values..."
      # Suspended solids pollution dictionary
      d[11] = 0.00
      d[21] = 11.10
      d[22] = 19.10
      d[23] = 27.00
      d[24] = 71.00
      d[31] = 70.00
      d[32] = 70.00
      d[41] = 11.10
      d[42] = 11.10
      d[43] = 11.10
      d[52] = 11.10
      d[71] = 55.30
      d[81] = 55.30
      d[82] = 107.00
      d[90] = 19.00
      d[95] = 19.00  
   
   else:
      fldName = "Cfactor"
      msg = "Adding field to store C-factor values..."
      # C-factor dictionary
      d[11] = 0.000
      d[21] = 0.005
      d[22] = 0.030
      d[23] = 0.010
      d[24] = 0.000
      d[31] = 0.700
      d[32] = 0.500
      d[41] = 0.009
      d[42] = 0.004
      d[43] = 0.007
      d[52] = 0.014
      d[71] = 0.120
      d[81] = 0.005
      d[82] = 0.240
      d[90] = 0.003
      d[95] = 0.003
   
   # Create and calculate a coefficient field in the land cover attribute table
   print(msg)
   arcpy.AddField_management(in_LC, fldName, "DOUBLE")
   
   print("Calculating field...")
   codeblock = '''def coeff(code, dic):
      try: 
         val = dic[code]
      except:
         val = 0
      return val
      '''
   expression = "coeff(!VALUE!, %s)" %d
   arcpy.CalculateField_management (in_LC, fldName, expression, 'PYTHON', codeblock)
   
   # Create a new raster from the coefficient field, and save
   print("Creating raster...")
   outRaster = Lookup(in_LC, fldName)
   
   print("Saving output...")
   outRaster.save(out_Coeff)
   
   print("Mission complete.")
 
def curvNum(in_LC, in_HydroGrp, out_CN):
   '''Given input land cover and hydrologic group, produces output raster representing runoff curve numbers.
   
   Curve numbers are assigned to combinations of land cover and soil types as specified in Table 1, page 6 of the OpenNSPECT Technical Guide. 
   
   This function modifies the input land cover attribute table, by adding and calculating a new field to store the curve numbers

   Parameters:
   - in_LC: Input classified land cover raster, using standard NLCD land cover codes (updated with CCAP for code 32 = unconsolidated shore), OR an integer representing a desired land cover class
   - in_HydroGrp: Input raster representing hydrologic groups (integer values must range from 1 = A to 4 = D)
   - out_CN: Output raster representing runoff curve numbers
   '''
   
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Set scratch output location
   scratchGDB = arcpy.env.scratchGDB
   
   # Initialize empty data dictionaries
   dictA = dict()
   dictB = dict()
   dictC = dict()
   dictD = dict()
   m = dict()
   
   # Populate dictionary for hydro group A, then append to list
   dictA[11] = 0
   dictA[21] = 49
   dictA[22] = 61
   dictA[23] = 77
   dictA[24] = 89
   dictA[31] = 77
   dictA[32] = 0
   dictA[41] = 30
   dictA[42] = 30
   dictA[43] = 30
   dictA[52] = 30
   dictA[71] = 30
   dictA[81] = 39
   dictA[82] = 67
   dictA[90] = 0
   dictA[95] = 0
   m["A"] = dictA
   
   # Populate dictionary for hydro group B
   dictB[11] = 0
   dictB[21] = 69
   dictB[22] = 75
   dictB[23] = 85
   dictB[24] = 92
   dictB[31] = 86
   dictB[32] = 0
   dictB[41] = 55
   dictB[42] = 55
   dictB[43] = 55
   dictB[52] = 48
   dictB[71] = 58
   dictB[81] = 61
   dictB[82] = 78
   dictB[90] = 0
   dictB[95] = 0
   m["B"] = dictB
   
   # Populate dictionary for hydro group C
   dictC[11] = 0
   dictC[21] = 79
   dictC[22] = 83
   dictC[23] = 90
   dictC[24] = 94
   dictC[31] = 91
   dictC[32] = 0
   dictC[41] = 70
   dictC[42] = 70
   dictC[43] = 70
   dictC[52] = 65
   dictC[71] = 71
   dictC[81] = 74
   dictC[82] = 85
   dictC[90] = 0
   dictC[95] = 0
   m["C"] = dictC
   
   # Populate dictionary for hydro group D
   dictD[11] = 0
   dictD[21] = 84
   dictD[22] = 87
   dictD[23] = 92
   dictD[24] = 95
   dictD[31] = 94
   dictD[32] = 0
   dictD[41] = 77
   dictD[42] = 77
   dictD[43] = 77
   dictD[52] = 73
   dictD[71] = 78
   dictD[81] = 80
   dictD[82] = 89
   dictD[90] = 0
   dictD[95] = 0
   m["D"] = dictD
      
   hydroGrps = ["A", "B", "C", "D"]
   in_HydroGrp = Raster(in_HydroGrp)
   
   if type(in_LC) == str:
      # Create and calculate curve number fields in the land cover attribute table
      for grp in hydroGrps:  
         fldName = "cn_%s" %grp
         d = m[grp]
         
         fldList = arcpy.ListFields(in_LC) 
         fldNames = [f.name for f in fldList]
         if fldName in fldNames:
            print("Deleting existing field %s..." %fldName)
            arcpy.DeleteField_management (in_LC, fldName)
         
         print("Adding field %s..." %fldName)
         arcpy.AddField_management(in_LC, fldName, "SHORT")
      
         print("Calculating field...")
         codeblock = '''def curvnum(code, dic):
            try:
               cn = dic[code]
            except:
               cn = 0
            return cn
            '''
         expression = "curvnum(!VALUE!, %s)" %d
         arcpy.CalculateField_management (in_LC, fldName, expression, 'PYTHON', codeblock)
      
      # Create a new raster from the curve number fields, based on soil type
      print("Creating curve number raster...")
      outRaster = Con(in_HydroGrp == 1, Lookup(in_LC, "cn_A"), Con(in_HydroGrp == 2, Lookup(in_LC, "cn_B"), Con(in_HydroGrp == 3, Lookup(in_LC, "cn_C"),Con(in_HydroGrp == 4, Lookup(in_LC, "cn_D")))))
   
   else:
      # Use the specified land cover constant with soil type to get the curve number
      outRaster = Con(in_HydroGrp == 1, dictA[in_LC], Con(in_HydroGrp == 2, dictB[in_LC], Con(in_HydroGrp == 3, dictC[in_LC],Con(in_HydroGrp == 4, dictD[in_LC]))))
   
   print("Saving output...")
   outRaster.save(out_CN)
   
   print("Mission complete.")

def eventRunoff(in_Raster, in_Rain, out_GDB, yearTag, cellArea = 1000000, inputType = "CN", convFact = 1):
   '''Produces an output raster representing event-based runoff volume in Liters
   
   Parameters:
   - in_Raster: input raster representing curve numbers OR maximum retention
   - in_Rain: input constant or raster representing rainfall
   - out_GDB: geodatabase for storing outputs
   - yearTag: tag to add to basenames to indicate land cover year determining curve numbers 
   - cellArea: area of cells in Curve Number raster, in square centimeters
   - inputType: indicates whether in_Raster is curve numbers (CN) or retention (RET)
   - convFact: conversion factor to convert input rainfall depth units to inches
   '''
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Set scratch output location
   scratchGDB = arcpy.env.scratchGDB
   
   # Set up some variables
   in_Raster = Raster(in_Raster)
   try:
      in_Rain = Raster(in_Rain)
   except:
      pass
   out_Retention = out_GDB + os.sep + "Retention_%s" %yearTag
   out_runoffDepth = out_GDB + os.sep + "runoffDepth_%s" %yearTag
   out_runoffVolume = out_GDB + os.sep + "runoffVol_%s" %yearTag
   out_accumRunoff = out_GDB + os.sep + "accRunoff_%s" %yearTag

   # Perform calculations
   # Result could be raster or a constant depending on input
   if convFact != 1:
      rain = convFact*in_Rain 
   else:
      rain = in_Rain
   
   if inputType == "CN":
      print("Calculating maximum retention...")
      # Have to deal with division by zero here.
      retention = Con(in_Raster == 0, 1000, ((float(1000)/in_Raster) - 10))
      print("Saving...")
      retention.save(out_Retention)
   else:
      retention = in_Raster
   
   print("Calculating runoff depth (inches)...")
   # Set runoff depth to zero if rainfall is less than initial abstraction
   runoffDepth = Con((rain - 0.2*retention) > 0,(rain - 0.2*retention)**2/(rain + 0.8*retention),0)
   print("Saving...")
   runoffDepth.save(out_runoffDepth)
   
   print("Calculating runoff volume (liters)...")
   # 2.54 converts inches to cm
   # 0.001 converts cubic cm to liters
   volumeConversion = 0.00254*cellArea
   runoffVolume = volumeConversion*runoffDepth
   print("Saving...")
   runoffVolume.save(out_runoffVolume)
   
   # if in_FlowDir != "NONE":
      # print("Calculating runoff accumulation...")
      # accumRunoff = FlowAccumulation(in_FlowDir, runoff, "FLOAT", "D8") + runoff
      # print("Saving...")
      # accumRunoff.save(out_accumRunoff)
   # else:
      # print("No flow direction raster provided; runoff not accumulated.")
   
   print("Mission accomplished.")
 
def main():
   # Inputs - Soils
   dc_gdb = r"E:\SpatialData\SSURGO\gSSURGO_DC\gSSURGO_DC.gdb"
   de_gdb = r"E:\SpatialData\SSURGO\gSSURGO_DE\gSSURGO_DE.gdb"
   ky_gdb = r"E:\SpatialData\SSURGO\gSSURGO_KY\gSSURGO_KY.gdb"
   md_gdb = r"E:\SpatialData\SSURGO\gSSURGO_MD\gSSURGO_MD.gdb"
   nc_gdb = r"E:\SpatialData\SSURGO\gSSURGO_NC\gSSURGO_NC.gdb"
   pa_gdb = r"E:\SpatialData\SSURGO\gSSURGO_PA\gSSURGO_PA.gdb"
   tn_gdb = r"E:\SpatialData\SSURGO\gSSURGO_TN\gSSURGO_TN.gdb"
   va_gdb = r"E:\SpatialData\SSURGO\gSSURGO_VA\gSSURGO_VA.gdb"
   wv_gdb = r"E:\SpatialData\SSURGO\gSSURGO_WV\gSSURGO_WV.gdb"
   
   # Inputs - Miscellany
   in_Snap = r"E:\SpatialData\HealthyWatersWork\HW_templateRaster_Feature\HW_templateRaster.tif"
   in_Elev = r"E:\SpatialData\elev_cm.gdb\elev_cm.gdb\elev_cm_VA"
   in_clpShp = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200601.gdb\HW_template_buff13k_noHoles"
   in_Rfactor = r"F:\CurrentData\R_Factor\R-Factor_CONUS.tif"
   in_pmpPts = r"E:\SpatialData\DCR_DamSafety\PMP\pmpEvalTool_v2\Output\General\PMP_64457.gdb\General_PMP_Points_64457"
   pmpFld = "PMP_24"
   
   # Outputs
   outGDB = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb" # I change this frequently   
   out_Runoff = outGDB + os.sep + "runoffScore"
   out_Erosion = outGDB + os.sep + "erosionScore"
   out_SoilSens = outGDB + os.sep + "soilSens" 
   hydroGrp = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\hydroGroup"
   slope_perc = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200626.gdb\slope_perc"
   Kfactor = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\rusleK"
   Sfactor = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200626.gdb\rusleS"
   Rfactor = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200601.gdb\rusleR"
   rusleRKS = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200626.gdb\rusleRKS"
   maxPrecip250 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200629.gdb\maxPrecip_gen24_topo250"
   maxPrecip10 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200629.gdb\maxPrecip_gen24_topo10"
   in_Rain = maxPrecip10
   
   # Year-specific Outputs/Inputs
   # RUSLE C-Factor
   rusleC_2016 = outGDB + os.sep + "rusleC_2016"
   rusleC_2011 = outGDB + os.sep + "rusleC_2011"
   rusleC_2006 = outGDB + os.sep + "rusleC_2006"
   rusleC_2001 = outGDB + os.sep + "rusleC_2001"   
   
   # RUSLE RKSC
   rusleRKSC_2016 = outGDB + os.sep + "rusleRKSC_2016"
   rusleRKSC_2011 = outGDB + os.sep + "rusleRKSC_2011"
   rusleRKSC_2006 = outGDB + os.sep + "rusleRKSC_2006"
   rusleRKSC_2001 = outGDB + os.sep + "rusleRKSC_2001"
   rusleRKSC_dfor = outGDB + os.sep + "rusleRKSC_dfor"
   rusleRKSC_bare = outGDB + os.sep + "rusleRKSC_bare"
   
   # Curve Numbers
   curvNum_2016 = outGDB + os.sep + "curvNum_2016"
   curvNum_2011 = outGDB + os.sep + "curvNum_2011"
   curvNum_2006 = outGDB + os.sep + "curvNum_2006"
   curvNum_2001 = outGDB + os.sep + "curvNum_2001"
   curvNum_dfor = outGDB + os.sep + "curvNum_dfor"
   curvNum_bare = outGDB + os.sep + "curvNum_bare"
   
   # Runoff Volume
   runoffVol_2016 = outGDB + os.sep + "runoffVol_2016"
   runoffVol_2011 = outGDB + os.sep + "runoffVol_2011"
   runoffVol_2006 = outGDB + os.sep + "runoffVol_2006"
   runoffVol_2001 = outGDB + os.sep + "runoffVol_2001"
   
   # Pollutant Coefficients
   Nitrogen_2016 = outGDB + os.sep + "Nitrogen_2016"
   Nitrogen_2011 = outGDB + os.sep + "Nitrogen_2011"
   Nitrogen_2006 = outGDB + os.sep + "Nitrogen_2006"
   Nitrogen_2001 = outGDB + os.sep + "Nitrogen_2001"
   Phosphorus_2016 = outGDB + os.sep + "Phosphorus_2016"
   Phosphorus_2011 = outGDB + os.sep + "Phosphorus_2011"
   Phosphorus_2006 = outGDB + os.sep + "Phosphorus_2006"
   Phosphorus_2001 = outGDB + os.sep + "Phosphorus_2001"
   SuspSolids_2016 = outGDB + os.sep + "SuspSolids_2016"
   SuspSolids_2011 = outGDB + os.sep + "SuspSolids_2011"
   SuspSolids_2006 = outGDB + os.sep + "SuspSolids_2006"
   SuspSolids_2001 = outGDB + os.sep + "SuspSolids_2001"
   
   # Processing Lists/Dictionaries
   gdbList = [dc_gdb, de_gdb, ky_gdb, md_gdb, nc_gdb, pa_gdb, tn_gdb, va_gdb, wv_gdb]
   testList = [dc_gdb]
   
   nlcdDict = dict()
   nlcdDict[2016] = r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2016_10m"
   nlcdDict[2011] = r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2011_10m"
   nlcdDict[2006] = r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2006_10m"
   nlcdDict[2001] = r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2001_10m"
   
   ### Specify function(s) to run
   createFGDB(outGDB) # Create the specified outGDB if it doesn't already exist
   
   ### Create NSPECT pollution coefficient rasters
   print("Creating year-specific NSPECT pollution coefficient rasters...")
   nDict = dict()
   pDict = dict()
   sDict = dict()
   coeffList = [["Nitrogen", "NPOLL", nDict], 
            ["Phosphorus", "PPOLL", pDict], 
            ["SuspSolids", "SPOLL", sDict]]
   for year in nlcdDict.keys():
      print("Working on %s data..." %year)
      for coeff in coeffList:
         rName = coeff[0]
         coeffType = coeff[1]
         coeffDict = coeff[2]
         out_Coeff = outGDB + os.sep + "%s_%s" %(rName, year)
         coeffNSPECT(nlcdDict[year], coeffType, out_Coeff)
         coeffDict[year] = out_Coeff
   
   ### Create curve number rasters
   SSURGOtoRaster(gdbList, "HydroGrpNum", in_Snap, hydroGrp)
   print("Creating year-specific Curve Number rasters...")
   cnDict = dict()
   for year in nlcdDict.keys():
      print("Working on %s data..." %year)
      in_LC = nlcdDict[year]
      out_CN = outGDB + os.sep + "curvNum_%s" %year
      curvNum(in_LC, hydroGrp, out_CN)
      cnDict[year] = out_CN
      
   ### Create RUSLE factors
   print("Creating year-specific C-factors...")
   cfactDict = dict()
   for year in nlcdDict.keys():
      print("Working on %s data..." %year)
      in_LC = nlcdDict[year]
      out_Cfactor = outGDB + os.sep + "rusleC_%s" %year
      coeffNSPECT(in_LC, "CFACT", out_Cfactor)
      cfactDict[year] = out_Cfactor
   print("Downscaling R-factor...")
   Downscale_ras(in_Rfactor, in_Snap, Rfactor, "BILINEAR", in_clpShp) # R-factor
   print("Creating K-factor raster...")
   SSURGOtoRaster(gdbList, "kFactor", in_Snap, Kfactor) # K-factor
   print("Creating S-factor raster...")
   SlopeTrans(in_Elev, "ELEV", "RUSLE", Sfactor, slope_perc, zfactor = 0.01) # S-factor
   print("Creating RKS raster...")
   soilLoss_RKS(Rfactor, Kfactor, Sfactor, rusleRKS) # R*K*S
   
   ### Get Probable Maximum Precipitation
   # First had to use the PMP tool(https://www.dcr.virginia.gov/dam-safety-and-floodplains/pmp-tool) from within ArcGIS Pro to generate the points used for interpolation. I specified a 24-hour storm duration, and used the "General" output.
   # arcpy.ImportToolbox(r'E:\SpatialData\DCR_DamSafety\PMP\pmpEvalTool_v2\Script\VA_PMP_Tools_v2.tbx','')
   # arcpy..PMPCalc(r"E:\SpatialData\HW_templateRaster_Feature\HW_templateFeature.shp", r"E:\SpatialData\DCR_DamSafety\PMP\pmpEvalTool_v2", r"E:\SpatialData\DCR_DamSafety\PMP\pmpEvalTool_v2\Output", "24", "24", "24", True, None)
   interpPoints(in_pmpPts, pmpFld, in_Snap, maxPrecip250, in_clpShp, "TOPO", "", "", 250)
   Downscale_ras(maxPrecip250, in_Snap, maxPrecip10, "BILINEAR", in_clpShp)
   
   ### Create runoff, pollution, and sediment yield rasters
   print("Creating year-specific runoff, pollution, and sediment yield rasters...")
   runoffDict = dict()
   nMassDict = dict()
   pMassDict = dict()
   sMassDict = dict()
   pollutantList = [["Nitrogen", nDict, nMassDict], 
            ["Phosphorus", pDict, pMassDict], 
            ["SuspSolids", sDict, sMassDict ]]
   for year in nlcdDict.keys():
      print("Working on %s data..." %year)
      CN = cnDict[year]
      cFact = cfactDict[year]
      print("Calculating runoff...")
      eventRunoff(CN, in_Rain, outGDB, year, 1000000, "CN")
      runoffDict[year] = outGDB + os.sep + "runoffVol_%s" %year
      for pollutant in pollutantList:
         rName = pollutant[0]
         coeffDict = pollutant[1]
         massDict = pollutant[2]
         out_Raster = outGDB + os.sep + "LocMass_%s_%s"%(rName, year)
         print("Calculating %s mass..."%rName)
         pollMass = Raster(coeffDict[year])*Raster(runoffDict[year])
         pollMass.save(out_Raster)
         massDict[year] = out_Raster
      print("Calculating standard sediment yield...")
      SedYld(rusleRKS, CN, year, slope_perc, outGDB, cFact, sdrType = "STD", cellArea = 0.0001)
      print("Calculating alternate sediment yield...")
      SedYld(rusleRKS, CN, year, slope_perc, outGDB, cFact, sdrType = "ALT")
   
   ### Get "worst-case" (bare land, NLCD code 31, C-factor = 0.700) and "best-case" (deciduous forest, NLCD code 41, C-factor = 0.009) scenarios for curve numbers, runoff, and sedimentation. These are not necessarily the best or worst (e.g., wetlands are even better than deciduous forest) but serve the purpose here.
   print("Calculating best- and worst-case curve numbers...")
   curvNum(41, hydroGrp, curvNum_dfor)
   curvNum(31, hydroGrp, curvNum_bare)
   # Event runoff
   print("Calculating best-and worst-case runoff...")
   eventRunoff(curvNum_dfor, in_Rain, outGDB, "dfor")
   eventRunoff(curvNum_bare, in_Rain, outGDB, "bare")
   # Soil loss potential
   print("Calculating best- and worst-case soil loss potential...")
   soilLoss_RKSC(rusleRKS, 0.009, rusleRKSC_dfor)
   soilLoss_RKSC(rusleRKS, 0.700, rusleRKSC_bare)
   print("Mission accomplished.")
   
if __name__ == '__main__':
   main()
