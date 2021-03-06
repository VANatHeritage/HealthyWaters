#----------------------------------------------------
# Purpose: Process Rasters for use in catchment summaries.
#
# This script covers preparation work for catchment zonal summaries. This includes
# creating a master catchment feature class and zonal raster, used in zonal summaries. A
# template raster and feature is also created, based on a 1-km buffer around input catchments.
#
# The main body of the script covers processing for specific input (environmental variable)
# datasets, including standardizing to the NHDPlusHR raster projection, snap, cell size, extent,
# and mask.
#
# Version: ArcPro / Python 3+
# Date Created: 3-12-20
# Authors: Hannah Huggins/David Bucklin
#----------------------------------------------------

import arcpy
import os


def process_rasters(in_raster, template_raster, output, setNoData=None):
   """This function masks, projects, and optionally sets values to NoData.
   Parameters:
   in_raster = the raster with the values the expression is based on.
   template_raster = The raster used as a projection, cell size, and snap template
   output = This is the output raster. All output rasters will use this name pattern.
   setNoData = Query (e.g. `Value = 11`) to identify values that should set NoData in the output."""
   #Check out the spatial extension
   arcpy.CheckOutExtension("Spatial")
   arcpy.env.snapRaster = in_raster
   arcpy.env.cellSize = in_raster

   # Make a cropped/masked version of the raster, optionally setting values to nodata
   if setNoData:
      print('Setting ' + setNoData + ' to NoData...')
      arcpy.sa.SetNull(in_raster, in_raster, setNoData).save(output)
   else:
      print('Masking raster...')
      arcpy.sa.ExtractByMask(in_raster, arcpy.env.mask).save(output)

   # Now project/resample
   arcpy.env.snapRaster = template_raster
   arcpy.env.cellSize = template_raster
   print("Projecting raster...")
   arcpy.ProjectRaster_management(output, output + '_proj', template_raster, "NEAREST", "10 10")
   return output


# HEADER FOR ALL PROCESSES

arcpy.env.overwriteOutput = True
# template for snap, cell size, projection of outputs
template_raster = r'L:\David\GIS_data\NHDPlus_HR\NHDPlus_HR_FlowLength.gdb\flowlengover_VA'
arcpy.env.snapRaster = template_raster
arcpy.env.cellSize = template_raster

# original NHDPlusHR catchments
cat_orig = r'L:\David\GIS_data\NHDPlus_HR\NHDPlus_HR_Virginia.gdb\NHDPlusCatchment'
gdb = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb"
if not (os.path.exists(gdb)):
   arcpy.CreateFileGDB_management(os.path.dirname(gdb), os.path.basename(gdb))
arcpy.env.workspace = gdb

# Create catchment master file (both feature and raster), and feature and raster templates (1-km buffer)
# NOTE: originally was using a VALAM-projected catchment feature class, but noticed some striping in conversion to
#  raster. Projection now set to match the NHDPlusHR Raster projection for the catchments (which is different than
#  the NHDPlusHR features). Seems to have resolved the striping issue.
# NOTE: Also did some manual editing to clean up the catchments (exploded several catchments with Null NHDPlusIDs, then
# deleted one catchment falling far outside the processing area).
cat_master = 'NHDPlusCatchment_metrics'
if not arcpy.Exists(cat_master):
   print('Copying original catchments...')
   arcpy.env.outputCoordinateSystem = template_raster
   arcpy.FeatureClassToFeatureClass_conversion(cat_orig, gdb, cat_master)
# TODO: manually edit `cat_master` feature class now, prior to continuing. See notes above.

