#----------------------------------------------------
# Name: Catchment Zonal summaries
# This script summarizes metrics (land cover, crops, road crossings, etc) within catchments.
# Version: ArcPro / Python 3+
# Date Created: 3-5-20
# Last Edited: 6-2-20
# Authors: Hannah Huggins / David Bucklin
#----------------------------------------------------

import arcpy
import os
# Check out the spatial extension
arcpy.CheckOutExtension("Spatial")


def add_zs(in_Zone, out_Tab, in_raster, stat, zone_field='Value'):
   """This function uses the Zonal Statistics as Table Tool to create an output table about canopies.
   Parameters:
   in_Zone = The input raster that defines the zones where the Zonal Statistics function.
   out_Tab = This is the pathname to and name of the output table
   in_raster = The input dataset that the statistics are based on.
   stat = what statistic type will be calculated"""
   # Specify fields for rasters
   print('Input zones: ' + in_Zone)
   arcpy.sa.ZonalStatisticsAsTable(in_Zone, zone_field, in_raster, out_Tab, "DATA", stat)
   print('Output table: ' + out_Tab)


def add_NLCD_LCmetrics(in_Zone, out_Tab, in_LandCover, zone_field='Value', class_field='Value'):
   """This function creates a table based on the Tabulate Area tool and adds landcover metrics.
   Parameter:
   in_Zone = The input raster/features that defines the zones where the tabulate area functions.
   out_Tab = This is the pathname to and name of the output table
   in_LandCover = The input dataset that defines the classes that have their areas summarized in the zones.
   zone_field = Filed in in_Zone that defines the unique zones.
   class_field = Field in in_Landcover with class values."""
   # Specify fields for rasters
   print('Input zones: ' + in_Zone)
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
   # Add and calculate percDEV field
   arcpy.AddField_management(out_Tab, "percDEV", "DOUBLE")
   arcpy.CalculateField_management(out_Tab, "percDEV", "((!VALUE_21! + !VALUE_22! + !VALUE_23! + !VALUE_24!) / !areaLand!) * 100")
   print('Output table: ' + out_Tab)


