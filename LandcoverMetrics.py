#----------------------------------------------------
# Name: Land Cover Metrics Assigner
# Version: ArcPro / Python 3+
# Date Created: 3-5-20
# Last Edited: 4-23-20
# Authors: Hannah Huggins / David Bucklin
# Summary: Adds desired metrics to a summary table for a zone raster.
#----------------------------------------------------

import arcpy
import os
# Check out the spatial extension
arcpy.CheckOutExtension("Spatial")


# From KeyID_code_fixed.py
def add_KeyID(out_table):
   """This function creates a KeyID field based on the raster_num and the Str_VALUE, which is created in the function.
   Parameter:
   out_tables = This is the pathname to and name of the output tables"""
   bid = out_table[-4:]
   # make the value field string
   # new_value = arcpy.AddField_management(out_table, "Str_VALUE", "TEXT")
   # arcpy.CalculateField_management(out_table, "Str_VALUE", "!VALUE!", "PYTHON")
   # Make a KeyID by combining the raster_num and Str_VALUE fields
   arcpy.AddField_management(out_table, "KeyID", "TEXT")
   expression = "'" + str(bid) + "' + str(int(!VALUE!))"
   arcpy.CalculateField_management(out_table, "KeyID", expression, "PYTHON")
   # Statement on location in the loop
   print("{} KeyID created".format(bid))


# From KeyID_code_fixed.py
def add_KeyID_Catchment(catchment_table):
   """This function creates a KeyID field based on the GridCode and the VPUID fields
   Parameter:
   catchment_table = This is the pathname to and name of the catchment table"""
   arcpy.AddField_management(catchment_table, "KeyID", "TEXT")
   expression = "str(!VPUID!) + str(!GridCode!)"
   arcpy.CalculateField_management(catchment_table, "KeyID", expression, "PYTHON")
   # Statement on location in the loop
   print("KeyID Created")


def add_zs(in_Zone, out_Tab, in_raster, stat, zone_field='Value'):
   """This function uses the Zonal Statistics as Table Tool to create an output table about canopies.
   Parameters:
   in_Zone = The input raster that defines the zones where the Zonal Statistics function.
   out_Tab = This is the pathname to and name of the output table
   in_raster = The input dataset that the statistics are based on.
   stat = what statistic type will be calculated"""
   # Specify fields for rasters
   print(in_Zone)
   print(out_Tab)
   arcpy.sa.ZonalStatisticsAsTable(in_Zone, zone_field, in_raster, out_Tab, "DATA", stat)
   print("Zonal statistics for `" + in_raster + "` calculated.")


def add_NLCD_LCmetrics(in_Zone, out_Tab, in_LandCover, zone_field='Value', class_field='Value'):
   """This function creates a table based on the Tabulate Area tool and adds landcover metrics.
   Parameter:
   # in_outs = [in_Zones, out_Tab]
   in_Zone = The input raster that defines the zones where the tabulate area functions.
   out_Tab = This is the pathname to and name of the output table
   in_LandCover = The input dataset that defines the classes that have their areas summarized in the zones."""
   # Specify fields for rasters
   print(in_Zone)
   print(out_Tab)
   # Tabulate area
   arcpy.sa.TabulateArea(in_Zone, zone_field, in_LandCover, class_field, out_Tab)
   # add missing fields (can happen for less common land covers in small watersheds)
   nlcd_val = ['11', '21', '22', '23', '24', '31', '41', '42', '43', '52', '71', '81', '82', '90', '95']
   all_nm = ['VALUE_' + a for a in nlcd_val]
   tab_nm = [a.name for a in arcpy.ListFields(out_Tab)]
   miss = [a for a in all_nm if a not in tab_nm]
   for m in miss:
      print('Adding missing field `' + m + '`.')
      arcpy.AddField_management(out_Tab, m, 'LONG')
      arcpy.CalculateField_management(out_Tab, m, '0')
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
   arcpy.CalculateField_management(out_Tab, "percFORWET", "((!VALUE_41! + !VALUE_42! + !VALUE_43! + !VALUE_90! + "
                                                          "!VALUE_95!) / !areaLand!) * 100")
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
   print("The output table `" + out_Tab + "` has been created.")


