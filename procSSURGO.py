# ---------------------------------------------------------------------------
# procSSURGO.py
# Version: ArcPro / Python 3+
# Creation Date: 2020-05-19
# Last Edit: 2020-06-30
# Creator: Kirsten R. Hazler
#
# Summary: Functions for processing SSURGO data and producing rasters representing soil conditions, as well as functions inspired by OpenNSPECT software to produce rasters representing interactions between soils, topography, and land cover.
#
# Adapted from toolbox tools and scripts used to produce the 2017 edition of the ConservationVision Watershed Model, and from information about the OpenNSPECT tool.
# For background references and formulas, see: 
# - Virginia ConservationVision Watershed Model, 2017 Edition (NHTR 18-16; 2018)
# - Technical Guide for OpenNSPECT, Version 1.1 (2012)
# - Predicting soil erosion by water: a guide to conservation planning with the revised universal soil loss equation (RUSLE) (USDA Agriculture Handbook 703; 1997)
# ---------------------------------------------------------------------------

# Import modules
import arcpy
import sys, os
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
from datetime import datetime as datetime 

### Helper functions (should be moved over to Helper.py later)
def createFGDB(FGDB):
   '''Checks to see if specified file geodatabase exists, and creates it if not.
   Parameters:
   - FGDB: full path to file geodatabase (e.g. r'C:\myDir\myGDB.gdb')
   '''
   gdbPath = os.path.dirname(FGDB)
   gdbName = os.path.basename(FGDB)
   
   if arcpy.Exists(FGDB):
      print("%s already exists." %gdbName)
      pass
   else:
      print("Creating new file geodatabase...")
      arcpy.CreateFileGDB_management(gdbPath, gdbName)
      print("%s created." %gdbName)
   return FGDB

def CompareSpatialRef(in_Data, in_Template):
   sr_In = arcpy.Describe(in_Data).spatialReference
   sr_Out = arcpy.Describe(in_Template).spatialReference
   srString_In = sr_In.exporttostring()
   srString_Out = sr_Out.exporttostring()
   gcsString_In = sr_In.GCS.exporttostring()
   gcsString_Out = sr_Out.GCS.exporttostring()
    
   if srString_In == srString_Out:
      reproject = 0
      transform = 0
      geoTrans = ""
   else:
      reproject = 1
      
   if reproject == 1:
      if gcsString_In == gcsString_Out:
         transform = 0
         geoTrans = ""
      else:
         transList = arcpy.ListTransformations(sr_In, sr_Out)
         if len(transList) == 0:
            transform = 0
            geoTrans = ""
         else:
            transform = 1
            geoTrans = transList[0]
         
   return (sr_In, sr_Out, reproject, transform, geoTrans)
   
def ProjectToMatch_vec(in_Data, in_Template, out_Data, copy = 1):
   '''Check if input features and template data have same spatial reference.
   If so, make a copy. If not, reproject features to match template.
   
   Parameters:
   in_Data: input features to be reprojected or copied
   in_Template: dataset used to determine desired spatial reference
   out_Data: output features resulting from copy or reprojection
   copy: indicates whether to make a copy (1) or not (0) for data that don't need to be reprojected
   '''
   
   # Compare the spatial references of input and template data
   (sr_In, sr_Out, reproject, transform, geoTrans) = CompareSpatialRef(in_Data, in_Template)
   
   if reproject == 0:
      print('Coordinate systems for features and template data are the same.')
      if copy == 1: 
         print('Copying...')
         arcpy.CopyFeatures_management (in_Data, out_Data)
      else:
         print('Returning original data unchanged.')
         out_Data = in_Data
   else:
      print('Reprojecting features to match template...')
      if transform == 0:
         print('No geographic transformation needed...')
      else:
         print('Applying an appropriate geographic transformation...')
      arcpy.Project_management (in_Data, out_Data, sr_Out, geoTrans)
   return out_Data
   
def ProjectToMatch_ras(in_Data, in_Template, out_Data, resampleType = "NEAREST", cellSize = ""):
   '''Check if input raster and template raster have same spatial reference.
   If not, reproject input to match template.
   Parameters:
   in_Data = input raster to be reprojected
   in_Template = dataset used to determine desired spatial reference and cell alignment
   out_Data = output raster resulting from resampling
   resampleType = type of resampling to use (NEAREST, MAJORITY, BILINEAR, or CUBIC)
   '''
   
   # Compare the spatial references of input and template data
   (sr_In, sr_Out, reproject, transform, geoTrans) = CompareSpatialRef(in_Data, in_Template)
   
   if reproject == 0:
      print('Coordinate systems for input and template data are the same. No need to reproject.')
      return in_Data
   else:
      print('Reprojecting input raster to match template...')
      arcpy.env.snapRaster = in_Template
      if transform == 0:
         print('No geographic transformation needed...')
      else:
         print('Applying an appropriate geographic transformation...')
      arcpy.ProjectRaster_management (in_Data, out_Data, sr_Out, resampleType, cellSize, geoTrans)
      return out_Data
 
