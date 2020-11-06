#----------------------------------------------------
# Purpose: Catchment Zonal summaries
#
# This script summarizes metrics (land cover, crops, road crossings, pollutants, etc.) within catchments.
# Summary metrics are output to 'catchment geodatabases', one for each temporal group: 2016,
# 2011, 2006, 2001. Datasets not tied to a specific year should be added to the latest temporal gdb (2016).
#
# Catchment variables should begin with one of the following prefixes:
#  perc: represents percent coverage of an attribute (e.g. land cover type)
#  avg: represents an average value of an attribute across the catchment
#  dens: represents the density of an attribute (normalized by square kilometers)
#  area: Raw area value (square meters)
#
# A land-only mask (derived from NLCD) is used for most of the zonal summaries.
#
# Version: ArcPro / Python 3+
# Date Created: 3-5-20
# Authors: Hannah Huggins / David Bucklin
#----------------------------------------------------

# Loads generic functions and variables, and run (one-time) process to create catchment rasters (if not existing)
from Helper_CatchmentMetrics import *

# General loop workflow:
   # 1. over catchment type
   # 2. over years (multi-temporal datasets)
   # 3. over datasets (where multiple datasets are processed in the same way)
   # 4. over stream buffers (alters the zones dataset)
# Step 1 is always used, while steps 2-4 are dependent on the dataset.

### NLCD (land cover, impervious, canopy)
# DONE: redo buffered versions (only) with inclWater rasters.
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
      mask = src_gdb + os.sep + "lc_" + year + "_watermask"

      # Loop over buffers
      for buff in buffs:
         print('Working on year ' + year + ' for buffer size: ' + buff)
         if buff != "":
            # change zone raster to the buffer-only versions
            if cnm == 'subCatchments':
               c1 = fdbuff + buff + '_subCatRast_inclWater'
            else:
               c1 = fdbuff + buff + '_catRast_inclWater'
         else:
            c1 = c

         # Calculate and join metrics
         add_NLCD_LCmetrics(c1, 'tmp_lc_table', in_LandCover, zone_field=czn)
         cat_join(cjn, cid, 'tmp_lc_table', czn, buff)
         # NOTE: no NLCD canopy data for 2001, 2006
         if arcpy.Exists(in_canopy):
            add_zs(c1, czn, in_canopy, 'tmp_canopy', "MEAN", 'percCAN', mask)
            cat_join(cjn, cid, 'tmp_canopy', czn, buff)
         add_zs(c1, czn, in_imp, 'tmp_imp', "MEAN", 'percIMP', mask)
         cat_join(cjn, cid, 'tmp_imp', czn, buff)
# end NLCD

### Pollutant loads
# For N/P/S, Unit is mg. There are two versions of sediment yield (SedYld and altSedYld, using different calculations).
# The land-only mask is used for these analyses.
poll_gdb = r'G:\SWAPSPACE\hwProducts_20200731.gdb'

for t in cattype:
   c = t[0]
   cid = t[1]
   cnm = t[2]
   czn = t[3]
   cjn = t[4]
   print('Working on ' + cnm + '...')

   # loop over years
   for year in years:

      # get list of datasets, by year
      ls = [[poll_gdb + os.sep + 'LocMass_Nitrogen_' + year, 'avgN'],
            [poll_gdb + os.sep + 'LocMass_Phosphorus_' + year, 'avgP'],
            [poll_gdb + os.sep + 'LocMass_SuspSolids_' + year, 'avgS'],
            [poll_gdb + os.sep + 'SedYld_' + year, 'avgSED'],
            [poll_gdb + os.sep + 'altSedYld_' + year, 'avgSEDALT'],
            [poll_gdb + os.sep + 'runoffDepth_' + year, 'avgRUNOFF']]
      # Create file GDB (one for each year), catchment copies
      ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_' + year + '.gdb'
      mask = src_gdb + os.sep + "lc_" + year + "_watermask"
      make_catGDB(ws, in_Catchments0, in_subCatchments0)
      arcpy.env.workspace = ws

      for i in ls:
         r = i[0]
         if not arcpy.Exists(r):
            print('Dataset `' + r + '` does not exist.')
            continue
         for buff in buffs:
            print('Working on `' + i[1] + '` for buffer size: ' + buff)
            if buff != "":
               # change zone raster to the buffer-only versions
               if cnm == 'subCatchments':
                  c1 = fdbuff + buff + '_subCatRast_inclWater'
               else:
                  c1 = fdbuff + buff + '_catRast_inclWater'
            else:
               c1 = c
            # Get zonal statistics (MEAN)
            add_zs(c1, czn, r, i[1], "MEAN", i[1], mask=mask)
            cat_join(cjn, cid, i[1], czn, buff)


### Non year-specific variables (add these to latest year GDB: 2016)

# Set up geodatabase
ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_2016.gdb'
make_catGDB(ws, in_Catchments0, in_subCatchments0)
arcpy.env.workspace = ws
# pollutant GDB
poll_gdb = r'G:\SWAPSPACE\hwProducts_20200731.gdb'
# Some of these use the open water mask; use the NLCD 2016 version
mask = src_gdb + os.sep + "lc_2016_watermask"

