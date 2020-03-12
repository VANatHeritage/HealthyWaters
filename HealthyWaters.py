# ----------------------------------------------------------------------------------------
# HealthyWaters.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2020-01-06
# Last Edit: 2020-01-16
# Creator(s):  Kirsten R. Hazler/David Bucklin

# Summary:
# Functions for Healthy Waters/INSTAR data

# Usage Tips:

# Dependencies: This set of functions will not work if the hydro network is not set up properly! The network
# geodatabase VA_HydroNet.gdb has been set up manually, not programmatically.

# The Network Analyst extension is required for some functions, which will fail if the license is unavailable.

# Note that the restrictions (contained in "r" variable below) for traversing the network must have been defined
# in the HydroNet itself (manually).

# If any additional restrictions are added, the HydroNet must be rebuilt or they will not take effect.
# I originally set a restriction of NoEphemeralOrIntermittent, but on testing I discovered that this eliminated
# some stream segments that actually might be needed. I set the restriction to NoEphemeral instead. We may find
# that we need to remove the NoEphemeral restriction as well, or that users will need to edit attributes of the
# NHDFlowline segments on a case-by-case basis. I also previously included NoConnectors as a restriction,
# but in some cases I noticed with INSTAR data, it seems necessary to allow connectors, so I've removed that
# restriction. (-krh)
# The NoCanalDitch exclusion was also removed, after finding some INSTAR sites on this type of flowline, and with
# CanalDitch immediately upstream.

# Syntax:
# # Set up a network analysis layer, specifying upstream distance desired (in map units)
# in_lyrUpTrace = MakeServiceLayer_hw(in_hydroNet, up_Dist = 1000, dams=False)
#
# Create feature classes for upstream flowline network and catchments
# GetCatchArea_hw(in_Points, in_lyrUpTrace, in_Catchment, out_Lines, out_CatchArea)
# ----------------------------------------------------------------------------------------

# Import modules
import Helper
from Helper import *

def MakeServiceLayer_hw(in_hydroNet, up_Dist, dams=True):
   '''Creates a service layer needed to grab stream segments a specified distance upstream of network points.
   This function only needs to be run once for each distance specified. After that, the output layers can be reused
   repeatedly.
   Parameters:
   - in_hydroNet = Input hydrological network dataset (e.g., VA_HydroNet.gdb\HydroNet\HydroNet_ND)
   - up_Dist = The distance (in map units) to traverse upstream from a point along the network
   - dams = Whether dams should be included as barriers in the network analysis layer
   '''
   arcpy.CheckOutExtension("Network")
   
   # Set up some variables
   descHydro = arcpy.Describe(in_hydroNet)
   nwDataset = descHydro.catalogPath
   catPath = os.path.dirname(nwDataset) # This is where hydro layers will be found
   hydroDir = os.path.dirname(catPath)
   hydroDir = os.path.dirname(hydroDir) # This is where output layer files will be saved

   # Output layer name to reflect the specified upstream distance
   lyrUpTrace = hydroDir + os.sep + "naUpTrace_%s.lyr" %str(int(round(up_Dist)))
   
   # Upstream trace with break at specified distance
   r = "NoPipelines;NoUndergroundConduits;NoEphemeral;NoCoastline"
   printMsg('Creating upstream service layers...')
   restrictions = r + ";" + "FlowUpOnly"
   serviceLayer = arcpy.MakeServiceAreaLayer_na(in_network_dataset=nwDataset,
      out_network_analysis_layer = "naUpTrace", 
      impedance_attribute = "Length", 
      travel_from_to = "TRAVEL_FROM", 
      default_break_values = up_Dist, 
      polygon_type = "NO_POLYS", 
      merge = "NO_MERGE", 
      nesting_type = "RINGS", 
      line_type = "TRUE_LINES_WITH_MEASURES", 
      overlap = "OVERLAP",
      split = "SPLIT", 
      excluded_source_name = "", 
      accumulate_attribute_name = "Length", 
      UTurn_policy = "ALLOW_UTURNS", 
      restriction_attribute_name = restrictions, 
      polygon_trim = "TRIM_POLYS", 
      poly_trim_value = "100 Meters", 
      lines_source_fields = "LINES_SOURCE_FIELDS", 
      hierarchy = "NO_HIERARCHY", 
      time_of_day = "")
   
   if dams:
      nwLines = catPath + os.sep + "NHDLine"
      qry = "FType = 343"  # DamWeir only
      arcpy.MakeFeatureLayer_management(nwLines, "lyr_DamWeir", qry)
      in_Lines = "lyr_DamWeir"

      # Add dam barriers to service layer
      printMsg('Adding dam barriers to service layer...')
      barriers = arcpy.AddLocations_na(in_network_analysis_layer = "naUpTrace",
         sub_layer = "Line Barriers",
         in_table = in_Lines,
         field_mappings = "Name Permanent_Identifier #",
         search_tolerance = "#",
         sort_field = "",
         search_criteria = "NHDFlowline SHAPE_MIDDLE_END;HydroNet_ND_Junctions NONE",
         # match_type = "#",
         append = "CLEAR",
         # snap_to_position_along_network = "#",
         # snap_offset = "#",
         # exclude_restricted_elements = "#",
         search_query = "NHDFlowline #;HydroNet_ND_Junctions #")

   # save
   printMsg('Saving service layer to %s...' %lyrUpTrace)      
   arcpy.SaveToLayerFile_management("naUpTrace", lyrUpTrace) 

   if dams:
      del barriers
   del serviceLayer
   
   arcpy.CheckInExtension("Network")
   
   return lyrUpTrace


