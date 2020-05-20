# ---------------------------------------------------------------------------
# procSSURGO.py
# Version: 
# Creation Date: 2020-05-19
# Last Edit: 2020-05-19
# Creator: Kirsten R. Hazler
#
# Summary: Functions for processing SSURGO data
#
# Adapted from toolbox tools and scripts used to produce the 2017 edition of the ConservationVision Watershed Model
# For background reference see Natural Heritage Technical Report 18-16
# ---------------------------------------------------------------------------

# Import modules
import arcpy, os

def RunoffScore():
   '''To the muaggatt table and the MUPOLYGON feature class, adds a field called "runoffScore", with scores from 0 (no runoff) to 100 (high runoff).
   Scores are based on drainage classes per Table 2, page 27 in NHTR 18-16.
   This function modifies the input data by adding new fields. It does not modify existing fields.
   Parameters:
   - in_GDB: input gSSURGO geodatabase
   '''

   muaggatt = in_GDB + os.sep + "muaggatt"
   mupolygon = in_GDB + os.sep + "MUPOLYGON"
   
   # Create a field in the muaggatt table to store the runoff score value, and calculate
   arcpy.AddField_management(muaggatt, "runoffScore", "SHORT")
   codeblock = '''def score(drainclass):
      # Create a dictionary relating drainage classes to scores
      s = dict()
      s["Very poorly drained"] = 100
      s["Poorly drained"] = 90
      s["Somewhat poorly drained"] = 75
      s["Moderately well drained"] = 50
      s["Well drained"] = 25
      s["Somewhat excessively drained"] = 10
      s["Excessively drained"] = 0
      
      try: 
         score = s[drainclass]
      except:
         score = 0
      
      return score
   '''
   expression = "score(!drclassdcd!)" 
   arcpy.CalculateField_management (muaggatt, "runoffScore", expression, 'PYTHON', codeblock)

   # Process: Join Runoff Score to MUPOLYGON
   arcpy.JoinField_management(MUPOLYGON, "MUKEY", muaggatt, "mukey", "runoffScore")

   return

