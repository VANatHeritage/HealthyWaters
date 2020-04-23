# ----------------------------------------------------------------------------------------
# HealthyWaters.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2020-01-06
# Last Edit: 2020-04-23
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
# import Helper
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
   catPath = os.path.dirname(nwDataset)  # This is where hydro layers will be found
   hydroDir = os.path.dirname(os.path.dirname(catPath))  # This is where output layer files will be saved

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


def GetNetworks_hw(in_Points, in_lyrUpTrace, in_hydroNet, out_Lines, in_Catchment = None, out_Scratch = arcpy.env.scratchGDB):
   '''Loads point(s), solves the upstream service layer to get lines, grabs catchments intersecting lines.
    Outputs are two feature classes (dissolved lines and catchments, one feature per input point).
   Parameters:
   - in_Points = Input feature class representing sample point(s) along network
   - in_lyrUpTrace = Network Analyst service layer set up to run upstream
   - in_hydroNet = Hydrological network used to build service layer. Must Contain NHDFlowline feature class
   - out_Lines = Output lines representing upstream flow to a specified distance from point
   - in_Catchment = Input catchment polygons layer, matching flowlines from in_hydroNet. Optional: if given, the
      catchments for the network will be output, using the naming scheme `[out_Lines]_catchArea`.
   - out_Scratch = Geodatabase to contain intermediate outputs
   '''
   
   arcpy.CheckOutExtension("Network")
   nhdFlow = os.path.dirname(in_hydroNet) + os.sep + 'NHDFlowline'
   if not arcpy.Exists(nhdFlow):
      return 'NHDFlowine file does not exist in network dataset `' + in_hydroNet + '`.'

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
  
   # Load point(s) as facilities into service layer; search distance 50 meters
   printMsg('Loading points into service layer...')
   naPoints = arcpy.AddLocations_na(in_network_analysis_layer = in_upTrace, 
      sub_layer = "Facilities", 
      in_table = in_Points, 
      field_mappings = "Name " + ptid_join + " #",
      search_tolerance = "50 Meters",
      sort_field = ptid_join,
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
   in_Lines = arcpy.mapping.ListLayers(in_upTrace, "Lines")[0]
   printMsg('Saving out lines...')
   arcpy.CopyFeatures_management(in_Lines, upLines)
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

   # first select lines from NHDFlowline to join. This makes the join faster.
   oids = [str(int(a[0])) for a in arcpy.da.SearchCursor(upLines, "SourceOID")]
   query = 'OBJECTID IN (' + ','.join(oids) + ')'
   nhdFlow_lyr = arcpy.MakeFeatureLayer_management(nhdFlow, where_clause=query)
   arcpy.JoinField_management(upLines, "SourceOID", nhdFlow_lyr, "OBJECTID", "NHDPlusID")

   arcpy.CopyFeatures_management(upLines, out_Lines + '_full')
   arcpy.Dissolve_management(upLines, out_Lines, dissolve_field=ptid_join)

   # Get catchments, if in_Catchment is given
   if in_Catchment:
      out_CatchArea = out_Lines + '_catchArea'
      out_Cat = GetCatchments_hw(out_Lines + '_full', in_Catchment, out_CatchArea, in_Points, ptid_join)

   # timestamp
   t1 = datetime.now()
   ds = GetElapsedTime(t0, t1)
   printMsg('Completed function. Time elapsed: %s' % ds)

   arcpy.CheckInExtension("Network")

   return out_Lines


def GetCatchments_hw(in_Lines, in_Catchment, out_CatchArea, in_Points, ptid_join="OBJECTID_in_Points"):

   # Use NHDPlusID to build a query. NHDPlusID is necessary for this.
   oids = set([str(int(a[0])) for a in arcpy.da.SearchCursor(in_Lines, "NHDPlusID")])
   oids = list(oids)
   query = "NHDPlusID IN (" + ','.join(oids) + ")"
   cat_lyr = arcpy.MakeFeatureLayer_management(in_Catchment, where_clause=query)

   # OLD method. Not necessary anymore
   # cat_lyr = arcpy.MakeFeatureLayer_management(in_Catchment, where_clause="SourceFC <> 'NHDPlusSink'")
   # arcpy.SelectLayerByLocation_management(cat_lyr, "INTERSECT", in_Lines)

   # get/dissolve catchments associated with lines
   print('Getting associated catchments...')
   catch_all = arcpy.SpatialJoin_analysis(cat_lyr, in_Lines,
                                          out_feature_class=arcpy.env.scratchGDB + os.sep + 'cat_sj',
                                          join_operation="JOIN_ONE_TO_MANY",
                                          join_type="KEEP_COMMON",
                                          match_option="INTERSECT")
   # Only want catchments matching corresponding flowlines
   catch_full = arcpy.MakeFeatureLayer_management(catch_all, where_clause='NHDPlusID = NHDPlusID_1')
   arcpy.CopyFeatures_management(catch_full, out_CatchArea + '_full')

   # Sub-catchment routine
   out_subCat = 'hw_Flowline_subCatchArea'
   if not arcpy.Exists(out_subCat):
      # Only needs to run once. Uses a fixed name so it can be reused for other catchments generated in the gdb.
      GetSubCatchments_hw(in_Lines, out_CatchArea + '_full', out_subCat, ptid_join, 'F:/David/GIS_data/NHDPlus_HR')
   print("Replacing initial catchment with sub-catchment...")
   catch_full = arcpy.MakeFeatureLayer_management(out_CatchArea + '_full')
   nid_oid = [[ptid_join + " = " + str(a[0]), "NHDPlusID = " + str(int(a[1]))] for a in arcpy.da.SearchCursor(out_subCat, [ptid_join, "NHDPlusID"])]
   # make query for pairwise selection of catchments
   query = '(' + ') OR ('.join([' AND '.join(b) for b in nid_oid]) + ')'
   arcpy.SelectLayerByAttribute_management(catch_full, "NEW_SELECTION", query)
   arcpy.DeleteRows_management(catch_full)
   arcpy.Append_management(out_subCat, out_CatchArea + '_full', "NO_TEST")
   del cat_lyr
   del catch_full
   # end Sub-catchment routine

   print('Dissolving catchments...')
   arcpy.Dissolve_management(out_CatchArea + '_full', out_CatchArea, dissolve_field=ptid_join)

   # point layer OID
   ptid = ptid_join.replace('_in_Points', '')

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

   return out_CatchArea


def GetSubCatchments_hw(in_Lines, in_CatchArea, out_subCatch,
                        ptid_join="OBJECTID_in_Points", fdr_src='L:/David/GIS_data/NHDPlus_HR'):

   print("Generating sub-catchment for initial pour points...")
   arcpy.CheckOutExtension("Spatial")
   temp = arcpy.env.scratchGDB
   arcpy.env.outputCoordinateSystem = in_CatchArea
   arcpy.env.extent = in_CatchArea

   # full flowlines layer
   flow = arcpy.MakeFeatureLayer_management(in_Lines)
   # full catchments layer
   cat = arcpy.MakeFeatureLayer_management(in_CatchArea)
   # unique ID
   uid = ptid_join

   # One Watershed run per HU4
   arcpy.SelectLayerByAttribute_management(flow, "NEW_SELECTION", "FromCumul_Length = 0")
   arcpy.Statistics_analysis(flow, temp + os.sep + 'flowdup', [['NHDPlusID', 'Count']], 'NHDPlusID')
   maxnid = max([a[0] for a in arcpy.da.SearchCursor(temp + os.sep + 'flowdup', 'COUNT_NHDPlusID')])
   if maxnid > 1:
      print('Duplication in starting reach/catchments. This method will not work correctly for those catchments.')
   nid_oid = [[uid + " = " + str(a[0]), "NHDPlusID = " + str(int(a[1]))] for a in arcpy.da.SearchCursor(flow, [uid, "NHDPlusID"])]
   # NOTE: some OIDs do not get a reach, generally since they are at the 'bottom' of the catchment already and do not need a subcatchment.
   # make query for pairwise selection of catchments
   query = '(' + ') OR ('.join([' AND '.join(b) for b in nid_oid]) + ')'
   arcpy.SelectLayerByAttribute_management(cat, "NEW_SELECTION", query)
   arcpy.Dissolve_management(cat, temp + os.sep + "subWatershed_mask", "VPUID")
   sub = temp + os.sep + "subWatershed_mask"
   vpu = [a[0] for a in arcpy.da.SearchCursor(sub, 'VPUID')]
   catvpu = arcpy.MakeFeatureLayer_management(sub)

   # Loop over VPUIDs
   ls_sub = []
   for v in vpu:

      vpuid = v
      arcpy.env.extent = in_CatchArea
      arcpy.SelectLayerByAttribute_management(catvpu, "NEW_SELECTION", "VPUID = '" + str(v) + "'")
      arcpy.CopyFeatures_management(catvpu, temp + os.sep + 'msk')

      if vpuid.startswith('02'):
         fdr = fdr_src + os.sep + "HRNHDPlusRasters" + vpuid + os.sep + 'hydrofix.gdb/fdr_sinkfix'
      else:
         fdr = fdr_src + os.sep + "HRNHDPlusRasters" + vpuid + os.sep + 'fdr.tif'
      arcpy.env.snapRaster = fdr
      arcpy.env.cellSize = fdr
      arcpy.env.outputCoordinateSystem = fdr

      arcpy.env.extent = temp + os.sep + 'msk'
      arcpy.env.mask = temp + os.sep + 'msk'
      # flowlines not necessary to select, since mask will filter them

      # Watershed, convert to polygon
      catsub = temp + os.sep + 'catSub_' + str(vpuid)
      arcpy.PolylineToRaster_conversion(flow, uid, temp + os.sep + 'pp_rast')  # Not Necessary in Pro, which can use lines as Watershed input
      arcpy.sa.Watershed(fdr, temp + os.sep + 'pp_rast', "Value").save(catsub)
      # arcpy.sa.Watershed(fdr, flow, uid).save(catsub)
      arcpy.env.outputCoordinateSystem = in_CatchArea
      arcpy.RasterToPolygon_conversion(catsub, catsub + '_poly0', "NO_SIMPLIFY",
                                       "Value") #,  "MULTIPLE_OUTER_PART")
      arcpy.Dissolve_management(catsub + '_poly0', catsub + '_poly0d', 'gridcode')  # Not Necessary in Pro
      arcpy.Identity_analysis(catsub + '_poly0d', cat, catsub + '_poly1')
      arcpy.Select_analysis(catsub + '_poly1', catsub + '_final', 'gridcode = ' + uid)
      ls_sub.append(catsub + '_final')

   # merge VPUID datasets
   arcpy.env.extent = None
   arcpy.Merge_management(ls_sub, out_subCatch)
   # Reset env variables used in fn
   arcpy.env.outputCoordinateSystem = None
   arcpy.env.snapRaster = None
   arcpy.env.cellSize = None
   arcpy.env.mask = None


def main():
   # Set up variables
   gdb = 'E:/git/HealthyWaters/inputs/watersheds/hw_watershed_nodams_' + DateStamp() + '.gdb'
   # gdb = 'C:/David/scratch/HW_watersheds/hw_watershed_nodams_' + DateStamp() + '.gdb'
   arcpy.CreateFileGDB_management(os.path.dirname(gdb), os.path.basename(gdb))
   arcpy.env.workspace = gdb

   # Use original points, copy to geodatabase
   # NOTE: process points as necessary in ArcGIS, then query (lyr) the ones that should get watersheds (e.g. use_HW = 1)
   in_Points0 = r'E:\git\HealthyWaters\HW_Reaches.gdb\Instar_Reaches_vertend'
   in_Points = os.path.basename(in_Points0).replace('.shp', '')
   lyr = arcpy.MakeFeatureLayer_management(in_Points0, where_clause="use_HW = 1 AND DATE_LOC_C IS NOT NULL")
   arcpy.CopyFeatures_management(lyr, in_Points)

   # Other datasets/settings
   # in_hydroNet = r'E:\git\HealthyWaters\inputs\watersheds\VA_HydroNet.gdb\HydroNet\HydroNet_ND'
   # in_Catchment = r'E:\git\HealthyWaters\inputs\watersheds\Proc_NHDPlus_HR.gdb\NHDPlusCatchment_Merge_valam'
   in_hydroNet = r'F:\David\GIS_data\NHDPlus_HR\VA_HydroNetHR.gdb\HydroNet\HydroNet_ND'
   in_Catchment = r'F:\David\GIS_data\NHDPlus_HR\VA_HydroNetHR.gdb\NHDPlusCatchment'
   dams = False  # whether to include dams as barriers or not

   # distances to loop over, in KM
   kms = [2, 3, 5, 10, 540]

   # loop over distances
   for km in kms:
      up_Dist = km * 1000
      out_Lines = 'hw_Flowline_' + str(km) + 'km'
      in_lyrUpTrace = MakeServiceLayer_hw(in_hydroNet, up_Dist, dams)
      GetNetworks_hw(in_Points, in_lyrUpTrace, in_hydroNet, out_Lines, in_Catchment)

      # Below is now built-in to GetCatchments_hw (which itself is built-in to GetNetworks_hw)
      # Run sub-catchments only if they don't exist
      # out_subCat = 'hw_Flowline_subCatchArea'
      # if not arcpy.Exists(out_subCat):
      #    GetSubCatchments_hw(out_Lines + '_full', out_Lines + '_catchArea_full', out_subCat,
      #                        "OBJECTID_in_Points", fdr_src='F:/David/GIS_data/NHDPlus_HR')
      # NOTE: Make sure to generate catchments, at least for partial watersheds. Because lines get cut in partial
      # watersheds, a partial flowline may show up in the output Network lines, but may not be long enough to actually
      # extend into its own catchment. These catchments will not be in the output catchments (which is good).


if __name__ == '__main__':
   main()