def GetCatchArea_hw(in_Points, in_lyrUpTrace, in_Catchment, out_Lines, out_CatchArea, out_Scratch = arcpy.env.scratchGDB):
   '''Loads point(s), solves the upstream service layer to get lines, grabs catchments intersecting lines.
    Outputs are two feature classes (dissolved lines and catchments, one feature per input point).
   Parameters:
   - in_Points = Input feature class representing sample point(s) along network
   - in_lyrUpTrace = Network Analyst service layer set up to run upstream
   - in_Catchment = Catchment polygons for flowlines used in the network
   - out_Lines = Output lines representing upstream flow to a specified distance from point
   - out_CatchArea = Output polygons covering catchments intersecting output lines
   - out_Scratch = Geodatabase to contain intermediate outputs
   '''
   
   arcpy.CheckOutExtension("Network")

   # get point field info, add new field storing ID
   ptid = str([f.name for f in arcpy.Describe(in_Points).Fields][0])
   ptid_join = ptid + '_in_Points'
   if ptid_join not in [str(f.name) for f in arcpy.Describe(in_Points).Fields]:
      print('Adding new field `' + ptid_join + '` to points as a unique ID...')
      arcpy.AddField_management(in_Points, ptid_join, "LONG")
      arcpy.CalculateField_management(in_Points, ptid_join, '!'+ptid+'!', "PYTHON")
   else:
      print('Using existing field `' + ptid_join + '` as a unique point ID...')

   # timestamp
   t0 = datetime.now()
   
   # Set up some variables
   if out_Scratch == "in_memory":
      # recast to save to disk, otherwise there is no OBJECTID field for queries as needed
      out_Scratch = arcpy.env.scratchGDB
   printMsg('Casting strings to layer objects...')
   in_upTrace = arcpy.mapping.Layer(in_lyrUpTrace)
   upLines = out_Scratch + os.sep + 'upLines'
  
   # Load point(s) as facilities into service layer; search distance 500 meters
   printMsg('Loading points into service layer...')
   naPoints = arcpy.AddLocations_na(in_network_analysis_layer = in_upTrace, 
      sub_layer = "Facilities", 
      in_table = in_Points, 
      field_mappings = "Name " + ptid_join + " #",
      search_tolerance = "500 Meters",
      sort_field = "", 
      search_criteria = "NHDFlowline SHAPE;HydroNet_ND_Junctions NONE", 
      match_type = "MATCH_TO_CLOSEST", 
      append = "CLEAR", 
      snap_to_position_along_network = "SNAP", 
      snap_offset = "0 Meters", 
      exclude_restricted_elements = "EXCLUDE", 
      search_query = "NHDFlowline #;HydroNet_ND_Junctions #")
   printMsg('Completed point loading.')
   
   del naPoints
  
   # Solve upstream service layer; save out lines and updated layer
   printMsg('Solving service layer...')
   arcpy.Solve_na(in_network_analysis_layer = in_upTrace, 
      ignore_invalids = "SKIP", 
      terminate_on_solve_error = "TERMINATE", 
      simplification_tolerance = "")
   inLines = arcpy.mapping.ListLayers(in_upTrace, "Lines")[0]
   printMsg('Saving out lines...')
   arcpy.CopyFeatures_management(inLines, upLines)
   arcpy.RepairGeometry_management(upLines, "DELETE_NULL")
   printMsg('Saving updated %s service layer to %s...' %(in_upTrace, in_lyrUpTrace))
   arcpy.SaveToLayerFile_management(in_upTrace, in_lyrUpTrace)

   # Add ID field from original points to facilities
   joinPt = arcpy.CopyFeatures_management(arcpy.mapping.ListLayers(in_upTrace, "Facilities")[0],
                                          out_Scratch + os.sep + "in_Points")
   arcpy.AddField_management(joinPt, ptid_join, "LONG")
   arcpy.CalculateField_management(joinPt, ptid_join, "!Name!", "PYTHON")

   # output lines datasets, with original points ID attached
   # Note: Facilty ID in Lines == ObjectID in Facilities. The join adds the unique point ID field to Lines.
   printMsg('Dissolving line networks...')
   arcpy.JoinField_management(upLines, "FacilityID", joinPt, "ObjectID", ptid_join)
   arcpy.CopyFeatures_management(upLines, out_Lines + '_full')
   lines_diss = arcpy.Dissolve_management(upLines, out_Lines, dissolve_field=ptid_join)

   # get/dissolve catchments associated with lines
   printMsg('Getting and dissolving catchments...')
   cat_lyr = arcpy.MakeFeatureLayer_management(in_Catchment, where_clause="SourceFC <> 'NHDPlusSink'")
   arcpy.SelectLayerByLocation_management(cat_lyr, "INTERSECT", lines_diss)
   catch_all = arcpy.SpatialJoin_analysis(cat_lyr, lines_diss,
                              out_feature_class=out_CatchArea + '_full',
                              join_operation="JOIN_ONE_TO_MANY",
                              join_type="KEEP_COMMON",
                              match_option="INTERSECT")
   del cat_lyr
   arcpy.Dissolve_management(catch_all, out_CatchArea, dissolve_field=ptid_join)

   # get unaasociated catchments
   assoc = ','.join([str(f[0]) for f in arcpy.da.SearchCursor(out_CatchArea, ptid_join)])
   query = ptid + " NOT IN (" + assoc + ")"
   pt_lyr = arcpy.MakeFeatureLayer_management(in_Points, where_clause=query)

   if (int(arcpy.GetCount_management(pt_lyr)[0]) > 0):
      printMsg('Adding catchments for unassociated points...')
      arcpy.AddField_management(pt_lyr, ptid_join, "LONG")
      arcpy.CalculateField_management(pt_lyr, ptid_join, '!' + ptid + '!', "PYTHON")
      cat_lyr = arcpy.MakeFeatureLayer_management(in_Catchment)
      arcpy.SelectLayerByLocation_management(cat_lyr, "INTERSECT", pt_lyr)
      arcpy.SpatialJoin_analysis(cat_lyr, pt_lyr, 'catUnassoc', join_operation="JOIN_ONE_TO_MANY",
                              join_type="KEEP_COMMON", match_option="INTERSECT")
      arcpy.Append_management('catUnassoc', out_CatchArea, "NO_TEST")
      arcpy.Append_management('catUnassoc', out_CatchArea + '_full', "NO_TEST")
      arcpy.Delete_management('catUnassoc')
      del pt_lyr, cat_lyr

   # timestamp
   t1 = datetime.now()
   ds = GetElapsedTime(t0, t1)
   printMsg('Completed function. Time elapsed: %s' % ds)

   arcpy.CheckInExtension("Network")
   
   return (out_Lines, out_CatchArea)


