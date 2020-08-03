#----------------------------------------------------
# Name: Catchment Zonal summaries
#  This script summarizes metrics (land cover, crops, road crossings, pollutants, etc.) within catchments.
#  The general workflow is to (1) loop over catchment types (subCatchments and catchments), (2) loop over years (for
#  multi-temporal datasets), (3) loop over stream buffers, and (4) loop over datasets in a group processed in the same
#  way (e.g. land cover). Summary metrics are ouptut to 'Catchment geodatabases', one for each temporal group (2016,
#  2011, 2006, 2001, and noYear, for those datasets not tied to a specific year).
# Version: ArcPro / Python 3+
# Date Created: 3-5-20
# Authors: Hannah Huggins / David Bucklin
#----------------------------------------------------

import arcpy
import os
# Check out the spatial extension
arcpy.CheckOutExtension("Spatial")


def add_zs(in_Zone, zone_field, in_raster, out_Tab, stat="MEAN", fld_name=None, mask=None):
   """This function is a wrapper around ZonalStatisticsAsTable, allowing to set a mask just for the summary,
   and change the name of the summary field."""

   print('Zonal summarizing ' + stat + ' of raster `' + in_raster + '` in zones `' + in_Zone + '`...')
   if mask:
      envmask = arcpy.env.mask
      arcpy.env.mask = mask
   arcpy.sa.ZonalStatisticsAsTable(in_Zone, zone_field, in_raster, out_Tab, "DATA", stat)
   if fld_name:
      arcpy.AlterField_management(out_Tab, stat, fld_name, clear_field_alias=True)
   if mask:
      arcpy.env.mask = envmask
   return out_Tab


def cat_join(cat_tab, cat_id, join_tab, join_id, fld_suffix=""):
   """Joins summarized table to master catchment feature class, by selecting fields to
   join (based on the field prefix), optionally adding a suffix (i.e. buffer size) to the joined field names, and
   deleting join_tab following the join."""

   flds = [a.name for a in arcpy.ListFields(join_tab)]
   # TODO: update prefixes as needed
   fld = [f for f in flds if f.startswith(('perc', 'area', 'dens', 'leng', 'num', 'freq', 'sum', 'avg'))]
   if fld_suffix != "":
      for f in fld:
         arcpy.AlterField_management(join_tab, f, f + fld_suffix, clear_field_alias=True)
      fld = [f + fld_suffix for f in fld]
   print('Joining fields : [' + ', '.join(fld) + ']')
   if len(fld) == 0:
      print('No fields to join.')
      return
   fld_exist = [f.name for f in arcpy.ListFields(cat_tab) if f.name in fld]
   if len(fld_exist) > 0:
      print("Removing existing fields...")
      for f in fld_exist:
         arcpy.DeleteField_management(cat_tab, f)
   arcpy.JoinField_management(cat_tab, cat_id, join_tab, join_id, fld)
   arcpy.Delete_management(join_tab)
   return cat_tab