def main():

   # HEADER FOR ALL PROCESSES

   # Source geodatabase for input rasters
   src_gdb = r'E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb'

   # Template raster. Note that mask and extent should not be set. Masking is handled by-variable
   template_raster = r'E:\git\HealthyWaters\inputs\snap_raster\HW_templateRaster.tif'
   arcpy.env.overwriteOutput = True
   arcpy.env.cellSize = template_raster
   arcpy.env.snapRaster = template_raster
   arcpy.env.outputCoordinateSystem = template_raster
   # 'Buffer' (flow distance) raster prefix
   fdbuff = 'L:/David/GIS_data/NHDPlus_HR/NHDPlus_HR_FlowLength.gdb/flowDistance_'

   # Catchment feature class
   in_Catchments0 = src_gdb + os.sep + 'NHDPlusCatchment_metrics'
   catID = 'catID'
   # Rasterized version of catchemnts. This is now in ProcessRasters.py,
   # with some manual editing involved; see notes there.
   in_Catchments = src_gdb + os.sep + 'NHDPlusCatchment_raster'
   if catID not in [a.name for a in arcpy.ListFields(in_Catchments0)]:
      print('Missing catID field...')
      # # Generate new unique ID for each catchment; will rasterize this value. For use only in this script
      # arcpy.AddField_management(in_Catchments0, catID, 'LONG')
      # arcpy.CalculateField_management(in_Catchments0, catID, '!OBJECTID!')
   if not arcpy.Exists(in_Catchments):
      print('Missing catchment raster...')
      # arcpy.PolygonToRaster_conversion(in_Catchments0, catID, in_Catchments) #, "CELL_CENTER", "NONE", template_raster)
      # arcpy.BuildPyramids_management(in_Catchments)

   # SubCatchment feature class. Not converting this to raster, since this is a small dataset
   in_subCatchments = r"E:\git\HealthyWaters\inputs\watersheds\hw_watershed_nodams_20200528.gdb\hw_Flowline_subCatchArea"
   subcatID = 'OBJECTID_in_Points'

   # Use this to generate metrics in stream buffer zones only (See StreamBufferZones.py)
   # The empty string value `''` generates metrics for full catchments
   buffs = ['', '100m', '250m', '500m']
   years = ['2001', '2006', '2011', '2016']

   # END HEADER

   # List of catchment/subCatchment properties [zones data, unique ID field, name for outputs, zone ID field]
   # Processing is the same for both datasets, so setting up this list allows to loop over the two datasets.
   # cattype = [[in_Catchments, catID, 'Catchments', 'Value'], [in_subCatchments, subcatID, 'subCatchments', subcatID]]
   # TODO: need to re-run subCatchments, when new watersheds are created.
   cattype = [[in_subCatchments, subcatID, 'subCatchments', subcatID]]

   for t in cattype:
      c = t[0]
      cid = t[1]
      cnm = t[2]
      czn = t[3]
      print(c)
      print(cnm)

      ### NLCD Variables: loop over years
      for year in years:

         # Land cover datasets
         in_LandCover0 = src_gdb + os.sep + "lc_" + year + "_proj"
         # NOTE: no NLCD canopy data for 2001, 2006
         in_canopy0 = src_gdb + os.sep + "treecan_" + year + "_proj"
         in_imp0 = src_gdb + os.sep + "imp_" + year + "_proj"
         mask = src_gdb + os.sep + "lc_" + year + "_nowater"
         print('Processing land cover metrics for year ' + year + '...')

         # Create file GDB if it doesn't exist
         ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_' + year + '.gdb'
         if not os.path.exists(ws):
            arcpy.CreateFileGDB_management(os.path.dirname(ws), os.path.basename(ws))
         arcpy.env.workspace = ws

         for buff in buffs:
            print('Working on buffer size: ' + buff)

            # No mask for land cover summaries
            arcpy.env.mask = None
            if buff != "":
               print('Masking land cover datasets to buffered streams...')
               in_buff = fdbuff + buff
               if not arcpy.Exists('in_LandCover_' + buff):
                  arcpy.sa.ExtractByMask(in_LandCover0, in_buff).save('in_LandCover_' + buff)
               in_LandCover = 'in_LandCover_' + buff
               if arcpy.Exists(in_canopy0):
                  if not arcpy.Exists('in_canopy_' + buff):
                     arcpy.sa.ExtractByMask(in_canopy0, in_buff).save('in_canopy_' + buff)
                  in_canopy = 'in_canopy_' + buff
               else:
                  in_canopy = in_canopy0
               if not arcpy.Exists('in_imp_' + buff):
                  arcpy.sa.ExtractByMask(in_imp0, in_buff).save('in_imp_' + buff)
               in_imp = 'in_imp_' + buff
               buff = '_' + buff
            else:
               in_LandCover = in_LandCover0
               in_canopy = in_canopy0
               in_imp = in_imp0

            # Create metric tables for original and sub-catchments
            add_NLCD_LCmetrics(c, 'lc_table_' + cnm + buff, in_LandCover, zone_field=czn)
            # Canopy and Impervious use a (NLCD water) mask
            arcpy.env.mask = mask
            if arcpy.Exists(in_canopy):
               add_zs(c, 'canopy_' + cnm + buff, in_canopy, "MEAN", zone_field=czn)
               arcpy.AlterField_management('canopy_' + cnm + buff, 'MEAN', 'percCAN', clear_field_alias=True)
            add_zs(c, 'imp_' + cnm + buff, in_imp, "MEAN", zone_field=czn)
            arcpy.AlterField_management('imp_' + cnm + buff, 'MEAN', 'percIMP', clear_field_alias=True)

            # Create/populate master feature class catchment table ('catID' ['Value' in the raster] is unique ID)
            if cnm == 'Catchment':
               new_Catchments = 'NHDPlusCatchment_metrics'
               if not arcpy.Exists(new_Catchments):
                  arcpy.CopyFeatures_management(in_Catchments0, new_Catchments)
            else:
               new_Catchments = os.path.basename(c)
               if not arcpy.Exists(new_Catchments):
                  arcpy.CopyFeatures_management(c, new_Catchments)

            # Loop over tables, joining to master catchment layer
            tabs = arcpy.ListTables('*_' + cnm + buff)
            for t in tabs:
               print('Joining `' + t + '`...')
               flds = [a.name for a in arcpy.ListFields(t)]
               fld = [f for f in flds if f.startswith('perc') or f.startswith('area')]  #  f.startswith('VALUE_') or
               if buff != "":
                  for f in fld:
                     arcpy.AlterField_management(t, f, f + buff, clear_field_alias=True)
                  fld = [f + buff for f in fld]
               arcpy.JoinField_management(new_Catchments, cid, t, czn, fld)
               arcpy.Delete_management(t)
      # end NLCD


      ### Non year-specific variables

      # Set up geodatabase
      ws = r'E:\git\HealthyWaters\inputs\catchments\catMetrics_noYear.gdb'
      if not os.path.exists(ws):
         arcpy.CreateFileGDB_management(os.path.dirname(ws), os.path.basename(ws))
      arcpy.env.workspace = ws

      # Catchment copies
      if cnm == 'Catchment':
         new_Catchments = 'NHDPlusCatchment_metrics'
         if not arcpy.Exists(new_Catchments):
            arcpy.CopyFeatures_management(in_Catchments0, new_Catchments)
      else:
         new_Catchments = os.path.basename(c)
         if not arcpy.Exists(new_Catchments):
            arcpy.CopyFeatures_management(c, new_Catchments)

      ### Crop frequencies
      # These use the open water mask
      mask = src_gdb + os.sep + "lc_2016_nowater"
      arcpy.env.mask = mask
      ls = ['cornfreq', 'cottonfreq', 'soyfreq', 'wheatfreq']
      for i in ls:
         crop = src_gdb + os.sep + i + '_proj'
         for buff in buffs:
            if buff == "":
               varname = 'freq' + i.replace('freq', '').upper()
               rast = crop
            else:
               in_buff = fdbuff + buff
               varname = 'freq' + i.replace('freq', '').upper() + '_' + buff
               rast = i + '_' + buff
               if not arcpy.Exists(rast):
                  print('Creating ' + rast + ' raster...')
                  arcpy.sa.ExtractByMask(crop, in_buff).save(i + '_' + buff)
            # Catchments
            add_zs(c, i, rast, 'MEAN', zone_field=czn)
            arcpy.AlterField_management(i, 'MEAN', varname, clear_field_alias=True)
            arcpy.JoinField_management(new_Catchments, cid, i, czn, varname)
         arcpy.Delete_management(i)


      ### Road crossings
      arcpy.env.mask = None
      out = 'roadcross'
      varname = 'numRDCRS'
      rast = src_gdb + os.sep + out
      # Catchments
      add_zs(c, out, rast, 'SUM', zone_field=czn)
      arcpy.AlterField_management(out, 'SUM', varname, clear_field_alias=True)
      arcpy.JoinField_management(new_Catchments, cid, out, czn, varname)
      arcpy.Delete_management(out)


      ### Add new variables here


main()
