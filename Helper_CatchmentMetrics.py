#----------------------------------------------------
# Purpose: Functions and header processes for CatchmentMetrics.py, which completes catchment zonal summaries
# for all datasets. The processes completed in this script are limited to setting up variables
# in catchment metrics, and creating raster versions of the catchments, if they don't exist.
#
# Version: ArcPro / Python 3+
# Date Created: 8-3-2020
# Authors: David Bucklin
#----------------------------------------------------

import arcpy
import os
# Check out the spatial extension
arcpy.CheckOutExtension("Spatial")


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


def add_zs(in_Zone, zone_field, in_raster, out_Tab, stat="MEAN", fld_name=None, mask=None):
   """This function is a wrapper around ZonalStatisticsAsTable, allowing to set a mask just for the summary,
   and change the name of the summary field."""

   print('Zonal summarizing ' + stat + ' of raster `' + in_raster + '` in zones `' + in_Zone + '`...')
   if mask:
      envmask = arcpy.env.mask
      arcpy.env.mask = mask
      print("Using mask `" + mask + "`...")
   arcpy.sa.ZonalStatisticsAsTable(in_Zone, zone_field, in_raster, out_Tab, "DATA", stat)
   if fld_name:
      arcpy.AlterField_management(out_Tab, stat, fld_name, clear_field_alias=True)
   if mask:
      arcpy.env.mask = envmask
   return out_Tab


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


def cat_join(cat_tab, cat_id, join_tab, join_id, fld_suffix=""):
   """Joins summarized table to master catchment feature class, by selecting fields to
   join (based on the field prefix), optionally adding a suffix (i.e. buffer size) to the joined field names, and
   deleting join_tab following the join."""

   flds = [a.name for a in arcpy.ListFields(join_tab)]
   # TODO: update prefixes as needed
   fld = [f for f in flds if f.startswith(('perc', 'area', 'dens', 'leng', 'num', 'avg'))]  # 'sum', 'freq'
   if fld_suffix != "":
      for f in fld:
         arcpy.AlterField_management(join_tab, f, f + fld_suffix, clear_field_alias=True)
      fld = [f + fld_suffix for f in fld]
   if len(fld) == 0:
      print('No fields to join.')
      return
   print('Joining fields : [' + ', '.join(fld) + '] to dataset `' + cat_tab + '`.')
   fld_exist = [f.name for f in arcpy.ListFields(cat_tab) if f.name in fld]
   if len(fld_exist) > 0:
      print("Removing existing fields...")
      for f in fld_exist:
         arcpy.DeleteField_management(cat_tab, f)
   arcpy.JoinField_management(cat_tab, cat_id, join_tab, join_id, fld)
   arcpy.Delete_management(join_tab)
   return cat_tab


### Global variables/settings. Includes preparation of subCatchment zonal rasters, if they don't exist

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
      # Note: decided to use the 'inclWater' version, as of 2020-08-04
      out = fdbuff + b + '_subCatRast'
      arcpy.sa.ExtractByMask(in_subCatchments, fdbuff + b + '_catRast').save(out)
      out = fdbuff + b + '_subCatRast_inclWater'
      arcpy.sa.ExtractByMask(in_subCatchments, fdbuff + b + '_catRast_inclWater').save(out)
      out = fdbuff + b + '_subCatFeat'
      arcpy.Clip_analysis(in_subCatchments0, fdbuff + b + '_catFeat', out)

# List of catchment/subCatchment properties:
#  [zones data, unique ID field, name for outputs, zone ID field, name of join dataset]
# Processing is the same for both datasets, so setting up this list allows to loop over the two datasets.
cattype = [[in_Catchments, catID, 'Catchments', 'Value', os.path.basename(in_Catchments0)],
           [in_subCatchments, subcatID, 'subCatchments', 'Value', os.path.basename(in_subCatchments0)]]

### END
