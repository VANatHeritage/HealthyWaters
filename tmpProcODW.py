# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# tmpProcODW.py
# Created on: 2020-07-29 18:28:57.00000
#   (generated by ArcGIS/ModelBuilder)
# Usage: tmpProcODW <Input_Drinking_Water_Source_Points> <Output_Frequency_Population_Table> 
# Description: 
# ---------------------------------------------------------------------------

# Set the necessary product code
# import arcinfo


# Import arcpy module
import arcpy

# Script arguments
Input_Drinking_Water_Source_Points = arcpy.GetParameterAsText(0)
if Input_Drinking_Water_Source_Points == '#' or not Input_Drinking_Water_Source_Points:
    Input_Drinking_Water_Source_Points = "C:\\Users\\xch43889\\Documents\\GitHub\\DataConsolidation\\wm_Inputs_Albers.gdb\\odw_WaterSrcPts" # provide a default value if unspecified

Output_Frequency_Population_Table = arcpy.GetParameterAsText(1)
if Output_Frequency_Population_Table == '#' or not Output_Frequency_Population_Table:
    Output_Frequency_Population_Table = "C:\\Users\\xch43889\\Documents\\GitHub\\DataConsolidation\\Products_20170427.gdb\\tb_odwFreqPop" # provide a default value if unspecified

# Local variables:
Updated_Table = Output_Frequency_Population_Table

# Process: Frequency
arcpy.Frequency_analysis(Input_Drinking_Water_Source_Points, Output_Frequency_Population_Table, "PWSID;D_POPULATION_COUNT", "")

# Process: Add Field
arcpy.AddField_management(Output_Frequency_Population_Table, "ManEdit", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

