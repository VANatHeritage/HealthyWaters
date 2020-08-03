#----------------------------------------------------
# Name: Catchment Zonal summaries
#  This script summarizes metrics (land cover, crops, road crossings, pollutants, etc.) within catchments.
#  The general workflow is to (1) loop over catchment types (subCatchments and catchments), (2) loop over years (for
#  multi-temporal datasets), (3) loop over stream buffers, and (4) loop over datasets in a group processed in the same
#  way (e.g. land cover). Summary metrics are output to 'Catchment geodatabases', one for each temporal group: 2016,
#  2011, 2006, 2001, and noYear, for those datasets not tied to a specific year.
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
            [poll_gdb + os.sep + 'runoffDepth_' + year, 'sumRUNOFF']]
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
         add_zs(c1, czn, r, varname, "MEAN", varname, mask)
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