def add_NLCD_LCmetrics(in_Zone, out_Tab, in_LandCover, zone_field='Value', class_field='Value'):
   """This function creates a table based on the Tabulate Area tool and adds landcover metrics.
   Parameter:
   in_Zone = The input raster/features that defines the zones where the tabulate area functions.
   out_Tab = output table
   in_LandCover = The input dataset that defines the classes that have their areas summarized in the zones.
   zone_field = Field in in_Zone that defines the unique zones.
   class_field = Field in in_Landcover with class values."""

   # Specify fields for rasters
   print('Tabulating values of field `' + class_field + '` for `' + in_LandCover + '` in zones `' + in_Zone + '`...')
   # Tabulate area
   arcpy.sa.TabulateArea(in_Zone, zone_field, in_LandCover, class_field, out_Tab)
   nlcd_val = ['11', '21', '22', '23', '24', '31', '41', '42', '43', '52', '71', '81', '82', '90', '95']
   all_nm = ['VALUE_' + a for a in nlcd_val]
   tab_nm = [a.name for a in arcpy.ListFields(out_Tab)]
   # add missing fields (can happen for less common land covers in small watersheds)
   miss = [a for a in all_nm if a not in tab_nm]
   for m in miss:
      print('Adding missing field `' + m + '`.')
      arcpy.AddField_management(out_Tab, m, 'LONG')
      arcpy.CalculateField_management(out_Tab, m, '0')
   # set areaWater field name
   arcpy.AlterField_management(out_Tab, 'VALUE_11', 'areaWater', clear_field_alias=True)
   # Add and calculate areaLand field
   arcpy.AddField_management(out_Tab, "areaLand", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "areaLand", "!VALUE_21! + !VALUE_22! + !VALUE_23! + !VALUE_24! + !VALUE_31! + !VALUE_41! + !VALUE_42! + !VALUE_43! + !VALUE_52! + !VALUE_71! + !VALUE_81! + !VALUE_82! + !VALUE_90! + !VALUE_95!")
   # Add and calculate percNAT field
   arcpy.AddField_management(out_Tab, "percNAT", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percNAT", "((!VALUE_41! + !VALUE_42! + !VALUE_43! + !VALUE_52! + !VALUE_71! + !VALUE_90! + !VALUE_95!) / !areaLand!) * 100")
   # Add and calculate percSHBHRB field
   arcpy.AddField_management(out_Tab, "percSHBHRB", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percSHBHRB", "((!VALUE_52! + !VALUE_71!) / !areaLand!) * 100")
   # Add and calculate percFORWET field
   arcpy.AddField_management(out_Tab, "percFORWET", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percFORWET", "((!VALUE_41! + !VALUE_42! + !VALUE_43! + !VALUE_90! + !VALUE_95!) / !areaLand!) * 100")
   # Add and calculate percAGR field
   arcpy.AddField_management(out_Tab, "percAGR", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percAGR", "((!VALUE_81! + !VALUE_82!) / !areaLand!) * 100")
   # Add and calculate percPSTR field
   arcpy.AddField_management(out_Tab, "percPSTR", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percPSTR", "((!VALUE_81!) / !areaLand!) * 100")
   # Add and calculate percCROP field
   arcpy.AddField_management(out_Tab, "percCROP", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percCROP", "((!VALUE_82!) / !areaLand!) * 100")
   # Add and calculate percBARE field
   arcpy.AddField_management(out_Tab, "percBARE", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percBARE", "((!VALUE_31!) / !areaLand!) * 100")
   # Add and calculate percDEV field
   arcpy.AddField_management(out_Tab, "percDEV", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percDEV", "((!VALUE_21! + !VALUE_22! + !VALUE_23! + !VALUE_24!) / !areaLand!) * 100")
   return out_Tab


def make_catGDB(gdb, cat, subCat):

   if not arcpy.Exists(cat) or not arcpy.Exists(subCat):
      print('Catchment/subCatchment feature classes do not exist.')
      return
   if not os.path.exists(gdb):
      print('Making new geodatabase `' + gdb + '`...')
      arcpy.CreateFileGDB_management(os.path.dirname(gdb), os.path.basename(gdb))
      arcpy.CopyFeatures_management(cat, gdb + os.sep + os.path.basename(cat))
      arcpy.CopyFeatures_management(subCat, gdb + os.sep + os.path.basename(subCat))
      print('Geodatabase and catchment feature classes created.')
   else:
      print('Geodatabase `' + gdb + '` already exists, will add metrics to existing feature classes.')
   return


### HEADER FOR ALL PROCESSES

# Source geodatabase for input rasters
src_gdb = r'E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb'

# Template raster. Note that mask and extent should NOT be set. Masking is handled by-variable
template_raster = r'E:\git\HealthyWaters\inputs\snap_raster\HW_templateRaster.tif'
arcpy.env.overwriteOutput = True
arcpy.env.cellSize = template_raster
arcpy.env.snapRaster = template_raster
arcpy.env.outputCoordinateSystem = template_raster
arcpy.env.parallelProcessingFactor = "75%"
# Workspaces are created and set throughout the workflow. Do not set here.

# 'Buffer' (flow distance) raster prefix. See StreamBufferZones.py
fdbuff = 'L:/David/GIS_data/NHDPlus_HR/NHDPlus_HR_FlowLength.gdb/flowDistance'
# List of stream buffer sizes. The empty string value `''` generates metrics for full catchments
buffs = ['', '_100m', '_250m', '_500m']
# NLCD years, for multi-temporal variables
years = ['2001', '2006', '2011', '2016']

# Catchment feature class
in_Catchments0 = src_gdb + os.sep + 'NHDPlusCatchment_metrics'
# unique ID for catchments
catID = 'catID'
# Rasterized version of catchemnts. This is in ProcessRasters.py, with some manual editing involved; see notes there.
in_Catchments = src_gdb + os.sep + 'NHDPlusCatchment_raster'
if catID not in [a.name for a in arcpy.ListFields(in_Catchments0)]:
   print('Missing catID field...')
if not arcpy.Exists(in_Catchments):
   print('Missing catchment raster...')

# SubCatchment feature class. Will be converted to raster
in_subCatchments0 = r"E:\git\HealthyWaters\inputs\watersheds\hw_watershed_nodams_20200528.gdb\hw_Flowline_subCatchArea"
# unique ID for sub-Catchments = same as unique INSTAR ID.
subcatID = 'OBJECTID_in_Points'
# make subCatchment zone rasters/features (needs re-run if the subCatchments are updated)
in_subCatchments = src_gdb + os.sep + 'subCat_rast'
if not arcpy.Exists(in_subCatchments):
   arcpy.PolygonToRaster_conversion(in_subCatchments0, subcatID, in_subCatchments)
   for b in buffs[1:4]:
      print(b)
      out = fdbuff + b + '_subCatRast'
      arcpy.sa.ExtractByMask(in_subCatchments, fdbuff + b + '_catRast').save(out)
      out = fdbuff + b + '_subCatFeat'
      arcpy.Clip_analysis(in_subCatchments0, fdbuff + b + '_catFeat', out)

# List of catchment/subCatchment properties:
#  [zones data, unique ID field, name for outputs, zone ID field, name of join dataset]
# Processing is the same for both datasets, so setting up this list allows to loop over the two datasets.
cattype = [[in_subCatchments, subcatID, 'subCatchments', 'Value', os.path.basename(in_subCatchments0)],
           [in_Catchments, catID, 'Catchments', 'Value', os.path.basename(in_Catchments0)]]

# General loop workflow:
   # 1. over catchment type
   # 2. over years (multi-temporal datasets)
   # 3. over datasets (where multiple datasets are processed in the same way)
   # 4. over stream buffers (alters the zones dataset)
# Step 1 is always used, while steps 2-4 are dependent on the dataset.

### END HEADER


### NLCD (land cover, impervious, canopy)

for t in cattype:
   c = t[0]
   cid = t[1]
   cnm = t[2]
   czn = t[3]
   cjn = t[4]
   print('Working on ' + cnm + '...')

   ### NLCD Variables: loop over years
   for year in years:

      # Create file GDB (one for each year), catchment copies
      ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_' + year + '.gdb'
      make_catGDB(ws, in_Catchments0, in_subCatchments0)
      arcpy.env.workspace = ws

      # Set land cover dataset / mask, by year
      in_LandCover = src_gdb + os.sep + "lc_" + year + "_proj"
      in_canopy = src_gdb + os.sep + "treecan_" + year + "_proj"
      in_imp = src_gdb + os.sep + "imp_" + year + "_proj"
      mask = src_gdb + os.sep + "lc_" + year + "_nowater"

      # Loop over buffers
      for buff in buffs:
         print('Working on year ' + year + ' for buffer size: ' + buff)
         if buff != "":
            # change zone raster to the buffer-only versions
            if cnm == 'subCatchments':
               c1 = fdbuff + buff + '_subCatRast'
            else:
               c1 = fdbuff + buff + '_catRast'
         else:
            c1 = c

         # Calculate and join metrics
         add_NLCD_LCmetrics(c1, 'lc_table_' + cnm + buff, in_LandCover, zone_field=czn)
         cat_join(cjn, cid, 'lc_table_' + cnm + buff, czn, buff)
         # NOTE: no NLCD canopy data for 2001, 2006
         if arcpy.Exists(in_canopy):
            add_zs(c1, czn, in_canopy, 'canopy_' + cnm + buff, "MEAN", 'percCAN', mask)
            cat_join(cjn, cid, 'canopy_' + cnm + buff, czn, buff)
         add_zs(c1, czn, in_imp, 'imp_' + cnm + buff, "MEAN", 'percIMP', mask)
         cat_join(cjn, cid, 'imp_' + cnm + buff, czn, buff)
# end NLCD


# Zonal summarizing SUM of raster `G:\SWAPSPACE\hwProducts_20200731.gdb\SedYld_2001` in zones `E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb\subCat_rast`...


### Pollutant loads
# For N/P/S, Unit is mg.
# For Sediment yields, there are two versions (SedYld and altSedYld, using different calculations).
# pollutant raster geodatabase
poll_gdb = r'G:\SWAPSPACE\hwProducts_20200731.gdb'

for t in cattype:
   c = t[0]
   cid = t[1]
   cnm = t[2]
   czn = t[3]
   cjn = t[4]
   print('Working on ' + cnm + '...')

   ### NLCD Variables: loop over years
   for year in years:

      # get list of datasets, by year
      ls = [[poll_gdb + os.sep + 'LocMass_Nitrogen_' + year, 'sumN'],
            [poll_gdb + os.sep + 'LocMass_Phosphorus_' + year, 'sumP'],
            [poll_gdb + os.sep + 'LocMass_SuspSolids_' + year, 'sumS'],
            [poll_gdb + os.sep + 'SedYld_' + year, 'sumSED'],
            [poll_gdb + os.sep + 'altSedYld_' + year, 'sumSEDALT'],
            [poll_gdb + os.sep + 'runoffDepth_' + year, 'depRUNOFF']]
      # Create file GDB (one for each year), catchment copies
      ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_' + year + '.gdb'
      make_catGDB(ws, in_Catchments0, in_subCatchments0)
      arcpy.env.workspace = ws

      for i in ls:
         r = i[0]
         if not arcpy.Exists(r):
            print('Dataset `' + r + '` does not exist.')
            continue
         varname = i[1]
         for buff in buffs:
            print('Working on `' + varname + '` for buffer size: ' + buff)
            if buff != "":
               # change zone raster to the buffer-only versions
               if cnm == 'subCatchments':
                  c1 = fdbuff + buff + '_subCatRast'
               else:
                  c1 = fdbuff + buff + '_catRast'
            else:
               c1 = c
            # Get zonal statistics (SUM, no mask)
            add_zs(c1, czn, r, varname, "SUM", varname)
            cat_join(cjn, cid, varname, czn, buff)


### Non year-specific variables

# Set up geodatabase
ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_noYear.gdb'
make_catGDB(ws, in_Catchments0, in_subCatchments0)
arcpy.env.workspace = ws


### Crop frequencies
# Loop over crop frequency rasters
ls = [[src_gdb + os.sep + 'pasturefreq', 'freqPASTURE'],
      [src_gdb + os.sep + 'cornfreq', 'freqCORN'],
      [src_gdb + os.sep + 'cottonfreq', 'freqCOTTON'],
      [src_gdb + os.sep + 'soyfreq', 'freqSOY'],
      [src_gdb + os.sep + 'wheatfreq', 'freqWHEAT']]
# These use the open water mask; use the NLCD 2016 version
mask = src_gdb + os.sep + "lc_2016_nowater"
for t in cattype:
   c = t[0]
   cid = t[1]
   cnm = t[2]
   czn = t[3]
   cjn = t[4]
   print('Working on ' + cnm + '...')
   for i in ls:
      r = i[0]
      varname = i[1]
      for buff in buffs:
         print('Working on `' + r + '` for buffer size: ' + buff)
         if buff != "":
            # change zone raster to the buffer-only versions
            if cnm == 'subCatchments':
               c1 = fdbuff + buff + '_subCatRast'
            else:
               c1 = fdbuff + buff + '_catRast'
         else:
            c1 = c

         # Get zonal statistics
         add_zs(c1, czn, crop, r, "MEAN", varname, mask)
         cat_join(cjn, cid, r, czn, buff)


### Roads
# NOTE: These are all-vector analyses. Do not use the rasterized catchments
# Set up geodatabase
ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_noYear.gdb'
make_catGDB(ws, in_Catchments0, in_subCatchments0)
arcpy.env.workspace = ws

# Roads feature class
rcl = src_gdb + os.sep + 'rcl'
# Road crossings (point) feature class
rdcrs = src_gdb + os.sep + 'rdcrs1'
stream = r'L:\David\GIS_data\NHDPlus_HR\NHDPlus_HR_Virginia.gdb\NHDFlowline'

# Loop over catchments
for t in cattype:
   # These are vector analyses, so change the zones to the original features instead of catchment zone rasters
   if t[2] == 'Catchments':
      c = in_Catchments0
   else:
      c = in_subCatchments0
   cid = t[1]
   cnm = t[2]
   czn = t[3]
   cjn = t[4]
   print('Working on ' + cnm + '...')

   # Roads: length (km) and density (km per square km)
   out = 'road_length'
   for buff in buffs:
      # These use the feature buffers. NOTE: Stream-area is included in the buffer (unlike rasters analyses)
      print('Working on road length/density for buffer size: ' + buff)
      if buff != "":
         if cnm == 'subCatchments':
            c1 = fdbuff + buff + '_subCatFeat'
         else:
            c1 = fdbuff + buff + '_catFeat'
      else:
         c1 = c

      if 'area_sqm' not in [a.name for a in arcpy.ListFields(c1)]:
         arcpy.AddField_management(c1, 'area_sqm', 'DOUBLE')
         arcpy.CalculateGeometryAttributes_management(c1, [['area_sqm', 'AREA']], area_unit='SQUARE_METERS')

      # Intersect and dissolve by catchment
      arcpy.PairwiseIntersect_analysis([c1, rcl], 'cat_rcl', 'NO_FID', output_type='LINE')
      # Dissolve is needed to remove overlapping roads
      arcpy.PairwiseDissolve_analysis('cat_rcl', 'cat_rcl_diss0', [cid, 'area_sqm'])
      # summarize road length and area
      arcpy.Statistics_analysis('cat_rcl_diss0', out, [['Shape_Length', 'SUM'], ['area_sqm', 'MAX']], cid)
      arcpy.AddField_management(out, 'lengRD', 'DOUBLE')
      arcpy.CalculateField_management(out, 'lengRD', '!SUM_Shape_Length! / 1000')
      arcpy.AddField_management(out, 'densRD', 'DOUBLE')
      arcpy.CalculateField_management(out, 'densRD', '!lengRD! / (!MAX_area_sqm! / 1000000)')
      cat_join(cjn, cid, out, cid, buff)

   # Road crossings: number and density (number per sq km)
   out = 'roadcross_count'
   print('Calculating road crossing density for ' + cjn + '...')
   arcpy.SpatialJoin_analysis(rdcrs, c1, 'rdcrs_cat', "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="INTERSECT")
   arcpy.Statistics_analysis('rdcrs_cat', out, [[cid, 'COUNT'], ['area_sqm', 'MAX']], cid)
   arcpy.AlterField_management(out, 'COUNT_' + cid, 'numRDCRS', clear_field_alias=True)
   arcpy.AddField_management(out, 'densRDCRS', 'DOUBLE')
   arcpy.CalculateField_management(out, 'densRDCRS', '!numRDCRS! / (!MAX_area_sqm! / 1000000)', "PYTHON3")
   cat_join(cjn, cid, out, cid)

del_ls = ['cat_rcl', 'cat_rcl_diss0', 'rdcrs_cat']
for d in del_ls:
   arcpy.Delete_management(d)


### Add new variables here
