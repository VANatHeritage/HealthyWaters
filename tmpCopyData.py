import os
import arcpy

outGDB = r"D:\SWAPSPACE\hwProducts_20200731.gdb" 

procList = [r"E:\SpatialData\HealthyWatersWork\hwProducts_20200629.gdb\maxPrecip_gen24_topo10",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\SedYld_2001",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\SedYld_2006",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\SedYld_2011",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\SedYld_2016",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\altSedYld_2001",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\altSedYld_2006",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\altSedYld_2011",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\altSedYld_2016",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Nitrogen_2001",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Nitrogen_2006",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Nitrogen_2011",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Nitrogen_2016",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Phosphorus_2001",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Phosphorus_2006",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Phosphorus_2011",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_Phosphorus_2016",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_SuspSolids_2001",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_SuspSolids_2006",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_SuspSolids_2011",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\LocMass_SuspSolids_2016",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffDepth_2001",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffDepth_2006",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffDepth_2011",
            r"E:\SpatialData\HealthyWatersWork\hwProducts_20200710.gdb\runoffDepth_2016"]
            
nlcdList = [r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2001_10m",
            r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2006_10m",
            r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2011_10m",
            r"E:\SpatialData\NLCD_landCover.gdb\nlcd_ccap_2016_10m"
            ]

print("Starting copy function...")            
# for item in procList:
for item in nlcdList:
   bname = os.path.basename(item)
   outPath = outGDB + os.sep + bname
   try:
      arcpy.Copy_management (item, outPath)
      print("Copied %s"%bname)
   except:
      print("Failed to copy %s"%bname)
   