if 'catID' not in [a.name for a in arcpy.ListFields(cat_master)]:
   arcpy.PairwiseBuffer_analysis(cat_master, 'NHDPlusCatchment_metrics_1kmBuff', "1000 Meters",
                                 dissolve_option="ALL")
   arcpy.AddField_management('NHDPlusCatchment_metrics_1kmBuff', 'val', 'SHORT')
   arcpy.CalculateField_management('NHDPlusCatchment_metrics_1kmBuff', 'val', '1')
   arcpy.PolygonToRaster_conversion('NHDPlusCatchment_metrics_1kmBuff', 'val', 'HW_templateRaster')
   arcpy.BuildPyramids_management('HW_templateRaster')
   # Generate new unique ID for each catchment; this becomes unique ID and will be rasterized
   arcpy.AddField_management(cat_master, 'catID', 'LONG')
   arcpy.CalculateField_management(cat_master, 'catID', '!OBJECTID!')
   print('Creating catchment raster...')
   arcpy.PolygonToRaster_conversion(cat_master, 'catID', 'NHDPlusCatchment_raster')
   arcpy.BuildPyramids_management('NHDPlusCatchment_raster')


# Re-set template raster to the one just created
template_raster = r'E:\git\HealthyWaters\inputs\snap_raster\HW_templateRaster.tif'
arcpy.env.snapRaster = template_raster
arcpy.env.cellSize = template_raster
# Note: Coordinate system is set in the function; leave None so default is used
arcpy.env.outputCoordinateSystem = None
arcpy.env.extent = template_raster
arcpy.env.mask = template_raster

# END HEADER


# Process raster datasets (add new to bottom of the list).