def main():
   # Set up variables
   # arcpy.CreateFileGDB_management(r'E:\git\HealthyWaters\inputs\watersheds', 'hw_watershed_nodams.gdb')
   arcpy.env.workspace = r'E:\git\HealthyWaters\inputs\watersheds\hw_watershed_nodams.gdb'
   in_hydroNet = r'E:\git\HealthyWaters\inputs\watersheds\VA_HydroNet.gdb\HydroNet\HydroNet_ND'
   in_Points0 = r'E:\git\HealthyWaters\inputs\HW_working.gdb\INSTAR_Samples'
   in_Catchment = r'E:\git\HealthyWaters\inputs\watersheds\Proc_NHDPlus_HR.gdb\NHDPlusCatchment_Merge_valam'
   dams = False  # whether to include dams as barriers or not

   # copy points to geodatabase
   in_Points = os.path.basename(in_Points0).replace('.shp', '')
   arcpy.CopyFeatures_management(in_Points0, in_Points)

   # distances to loop over, in miles
   miles = [1, 2, 3, 4, 5, 330]  # 330 covers entire watershed

   # loop over distances
   for mi in miles:
      up_Dist = mi * 1609.34
      out_Lines = 'hw_Flowline_' + str(mi) + 'mile'
      out_CatchArea = 'hw_CatchArea_' + str(mi) + 'mile'
      in_lyrUpTrace = MakeServiceLayer_hw(in_hydroNet, up_Dist, dams)
      GetCatchArea_hw(in_Points, in_lyrUpTrace, in_Catchment, out_Lines, out_CatchArea)

if __name__ == '__main__':
   main()