### List all non-year specific rasters here [raster, variable name, statistic, mask]
ls = [[src_gdb + os.sep + 'pasturefreq', 'avgPASTURE', "MEAN", mask],
      [src_gdb + os.sep + 'cornfreq', 'avgCORN', "MEAN", mask],
      [src_gdb + os.sep + 'cottonfreq', 'avgCOTTON', "MEAN", mask],
      [src_gdb + os.sep + 'soyfreq', 'avgSOY', "MEAN", mask],
      [src_gdb + os.sep + 'wheatfreq', 'avgWHEAT', "MEAN", mask],
      [poll_gdb + os.sep + 'maxPrecip_gen24_topo10', 'avgMAXPREC', "MEAN", None]]

for t in cattype:
   c = t[0]
   cid = t[1]
   cnm = t[2]
   czn = t[3]
   cjn = t[4]
   print('Working on ' + cnm + '...')
   for i in ls:
      r = i[0]
      for buff in buffs:
         print('Working on `' + r + '` for buffer size: ' + buff)
         if buff != "":
            # change zone raster to the buffer-only versions
            if cnm == 'subCatchments':
               c1 = fdbuff + buff + '_subCatRast_inclWater'
            else:
               c1 = fdbuff + buff + '_catRast_inclWater'
         else:
            c1 = c
         # Get zonal statistics
         add_zs(c1, czn, r, i[1], i[2], i[1], i[3])
         cat_join(cjn, cid, i[1], czn, buff)


### Roads
# NOTE: These are all-vector analyses. They do not use the rasterized catchments
# These require the areaLand variable(s) from NLCD to be in the output catchments table, to calculate density
# See ProcessRasters.py for pre-processing steps with the RCL and Flowline data

# Set up geodatabase
ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_2016.gdb'
make_catGDB(ws, in_Catchments0, in_subCatchments0)
arcpy.env.workspace = ws

# Roads feature class
rcl = src_gdb + os.sep + 'rcl'
# Road crossings (point) feature class
rdcrs = src_gdb + os.sep + 'rdcrs1'
stream = r'L:\David\GIS_data\NHDPlus_HR\NHDPlus_HR_Virginia.gdb\NHDFlowline'

# Loop over catchments
for t in cattype:
   # These are vector analyses, so change the 'zones' to the original features instead of catchment zone rasters
   if t[2] == 'Catchments':
      c = in_Catchments0
   else:
      c = in_subCatchments0
   cid = t[1]
   cnm = t[2]
   # zones not used
   cjn = t[4]
   print('Working on ' + cnm + '...')

   # Roads: length (km) and density (km per square km)
   out = 'road_length'
   for buff in buffs:
      # These use the feature buffers. NOTE: Stream-area is included in the buffer (unlike rasters analyses)
      print('Working on road length / density for buffer size: ' + buff)
      if buff != "":
         if cnm == 'subCatchments':
            c1 = fdbuff + buff + '_subCatFeat'
         else:
            c1 = fdbuff + buff + '_catFeat'
      else:
         c1 = c

      # Intersect and dissolve by catchment
      arcpy.PairwiseIntersect_analysis([c1, rcl], 'cat_rcl', 'NO_FID', output_type='LINE')
      # Dissolve is needed to remove overlapping roads
      arcpy.PairwiseDissolve_analysis('cat_rcl', 'cat_rcl_diss0', [cid])
      # summarize road length
      arcpy.Statistics_analysis('cat_rcl_diss0', out, [['Shape_Length', 'SUM']], cid)
      arcpy.AddField_management(out, 'lengRD', 'DOUBLE')
      arcpy.CalculateField_management(out, 'lengRD', '!SUM_Shape_Length! / 1000')
      cat_join(cjn, cid, out, cid, buff)
      # calculate density (using areaLand in buffer)
      arcpy.AddField_management(cjn, 'densRD' + buff, 'DOUBLE')
      arcpy.CalculateField_management(cjn, 'densRD' + buff, '!lengRD' + buff + '! / (!areaLand' + buff + '! / 1000000)')

   # Road crossings: count and density (number / sq km)
   out = 'roadcross_count'
   print('Calculating road crossing count / density for ' + cjn + '...')
   arcpy.SpatialJoin_analysis(rdcrs, c1, 'rdcrs_cat', "JOIN_ONE_TO_ONE", "KEEP_COMMON", match_option="INTERSECT")
   arcpy.Statistics_analysis('rdcrs_cat', out, [[cid, 'COUNT']], cid)
   arcpy.AlterField_management(out, 'COUNT_' + cid, 'numRDCRS', clear_field_alias=True)
   cat_join(cjn, cid, out, cid)
   # calculate density (using areaLand). Added 'buffer' versions
   arcpy.AddField_management(cjn, 'densRDCRS', 'DOUBLE')
   arcpy.CalculateField_management(cjn, 'densRDCRS', '!numRDCRS! / (!areaLand! / 1000000)')
   # coulddo: add buffer versions?
   # for buff in buffs:
   #    arcpy.AddField_management(cjn, 'densRDCRS' + buff, 'DOUBLE')
   #    arcpy.CalculateField_management(cjn, 'densRDCRS', '!numRDCRS! / (!areaLand' + buff + '! / 1000000)')

del_ls = ['cat_rcl', 'cat_rcl_diss0', 'rdcrs_cat']
for d in del_ls:
   arcpy.Delete_management(d)


### Add new variables here