# Land cover datasets
ls = [['lc_2016', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2016_Land_Cover_L48_20190424.img'],
      ['lc_2011', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2011_Land_Cover_L48_20190424.img'],
      ['lc_2006', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2006_Land_Cover_L48_20190424.img'],
      ['lc_2001', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2001_Land_Cover_L48_20190424.img']]
for l in ls:
   in_raster = l[1]
   if not arcpy.Exists(l[0]):
      process_rasters(in_raster, template_raster, l[0])
      print("The output `" + l[0] + "` has been created.")
      # create water masks
      arcpy.sa.SetNull(l[0] + '_proj', 1, "Value = 11").save(l[0] + '_watermask')

# Impervious rasters
ls = [['imp_2016', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2016_Impervious_L48_20190405.img'],
      ['imp_2011', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2011_Impervious_L48_20190405.img'],
      ['imp_2006', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2006_Impervious_L48_20190405.img'],
      ['imp_2001', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2001_Impervious_L48_20190405.img']]
for l in ls:
   in_raster = l[1]
   if not arcpy.Exists(l[0]):
      process_rasters(in_raster, template_raster, l[0])
      print("The output `" + l[0] + "` has been created.")

# Canopy rasters (only available for 2011, 2016)
ls = [['treecan_2016', r'L:\David\GIS_data\NLCD\treecan2016.tif\treecan2016.tif'],
      ['treecan_2011', r'L:\David\GIS_data\NLCD\nlcd_2011_treecanopy_2019_08_31\nlcd_2011_treecanopy_2019_08_31.img']]
for l in ls:
   in_raster = l[1]
   if not arcpy.Exists(l[0]):
      process_rasters(in_raster, template_raster, l[0])
      print("The output `" + l[0] + "` has been created.")

# Crop-frequency rasters
set_to_null = 'Value = 255'
ls = [['cornfreq', r'L:\David\GIS_data\USDA_NASS\Crop_Frequency_2008-2019\crop_frequency_corn_2008-2019.img'],
      ['soyfreq', r'L:\David\GIS_data\USDA_NASS\Crop_Frequency_2008-2019\crop_frequency_soybeans_2008-2019.img'],
      ['cottonfreq', r'L:\David\GIS_data\USDA_NASS\Crop_Frequency_2008-2019\crop_frequency_cotton_2008-2019.img'],
      ['wheatfreq', r'L:\David\GIS_data\USDA_NASS\Crop_Frequency_2008-2019\crop_frequency_wheat_2008-2019.img']]
for l in ls:
   in_raster = l[1]
   if not arcpy.Exists(l[0]):
      process_rasters(in_raster, template_raster, l[0], set_to_null)
      print("The output `" + l[0] + "` has been created.")

# CDL: Create Custom frequency rasters from original CDL by year
cdl = r'L:\David\GIS_data\USDA_NASS\CDL'
if not os.path.exists(cdl + os.sep + 'cdl_processing.gdb'):
   arcpy.CreateFileGDB_management(cdl, 'cdl_processing.gdb')
   arcpy.BuildPyramidsandStatistics_management(cdl)
cdl_gdb = cdl + os.sep + 'cdl_processing.gdb'
# get initial list of rasters
arcpy.env.workspace = cdl
ls0 = [arcpy.env.workspace + os.sep + a for a in arcpy.ListRasters('*.tif')]
arcpy.env.workspace = gdb
ls = [[os.path.basename(a)[0:8].lower(), a] for a in ls0]
ls_sum = []
arcpy.env.snapRaster = ls[0][1]
arcpy.env.cellSize = ls[0][1]
# loop over types (output name, query)
types = [['pasturehay', 'Value IN (37, 176)']]  # add to list if needed
for t in types:
   print(t[0])
   for l in ls:
      print(l[0])
      r = cdl_gdb + os.sep + l[0]
      arcpy.sa.SetNull(l[1], l[1], "Value = 0").save(cdl_gdb + os.sep + 'rtmp')
      arcpy.sa.Con(cdl_gdb + os.sep + 'rtmp', 1, 0, t[1]).save(r)
      ls_sum.append(r)
   arcpy.sa.CellStatistics(ls_sum, "SUM").save(cdl_gdb + os.sep + t[0] + '_frequency_2008_2019')
   print(t[0] + ' done.')
# Now project raster(s)
arcpy.env.snapRaster = template_raster
arcpy.env.cellSize = template_raster
# loop over types (output name, input file)
ls = [['pasturefreq', cdl_gdb + os.sep + 'pasturehay_frequency_2008_2019']]  # add to list if needed
for l in ls:
   in_raster = l[1]
   if not arcpy.Exists(l[0]):
      process_rasters(in_raster, template_raster, l[0])
      print("The output `" + l[0] + "` has been created.")

# Roads
# Road-crossings
# Note: added the individual counties here to complete coverage missing from the base all_centerline feature class
rcl = [r'E:\RCL_cost_surfaces\Tiger_2018\roads_proc.gdb\all_centerline',
       r'L:\David\projects\RCL_processing\Tiger_2018\data\unzip\tl_2018_10001_roads.shp',
       r'L:\David\projects\RCL_processing\Tiger_2018\data\unzip\tl_2018_10005_roads.shp',
       r'L:\David\projects\RCL_processing\Tiger_2018\data\unzip\tl_2018_42099_roads.shp',
       r'L:\David\projects\RCL_processing\Tiger_2018\data\unzip\tl_2018_42055_roads.shp',
       r'L:\David\projects\RCL_processing\Tiger_2018\data\unzip\tl_2018_24011_roads.shp',
       r'L:\David\projects\RCL_processing\Tiger_2018\data\unzip\tl_2018_37055_roads.shp']
stream = r'L:\David\GIS_data\NHDPlus_HR\NHDPlus_HR_Virginia.gdb\NHDFlowline'
# These are for vector-only analyses in CatchmentMetrics.py
arcpy.env.outputCoordinateSystem = template_raster
arcpy.env.parallelProcessingFactor = "75%"
out = 'rcl'
if not arcpy.Exists(out):
   arcpy.Merge_management(rcl, out)
# Create road crossing feature class
out = 'rdcrs1'
if not arcpy.Exists(out):
   arcpy.PairwiseIntersect_analysis(['rcl', stream], 'rdcrs0', 'ONLY_FID', output_type='Point')
   arcpy.MultipartToSinglepart_management('rdcrs0', out)
   arcpy.DeleteIdentical_management(out, "Shape")

# Add new datasets here


arcpy.BuildPyramidsandStatistics_management(arcpy.env.workspace)
# end