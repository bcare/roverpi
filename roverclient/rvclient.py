#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# generated by wxGlade 0.6.8 on Sat Mar 26 19:54:33 2016
#

# This is an automatically generated file.
# Manual changes will be overwritten without warning!
import sys
import os
import time
import multiprocessing

import traceback

import wx
import wx.html2

import gettext


sys.path.append(os.path.abspath("../rovercommons"))


from RoverFrame import RoverFrame







class RoverApp(wx.App):
	def OnInit(self):
		wx.InitAllImageHandlers()
		RoverClientGUI = RoverFrame(None, wx.ID_ANY, "")
		self.SetTopWindow(RoverClientGUI)
                sys.stderr.write("Showing GUI...\r\n")
		RoverClientGUI.Show()
		return 1

# end of class RoverApp

if __name__ == "__main__":
        ## required for pyinstaller + windows
        multiprocessing.freeze_support()
	gettext.install("rvclient") # replace with the appropriate catalog name
        
        try:
	        rvclient = RoverApp(0)
	        rvclient.MainLoop()
        except Exception as e:
                sys.stderr.write("Error : %s\r\n%s"%(e,traceback.format_exc()))
                sys.exit(-2)
