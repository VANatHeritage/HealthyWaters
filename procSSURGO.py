# ---------------------------------------------------------------------------
# procSSURGO.py
# Version: ArcPro / Python 3+
# Creation Date: 2020-05-19
# Last Edit: 2020-05-20
# Creator: Kirsten R. Hazler
#
# Summary: Functions for processing SSURGO data
#
# Adapted from toolbox tools and scripts used to produce the 2017 edition of the ConservationVision Watershed Model
# For background reference see Natural Heritage Technical Report 18-16
# ---------------------------------------------------------------------------

# Import modules
import arcpy
import os
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")

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

def GDBtoRaster(in_gdbList, in_Fld, in_Snap, out_Raster):
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
   '''To the MUPOLYGON feature class, adds a field called "erosionScore", with scores from 0 (low erodibility) to 100 (high erodibility), derived from the K-factor value provided by gSSURGO. 
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
   arcpy.CalculateField_management (kfactTab, kfactFld, expression, 'PYTHON', codeblock)
   
   # Create a field in the K-factor table to store the erosion score value, and calculate
   print("Adding erosionScore field...")
   arcpy.AddField_management(kfactTab, "erosionScore", "SHORT")
   
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
   arcpy.CalculateField_management (kfactTab, "erosionScore", expression, 'PYTHON', codeblock)
   
   # Process: Join Erosion Score to MUPOLYGON
   # First check if field exists (due to prior processing) and delete if so
   fldList = arcpy.ListFields(mupolygon) 
   fldNames = [f.name for f in fldList]
   if "erosionScore" in fldNames:
      print("Deleting existing erosionScore field in MUPOLYGON...")
      arcpy.DeleteField_management (mupolygon, "erosionScore")
   print("Joining erosionScore field to MUPOLYGON...")
   arcpy.JoinField_management(mupolygon, "MUKEY", kfactTab, "MUKEY", "erosionScore")
   
   print("Mission complete for %s." %bname)

   return

def SlopeScore_ras(in_Slope):
   '''From a raster representing slope in degrees, creates a new raster representing slope as a score ranging from 0 (flat) to 100 (cliff).

   Parameters:
   - in_Slope: input raster representing slope in degrees
   - out_SlopeScore: output raster representing slope score
   '''
   
   # Convert degrees to radians, take the sine, multiply by 100, and integerize
   print("Calculating score...")
   outRaster = Int(0.5 + 100*Sin(in_Slope * math.pi / 180.0))
   
   print("Saving output...")
   outRaster.save(out_SlopeScore)
   
   print("Mission complete")
   
   return
   
def SoilSensitivity(in_runoffScore, in_erosionScore, in_SlopeScore, out_SoilSens):
   '''From a raster representing slope score, and one or more gSSURGO geodatabases containing erosion score and runoff score fields, creates a raster representing soil sensitivity, ranging from 0 (low sensitivity) to 100 (high sensitivity). Inputs must have been first generated by the following functions:
   - RunoffScore_vec
   - ErosionScore_vec
   - SlopeScore_ras

   Parameters:
   - in_gdbList: List of gSSURGO geodatabases containing added attributes
   - in_SlopeScore: input raster representing slope score
   - out_SoilSens: output raster representing soil sensitivity
   '''
   # Set overwrite to be true         
   arcpy.env.overwriteOutput = True
   
   # Get output coordinate system, cell size, alignment, and processing area from SlopeScore raster
   srRast = arcpy.Describe(in_SlopeScore).spatialReference
   arcpy.env.snapRaster = in_SlopeScore
   arcpy.env.extent = in_SlopeScore
   arcpy.env.mask = in_SlopeScore

def main():
   # Set up variables
   dc_gdb = r"E:\SpatialData\SSURGO\gSSURGO_DC\gSSURGO_DC.gdb"
   de_gdb = r"E:\SpatialData\SSURGO\gSSURGO_DE\gSSURGO_DE.gdb"
   ky_gdb = r"E:\SpatialData\SSURGO\gSSURGO_KY\gSSURGO_KY.gdb"
   md_gdb = r"E:\SpatialData\SSURGO\gSSURGO_MD\gSSURGO_MD.gdb"
   nc_gdb = r"E:\SpatialData\SSURGO\gSSURGO_NC\gSSURGO_NC.gdb"
   pa_gdb = r"E:\SpatialData\SSURGO\gSSURGO_PA\gSSURGO_PA.gdb"
   tn_gdb = r"E:\SpatialData\SSURGO\gSSURGO_TN\gSSURGO_TN.gdb"
   va_gdb = r"E:\SpatialData\SSURGO\gSSURGO_VA\gSSURGO_VA.gdb"
   wv_gdb = r"E:\SpatialData\SSURGO\gSSURGO_WV\gSSURGO_WV.gdb"
   
   in_Snap = r"E:\SpatialData\flowlengover_HU8_VA.gdb\flowlengover_HU8_VA"
   out_Runoff = r"E:\SpatialData\hwProducts.gdb\runoffScore"
   out_Erosion = r"E:\SpatialData\hwProducts.gdb\erosionScore"
   
   gdbList = [dc_gdb, de_gdb, ky_gdb, md_gdb, nc_gdb, pa_gdb, tn_gdb, va_gdb, wv_gdb]
   testList = [dc_gdb]
   
   # Specify function(s) to run
   # for gdb in gdbList:
      # RunoffScore_vec(gdb)
      # ErosionScore_vec(gdb)
      
   GDBtoRaster(gdbList, "runoffScore", in_Snap, out_Runoff)
   GDBtoRaster(gdbList, "erosionScore", in_Snap, out_Erosion)
   
if __name__ == '__main__':
   main()
