#----------------------------------------------------
# Name: Sets water to null
# Version: ArcPro / Python 3+
# Date Created: 3-12-20
# Last Edited: 4-14-20
# Authors: Hannah Huggins/David Bucklin
#----------------------------------------------------

import arcpy
import os


def process_rasters(in_raster, template_raster, output, in_constant=None, expression=None):
   """This function masks, projects, and optionally creates a mask using SetNull,
    depending on in_constant and expression arguments.
   Parameters:
   in_raster = the raster with the values the expression is based on.
   template_raster = The raster used as a projection, cell size, and snap template
   output = This is the output raster. All output rasters will use this name pattern.
   in_constant = The constant that the values will change to if not null.
   expression = where clause determining what is null."""
   print("Masking raster...")
   #Check out the spatial extension
   arcpy.CheckOutExtension("Spatial")
   arcpy.env.snapRaster = in_raster
   arcpy.env.cellSize = in_raster
   arcpy.sa.ExtractByMask(in_raster, arcpy.env.mask).save(output)

   # Project/resample/set null
   arcpy.env.snapRaster = template_raster
   arcpy.env.cellSize = template_raster
   print("Projecting raster...")
   if in_constant:
      # this is for land cover rasters
      lc_res = arcpy.ProjectRaster_management(output, output + '_proj', template_raster, "NEAREST", "10 10")
      print('Setting values null...')
      arcpy.sa.SetNull(lc_res, in_constant, expression).save(output + '_nowater')
   else:
      # this is for canopy/impervious rasters
      arcpy.ProjectRaster_management(output, output + '_proj', template_raster, "NEAREST", "10 10")
   return output


def main():
   arcpy.env.overwriteOutput = True
   arcpy.env.workspace = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb"
   cat = r"E:\git\HealthyWaters\inputs\catchments\catchment_inputData.gdb\NHDPlusCatchment_1kmBuff_procRegion"
   arcpy.env.extent = cat
   arcpy.env.mask = cat
   template_raster = r'L:\David\GIS_data\NHDPlus_HR\HRNHDPlusRasters0208\cat.tif'

   # Land cover datasets
   # constants
   in_constant = "1"
   expression = "Value = 11"
   ls = [['lc_2016', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2016_Land_Cover_L48_20190424.img'],
         ['lc_2011', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2011_Land_Cover_L48_20190424.img'],
         ['lc_2006', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2006_Land_Cover_L48_20190424.img'],
         ['lc_2001', r'L:\David\GIS_data\NLCD\NLCD_Land_Cover_L48_20190424_full_zip\NLCD_2001_Land_Cover_L48_20190424.img']]
   for l in ls:
      in_landcover = l[1]
      if not arcpy.Exists(l[0]):
         process_rasters(in_landcover, template_raster, l[0], in_constant, expression)
         print("The output `" + l[0] + "` has been created.")

   # Impervious rasters
   ls = [['imp_2016', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2016_Impervious_L48_20190405.img'],
         ['imp_2011', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2011_Impervious_L48_20190405.img'],
         ['imp_2006', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2006_Impervious_L48_20190405.img'],
         ['imp_2001', r'L:\David\GIS_data\NLCD\NLCD_Impervious_L48_20190405_full_zip\NLCD_2001_Impervious_L48_20190405.img']]
   for l in ls:
      in_landcover = l[1]
      if not arcpy.Exists(l[0]):
         process_rasters(in_landcover, template_raster, l[0])
         print("The output `" + l[0] + "` has been created.")

   # Canopy rasters (only available for 2011, 2016)
   ls = [['treecan_2016', r'L:\David\GIS_data\NLCD\treecan2016.tif\treecan2016.tif'],
         ['treecan_2011', r'L:\David\GIS_data\NLCD\nlcd_2011_treecanopy_2019_08_31\nlcd_2011_treecanopy_2019_08_31.img']]
   for l in ls:
      in_landcover = l[1]
      if not arcpy.Exists(l[0]):
         process_rasters(in_landcover, template_raster, l[0])
         print("The output `" + l[0] + "` has been created.")

   arcpy.BuildPyramidsandStatistics_management(arcpy.env.workspace)


main()