def Downscale_ras(in_Raster, in_Snap, out_Raster, resType = "BILINEAR", in_clpShp = "NONE"):
   '''Converts a lower resolution raster to one of higher resolution to match the cell size and alignment of the specified snap raster.
   
   Parameters:
   - in_Raster: input raster to be resampled. Enter NONE if using input points instead.
   - in_Snap: snap raster used to set output cell size and alignment; also acts as mask
   - out_Raster: output resampled raster
   - resType: raster resampling type (NEAREST, BILINEAR, CUBIC, or MAJORITY)
   - in_clpShp: input feature class used to clip the input raster. Enter NONE if no clipping is needed.
   '''
   
   # Set environment variables        
   arcpy.env.overwriteOutput = True
   arcpy.env.snapRaster = in_Snap
   arcpy.env.extent = in_Snap
   arcpy.env.mask = in_Snap
   cellSize = arcpy.GetRasterProperties_management(in_Snap, "CELLSIZEX").getOutput(0)
   scratchGDB = arcpy.env.scratchGDB
   
   if in_clpShp == "NONE":
      clpRast = in_Raster
   else:
      clpRast = scratchGDB + os.sep + "clpRast"
      print("Getting extents of clip shape...")
      desc = arcpy.Describe(in_clpShp)
      xmin = desc.extent.XMin
      xmax = desc.extent.XMax
      ymin = desc.extent.YMin
      ymax = desc.extent.YMax
      rect = "%s %s %s %s" %(xmin, ymin, xmax, ymax)
      print("Clipping raster...")
      arcpy.management.Clip(in_Raster, rect, clpRast, in_clpShp, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
   
   resRast = scratchGDB + os.sep + "resRast"
   tmpRast = ProjectToMatch_ras(clpRast, in_Snap, resRast, resType, cellSize)
   
   if tmpRast == clpRast:
      # If no re-projection occurred...
      print("Resampling...")
      arcpy.management.Resample(clpRast, resRast, cellSize, resType)
   else:
      pass

   print("Finalizing output and saving...")
   finRast = Con(in_Snap, resRast)
   finRast.save(out_Raster)

   print("Mission complete.")

def interpPoints(in_Points, valFld, in_Snap, out_Raster, in_clpShp = "NONE", interpType = "IDW", numPts = 9, maxDist = "", cellSize = ""):
   '''Converts a point dataset to a raster via specified interpolation method
   
   NOTES/LESSONS LEARNED: 
   - I tried multiple methods on the PMP point data. In the end I settled on the topographic method.
   - The topographic method is memory-intensive. It failed (memory allocation error) when I tried to interpolate the PMP data to 10-m. Instead, I ended up doing the topographic interpolation to a 250-m cell size, then resampling that output to get a 10-m resolution raster. 
   
   Parameters:
   - in_Points: input points with values to be interpolated
   - valFld: the field in the input points used to determine output raster values. 
   - in_Snap: snap raster used to set output cell size and alignment; also acts as mask
   - out_Raster: output resampled raster
   - in_clpShp: input feature class used to clip the input raster or input points. Enter NONE if no clipping is needed.
   - interpType: interpolation type (SPLINE, TREND2, TREND3, TOPO, or IDW). 
   - numPts: number of points used for interpolation. Ignored if TREND2 interpolation.
   - maxDist: maximum search radius for interpolation. Ignored if SPLINE or TREND2 interpolation.
   - cellSize: cell size of the output raster. If not specified, same as in_Snap raster.
   '''
   
   # timestamp
   t0 = datetime.now()
   
   # Set environment variables        
   arcpy.env.overwriteOutput = True
   arcpy.env.snapRaster = in_Snap
   arcpy.env.extent = in_Snap
   arcpy.env.mask = in_Snap
   scratchGDB = arcpy.env.scratchGDB
   
   if cellSize == "":
      cellSize = arcpy.GetRasterProperties_management(in_Snap, "CELLSIZEX").getOutput(0)
   
   if in_clpShp == "NONE":  
      clpPts = in_Points
   else:
      clpPts = scratchGDB + os.sep + "clpPts"
      print("Getting extents of clip shape...")
      desc = arcpy.Describe(in_clpShp)
      xmin = desc.extent.XMin
      xmax = desc.extent.XMax
      ymin = desc.extent.YMin
      ymax = desc.extent.YMax
      rect = "%s %s %s %s" %(xmin, ymin, xmax, ymax)
      print("Clipping feature class...")
      arcpy.Clip_analysis(in_Points, in_clpShp, clpPts)
   
   prjPts = scratchGDB + os.sep + "prjPts"
   tmpPts = ProjectToMatch_vec(clpPts, in_Snap, prjPts, copy = 1)
   
   if interpType == "IDW":
      # This is not as smooth as I'd like, but output makes more sense than spline for PMP points
      print("Interpolating points using inverse weighted squared distance...")
      radius = RadiusVariable(numPts, maxDist)
      finRast = Idw(tmpPts, valFld, cellSize, 2, radius)
   elif interpType == "SPLINE":
      # This did NOT work well with PMP data points - values WAY out of range on the periphery
      print("Interpolating points using spline...")
      finRast = Spline(tmpPts, valFld, cellSize, "REGULARIZED", "", numPts)
   elif interpType == "TREND2":
      print("Interpolating points using 2nd-order polynomial trend...")
      finRast = Trend(tmpPts, valFld, cellSize, 2, "LINEAR")
   elif interpType == "TREND3":
      print("Interpolating points using 3nd-order polynomial trend...")
      finRast = Trend(tmpPts, valFld, cellSize, 3, "LINEAR")
   elif interpType == "TOPO":
      print("Interpolating points using topographic algorithm...")
      ptFeats = TopoPointElevation([[tmpPts, valFld]])
      in_topo_features = [ptFeats]
      finRast = TopoToRaster(in_topo_features, cellSize, rect, "", "", "", "NO_ENFORCE", "SPOT")
   else:
      print("Interpolation type specification is invalid. Aborting.")
      sys.exit()
      
   print("Finalizing output and saving...")
   finRast.save(out_Raster)
   
   # timestamp
   t1 = datetime.now()
   ds = GetElapsedTime (t0, t1)
   print("Completed interpolation function. Time elapsed: %s" % ds)

def PolyToRaster(in_Poly, in_Fld, in_Snap, out_Rast):
   '''Converts polygons to raster based on specified field.
   
   Parameters:
   - in_Poly: input polygon feature class to be converted to raster
   - in_Fld: field in feature class used to determine raster values
   - in_Snap: input raster used to specify output coordinate system, processing extent, cell size, and alignment
   - out_Rast: output raster
   '''
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Specify scratch location
   scratchGDB = arcpy.env.scratchGDB
   
   # Get output coordinate system and set environment variables
   srRast = arcpy.Describe(in_Snap).spatialReference
   arcpy.env.snapRaster = in_Snap
   arcpy.env.extent = in_Snap
   arcpy.env.mask = in_Snap
   
   # Project polygons, if necessary
   srPoly = arcpy.Describe(in_Poly).spatialReference
   if srRast.Name != srPoly.Name:
      print("Reprojecting polygons to match snap raster...")
      if srRast.GCS.Name == srPoly.GCS.Name:
         geoTrans = ""
         print("No geographic transformation needed...")
      else:
         transList = arcpy.ListTransformations(srPoly,srRast)
         geoTrans = transList[0]
      out_Poly = scratchGDB + os.sep + "polyPrj"
      arcpy.Project(in_Poly, out_Poly, srRast, geoTrans)
   else:
      print("No need for reprojection.")
      out_Poly = in_Poly
   
   # Convert to raster
   print("Rasterizing polygons...")
   arcpy.PolygonToRaster_conversion (out_Poly, in_Fld, out_Rast, "MAXIMUM_COMBINED_AREA", 'None', in_Snap)
   
   print("Rasterization complete.")
   return

def GetElapsedTime (t0, t1):
   """Gets the time elapsed between the start time (t0) and the finish time (t1).
   NOTE: This had to be modified from the function originally written for Python 2.x"""
   delta = t1 - t0
   (d, m, s) = (delta.days, int(delta.seconds/60), delta.seconds%60)
   h = int(m/60)
   deltaString = '%s days, %s hours, %s minutes, %s seconds' % (str(d), str(h), str(m), str(s))
   return deltaString
   
# Main functions      

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
   - slopeType: indicates whether the input raster is slope in degrees (DEG or DEGREES), slope as percent grade (PERC or PERCENT), or elevation (ELEV or ELEVATION)
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
   
def rusleRKS(in_Rfactor, in_Kfactor, in_Sfactor, out_RKS):
   '''Multiplies the rasters representing three of the factors in the Revised Universal Soil Loss Equation (RUSLE), to produce a relative measure of the propensity for soil loss. Does not include the cover management (C), slope length (L), or the  supporting practices (P) factors. Inputs must have been first generated by previous functions to produce the input rasters. 
   
   This functions assumes all inputs are in the same coordinate system and properly aligned with each other.

   Parameters:
   - in_Rfactor: rainfall/runoff erosivity factor
   - in_Kfactor: soil erodibility factor
   - in_Sfactor: slope steepness factor
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

def coeffNSPECT(in_LC, coeffType, out_Coeff):
   '''From and input land cover raster, creates a new raster representing the NSPECT coefficient type specified (coeffType). Coefficient values are from the OpenNSPECT Technical Guide. The land cover codes in that table are CCAP codes, so assignments in this function are to the equivalent NLCD codes. 
   
   The coefficients that may be specified are:
   - CFACT: The cover factor (C-Factor in the RUSLE equation; a unitless ratio)
   - NPOLL: Nitrogen pollution factor (mg/L)
   - PPOLL: Phosphorus pollution factor (mg/L)
   - SPOLL: Suspended solids pollution factor (mg/L)
   
   C-factor values are assigned to land cover classes as specified in Table 4, page 22 of the OpenNSPECT Technical Guide. The pollution coefficients are specified in Appendix A, pages 42-43.
   
   This function modifies the input land cover attribute table, by adding and calculating a new field to store the desired coefficients.

   Parameters:
   - in_LC: Input classified land cover raster, using standard NLCD land cover codes
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
   '''Given input land cover and hydrologic group rasters, produces output raster representing runoff curve numbers.
   
   Curve numbers are assigned to combinations of land cover and soil types as specified in Table 1, page 6 of the OpenNSPECT Technical Guide. 
   
   This function modifies the input land cover attribute table, by adding and calculating a new field to store the curve numbers

   Parameters:
   - in_LC: Input classified land cover raster, using standard NLCD land cover codes
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

   # Create and calculate curve number fields in the land cover attribute table
   
   hydroGrps = ["A", "B", "C", "D"]
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
   in_HydroGrp = Raster(in_HydroGrp)
   outRaster = Con(in_HydroGrp == 1, Lookup(in_LC, "cn_A"), Con(in_HydroGrp == 2, Lookup(in_LC, "cn_B"), Con(in_HydroGrp == 3, Lookup(in_LC, "cn_C"),Con(in_HydroGrp == 4, Lookup(in_LC, "cn_D")))))
    
   print("Saving output...")
   outRaster.save(out_CN)
   
   print("Mission complete.")

def eventRunoff(in_Raster, in_Rain, out_GDB, yearTag, cellArea, inputType = "CN", convFact = 1):
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
   outGDB = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200629.gdb" # I change this frequently   
   out_Runoff = outGDB + os.sep + "runoffScore"
   out_Erosion = outGDB + os.sep + "erosionScore"
   out_SoilSens = outGDB + os.sep + "soilSens" 
   out_hydroGrp = outGDB + os.sep + "hydroGroup"
   out_Slope = outGDB + os.sep + "slope_perc"
   out_Kfactor = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\rusleK"
   out_Sfactor = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200626.gdb\rusleS"
   out_Rfactor = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200601.gdb\rusleR"
   out_RKS = outGDB + os.sep + "rusleRKS"
   out_maxPrecip_topo250 = outGDB + os.sep + "maxPrecip_gen24_topo250"
   out_maxPrecip_topo10 = outGDB + os.sep + "maxPrecip_gen24_topo10"
   in_Rain = out_maxPrecip_topo10
   
   # Year-specific Outputs/Inputs
   # RUSLE C-Factor
   rusleC_2016 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\rusleC_2016"
   rusleC_2011 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\rusleC_2011"
   rusleC_2006 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\rusleC_2006"
   rusleC_2001 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\rusleC_2001"   
   
   # Curve Numbers
   curvNum_2016 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\curvNum_2016"
   curvNum_2011 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\curvNum_2011"
   curvNum_2006 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\curvNum_2006"
   curvNum_2001 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\curvNum_2001"
   
   # Pollutant Coefficients
   Nitrogen_2016 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Nitrogen_2016"
   Nitrogen_2011 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Nitrogen_2011"
   Nitrogen_2006 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Nitrogen_2006"
   Nitrogen_2001 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Nitrogen_2001"
   Phosphorus_2016 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Phosphorus_2016"
   Phosphorus_2011 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Phosphorus_2011"
   Phosphorus_2006 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Phosphorus_2006"
   Phosphorus_2001 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\Phosphorus_2001"
   SuspSolids_2016 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\SuspSolids_2016"
   SuspSolids_2011 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\SuspSolids_2011"
   SuspSolids_2006 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\SuspSolids_2006"
   SuspSolids_2001 = r"E:\SpatialData\HealthyWatersWork\hwProducts_20200527.gdb\SuspSolids_2001"
   
   
   # Processing Lists/Dictionaries
   gdbList = [dc_gdb, de_gdb, ky_gdb, md_gdb, nc_gdb, pa_gdb, tn_gdb, va_gdb, wv_gdb]
   testList = [dc_gdb]
   
   nlcdDict = dict()
   nlcdDict[2016] = r"E:\SpatialData\NLCD_landCover.gdb\lc_2016_proj"
   nlcdDict[2011] = r"E:\SpatialData\NLCD_landCover.gdb\lc_2011_proj"
   nlcdDict[2006] = r"E:\SpatialData\NLCD_landCover.gdb\lc_2006_proj"
   nlcdDict[2001] = r"E:\SpatialData\NLCD_landCover.gdb\lc_2001_proj"
   
   
   ### Specify function(s) to run
   createFGDB(outGDB) # Create the specified outGDB if it doesn't already exist
   
   ### Create scores for Watershed Model
   # for gdb in gdbList:
      # RunoffScore_vec(gdb)
      # ErosionScore_vec(gdb)
      # HydroGrp_vec(gdb) 
   # SSURGOtoRaster(gdbList, "runoffScore", in_Snap, out_Runoff)
   # SSURGOtoRaster(gdbList, "erosionScore", in_Snap, out_Erosion)
   # SoilSensitivity(out_Runoff, out_Erosion, out_Slope, out_SoilSens)

   ### Create NSPECT pollution coefficient rasters
   # for year in nlcdDict.keys():
      # print("Working on %s data..." %year)
      # cList = [["Nitrogen", "NPOLL"], 
               # ["Phosphorus", "PPOLL"], 
               # ["SuspSolids", "SPOLL"]]
      # for coeff in cList:
         # rName = coeff[0]
         # coeffType = coeff[1]
         # out_Coeff = outGDB + os.sep + "%s_%s" %(rName, year)
         # coeffNSPECT(nlcdDict[year], coeffType, out_Coeff)
   
   ### Create Curve Number rasters
   # SSURGOtoRaster(gdbList, "HydroGrpNum", in_Snap, out_hydroGrp)
   # for year in nlcdDict.keys():
      # print("Working on %s data..." %year)
      # in_LC = nlcdDict[year]
      # out_CN = outGDB + os.sep + "curvNum_%s" %year
      # curvNum(in_LC, out_hydroGrp, out_CN)
      
   ### Create RUSLE factors
   # SSURGOtoRaster(gdbList, "kFactor", in_Snap, out_Kfactor)
   # for year in nlcdDict.keys():
      # print("Working on %s data..." %year)
      # rName = "rusleC"
      # out_Cfactor = outGDB + os.sep + "%s_%s" %(rName, year)
      # coeffNSPECT(nlcdDict[year], "CFACT", out_Cfactor)
   # Downscale_ras(in_Rfactor, in_Snap, out_Rfactor, "BILINEAR", in_clpShp)
   # SlopeTrans(in_Elev, "ELEV", "RUSLE", out_Sfactor, out_Slope, zfactor = 0.01)
   # rusleRKS(out_Rfactor, out_Kfactor, out_Sfactor, out_RKS)
   
   ### Get Probable Maximum Precipitation and Runoff
   # For now just do 2016; later add other years
   # interpPoints(in_pmpPts, pmpFld, in_Snap, out_maxPrecip_topo250, in_clpShp, "TOPO", "", "", 250)
   # Downscale_ras(out_maxPrecip_topo, in_Snap, out_maxPrecip_topo10, "BILINEAR", in_clpShp)
   # eventRunoff(curvNum_2016, in_Rain, outGDB, "2016", 1000000, "CN")

   
if __name__ == '__main__':
   main()