def main():

   # Land cover data year
   year = '2016'
   # Parameters
   # in_LandCover = r"E:\git\HealthyWaters\inputs\catchments\TestGDB.gdb\lc2016_pro_resample"
   # in_canopy = r"E:\git\HealthyWaters\inputs\catchments\TestGDB.gdb\treecan2016_resample"
   # in_imp = r"E:\git\HealthyWaters\inputs\catchments\TestGDB.gdb\imp2016_resample"
   # mask = r"E:\git\HealthyWaters\inputs\catchments\TestGDB.gdb\lc2016_nowater"
   in_LandCover = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb\lc_" + year + "_proj"
   # NOTE: no NLCD canopy data for 2001, 2006
   in_canopy = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb\treecan_" + year + "_proj"
   in_imp = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb\imp_" + year + "_proj"
   mask = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb\lc_" + year + "_nowater"
   in_Catchments = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb\NHDPlusCatchment_metrics"
   in_subCatchments = r"E:\git\HealthyWaters\inputs\watersheds\hw_watershed_nodams_20200420.gdb\hw_Flowline_subCatchArea"

   # Loop over HU4 folders
   hr_folder = r'L:\David\GIS_data\NHDPlus_HR\HRNHDPlusRasters'
   hu4 = list(set([a[0] for a in arcpy.da.SearchCursor(in_Catchments, "VPUID")]))

   # Create file GDB if it doesn't exist
   ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_' + year + '.gdb'
   if not os.path.exists(ws):
      arcpy.CreateFileGDB_management(os.path.dirname(ws), os.path.basename(ws))
   arcpy.env.overwriteOutput = True
   arcpy.env.workspace = ws

   # Process land cover metrics
   arcpy.env.mask = None
   # SubCatchments
   add_NLCD_LCmetrics(in_subCatchments, 'lc_table_subCatchments', in_LandCover, zone_field='OBJECTID_in_Points')
   # Full catchments
   for vpuid in hu4:
      in_Zone = hr_folder + vpuid + os.sep + "cat.tif"
      out_Tab = "lc_table_" + vpuid
      if not arcpy.Exists(out_Tab):
         # Specify function(s) to run
         add_NLCD_LCmetrics(in_Zone, out_Tab, in_LandCover)
         try:
            add_KeyID(out_Tab)
         except:
            print('failed to add key for ' + vpuid + '.')

   # Process canopy and impervious. These use a mask
   arcpy.env.mask = mask
   # Subcatchments
   if arcpy.Exists(in_canopy):
      add_zs(in_subCatchments, 'canopy_subCatchments', in_canopy, "MEAN", 'OBJECTID_in_Points')
   add_zs(in_subCatchments, 'imp_subCatchments', in_imp, "MEAN", 'OBJECTID_in_Points')
   # Regular catchments
   for vpuid in hu4:
      in_Zone = hr_folder + vpuid + os.sep + "cat.tif"
      # canopy
      if arcpy.Exists(in_canopy):
         out_Tab = "canopy_" + vpuid
         if not arcpy.Exists(out_Tab):
            add_zs(in_Zone, out_Tab, in_canopy, "MEAN")
            try:
               add_KeyID(out_Tab)
            except:
               print('failed to add key for ' + vpuid + '.')
      # impervious
      out_Tab = "imp_" + vpuid
      if not arcpy.Exists(out_Tab):
         add_zs(in_Zone, out_Tab, in_imp, "MEAN")
         try:
            add_KeyID(out_Tab)
         except:
            print('failed to add key for ' + vpuid + '.')

   # merge all tables by type
   arcpy.env.workspace = ws
   tabs = arcpy.ListTables('lc_table_*')
   arcpy.Merge_management(tabs, 'lc_table_allCatchments')
   tabs = arcpy.ListTables('canopy_*')
   if len(tabs) > 0:
      arcpy.Merge_management(tabs, 'canopy_allCatchments')
      arcpy.AlterField_management('canopy_allCatchments', 'MEAN', 'percCAN', clear_field_alias=True)
   tabs = arcpy.ListTables('imp_*')
   arcpy.Merge_management(tabs, 'imp_allCatchments')
   arcpy.AlterField_management('imp_allCatchments', 'MEAN', 'percIMP', clear_field_alias=True)

   # Copy master catchment table
   if 'KeyID' not in [a.name for a in arcpy.ListFields(in_Catchments)]:
      add_KeyID_Catchment(in_Catchments)
   new_Catchments = os.path.basename(in_Catchments)
   arcpy.CopyFeatures_management(in_Catchments, new_Catchments)

   # loop over merged metric tables, join fields to new_Catchments
   in_field = "KeyID"
   tabs = arcpy.ListTables('*_allCatchments')
   for t in tabs:
      print('Joining `' + t + '`...')
      flds = [a.name for a in arcpy.ListFields(t)]
      fld = [f for f in flds if f.startswith('VALUE_') or f.startswith('perc') or f.startswith('area')]
      arcpy.JoinField_management(new_Catchments, in_field, t, in_field, fld)

   # subCatchments
   if arcpy.Exists('canopy_subCatchments'):
      arcpy.AlterField_management('canopy_subCatchments', 'MEAN', 'percCAN', clear_field_alias=True)
   arcpy.AlterField_management('imp_subCatchments', 'MEAN', 'percIMP', clear_field_alias=True)
   new_subCatchments = os.path.basename(in_subCatchments)
   arcpy.CopyFeatures_management(in_subCatchments, new_subCatchments)
   tabs = arcpy.ListTables('*_subCatchment*')
   for t in tabs:
      print('Joining `' + t + '`...')
      flds = [a.name for a in arcpy.ListFields(t)]
      fld = [f for f in flds if f.startswith('VALUE_') or f.startswith('perc') or f.startswith('area')]
      arcpy.JoinField_management(new_subCatchments, 'OBJECTID_in_Points', t, 'OBJECTID_in_Points', fld)


main()
