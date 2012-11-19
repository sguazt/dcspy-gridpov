#! /usr/bin/python

""" Python client for distributed rendering using POV-Ray.

    Split the rendering job in several rendering task, each of which is
    assigned to a (remote) machine via a Grid scheduler.
    Currently the only supported scheduler is OurGrid MyGrid.

    Based on an idea of George Pantazopoulos (http://www.gammaburst.com)


    Copyright (C) 2007-2012  Distributed Computing System (DCS) Group, Computer
    Science Department - University of Piemonte Orientale, Alessandria (Italy).

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Author: Marco Guazzone, <marco.guazzone@gmail>
"""

# ChangeLog:
#   [2009-05-13]: Version 0.2.1f
#    * BUGFIX: progress bar text remains to 99% after completion (solution: use
#      'int' instead of 'round').
#    * BUGFIX: index out-of-bound during tile generation (solution: added sanity
#      checks and default assignements to 1).
#
#   [2009-05-12]: Version 0.2.1e
#    * NEW: Added progress bar.
#    * UPDATE: Added fall-back logic for configuration parameter "mygrid-cmd"
#      (for the XML scene file): if the "mygrid-cmd" element is missing (or is
#      empty), the env variable "MGROOT" is first searched and if it is not
#      found it is assumed the "mygrid" path is in the system bin path.
#    * UPDATE: Added fall-back logic for configuration parameter "povray-cmd"
#      (for the XML scene file): if the "povary-cmd" element is missing (or is
#      empty), it is assumed the "povray" path is in the system bin path.
#    * UPDATE: e-mail address
#
#   [2008-09-26]: Version 0.2.1d
#    * NEW: Added configuration parameter "povray-libs" for the XML scene file.
#    * UPDATE: Changed requirements: "environment = povray" becomes
#      "povray = true"
#
#   [2007-05-22]: Version 0.2.1c
#    * NEW: Added new option "--title" for allowing to set the title of the
#      render preview window. 
#
#   [2007-05-17]: Version 0.2.1b
#    * NEW: Added a check for avoiding problems when the master-thread is faster
#      than display-thread; infact, in these cases the master-thread can re-find
#      tile files related to tiles already inserted in the "tiles to display"
#      queue.
#    * NEW: Added creation of tile sentil files (*.done) for avoiding cases
#      where the display-thread load a partial tile image file (i.e. a file
#      hasn't yet finished to be downloaded).
#    * BUGFIX: Added check on tile existence when producing JDF for
#      multi-core/cpu part if the number of tiles was not divisible by the
#      number of cores/cpus, an exception were thrown; now the program simply
#      check the number of available tiles before working with them.
#
#   [2007-05-06]: Version 0.2.1
#    * NEW: Added multi-cpu/core support (and option --ncpu to set the number of
#      cpu)
#
#   [2007-05-01]: Version 0.2.0
#    * NEW: Improved producer/consumer thread interaction
#    * BUGFIX: on error threads may hang
#    * UPDATE: Code refactory/rewriting
#    * NEW: XML configuration
#    * NEW: New command line options
#
#   [2007-04-26]: Initial Release (Version 0.1.0)

import pygtk
pygtk.require('2.0')
import gtk

import gc
import glob
import gobject
from gridpovconf import gridpovconf
import Queue
import re
from optparse import OptionParser
import os
import os.path
import sys
import tempfile
import threading
from tilelib import genStartAndEndCoords, MakeTileGrid, MakeSpiralTileList
import time

g_name    = "gridpov"
g_version = "0.2.1f"
    
g_tiles_to_display = Queue.Queue() # producer-consumer queue
g_options = 0 # command line options
g_jdf = 0 # JDF file handle
g_tilesMap = {} # tiles map <tile-id> => <tile-info>
g_pid = os.getpid() # this process identifier
g_conf = 0 # configuration object
g_pbmain = 0 # The main pixbuf canvas
g_image  = 0 # The raw image
g_progress_bar = 0 # The progress bar
#g_start_time = 0 # Program starting time
#g_stop_time = 0 # Program stopping time
g_tmpdir = tempfile.gettempdir()
g_povWrapShs = [] # collection of file handles of povray wrapper shell scripts
g_imageFmtExt = "png"

# -----------------------------------------------------------------------------

class MasterRenderThread(threading.Thread):
	""" Collect tile files and pass them to the display-thread.
	    Its role is the producer for the 'g_tiles_to_display' queue.
	"""

	stopthread = threading.Event() # When set, says the thread should terminate

	def __init__(self):
		""" The constructor """

		threading.Thread.__init__(self)

		self.startTime = 0
		self.stopTime = 0

		pass

	def run(self):
		""" The thread body """

		global g_tilesMap
		global g_conf
		global g_options
		global g_num_x_tiles, g_num_y_tiles
		#global g_stop_time
		global g_jdf
		global g_tiles_to_display
		global g_tmpdir
		global g_imageFmtExt

		# Initializa time stats
		self.startTime = time.time()

		# Generate tiles
		unrendered_tiles = GenerateTiles(
				g_conf.sceneWidth(),
				g_conf.sceneHeight(),
				g_num_x_tiles,
				g_num_y_tiles
		)
		unrendered_tiles.reverse()
		num_total_tiles = len(unrendered_tiles)

		for t in unrendered_tiles:
			g_tilesMap[ t["id"] ] = t
			if g_options.verbose:
				print "Generated tile: <#" + str(t["id"]) + "," + str(t["sc"]) + "," + str(t["ec"]) + "," + str(t["sr"]) + "," + str(t["er"]) + ">"

		# Generate JDF file
		if g_options.verbose:
			print "Generating JDF ..."
		GenerateJDF()
		if g_options.verbose:
			print "Generated JDF: " + g_jdf.name

		# Add the job to MyGrid
		if g_options.verbose:
			print "Adding job to MyGrid ..."
		mygridpid = os.spawnl( os.P_NOWAIT, g_conf.mygridCmd(), g_conf.mygridCmd(), "addjob", g_jdf.name )
		if g_options.verbose:
			print "Added job to MyGrid - PID: " + str( mygridpid )

		# while the number of rendered tiles is less than
		# the total tiles, wait.
		renderedTiles = 0
		renderedTilesId = {}
		while (renderedTiles < num_total_tiles) and (not DisplayThread.stopthread.isSet()) and (not MasterRenderThread.stopthread.isSet()):
			time.sleep(3)

			readyTileFNames = glob.glob( g_tmpdir + "/" + GenerateTileFilePrefix( g_conf.povrayOutputFile(), "" ) + "*." + g_imageFmtExt )

			if g_options.verbose:
				print "Checks for tile files '" + g_tmpdir + "/" + GenerateTileFilePrefix( g_conf.povrayOutputFile(), "" ) + "*" + "'. Found " + str(len( readyTileFNames )) + " files"

			for tilefname in readyTileFNames:
				if g_options.verbose:
					print "Tile-file: " + tilefname

				if os.stat( tilefname ).st_size == 0:
					if g_options.verbose:
						print "Tile-file #" + tilefname + " has zero size. Skip."
					continue

				id = int( re.search("(?:-tile-)([0-9]+)", tilefname).group(1) );

				sentinelFile = g_tmpdir + "/" + GenerateTileSentinelFileName( g_conf.povrayOutputFile(), id )
				if not os.path.exists( sentinelFile ):
					if g_options.verbose:
						print "Sentinel Tile-file " + sentinelFile + " not yet present. Skip."
					continue

				if renderedTilesId.has_key(id):
					if g_options.verbose:
						print "Tile #" + str(id) + " already in the display queue."
					continue

				if g_options.verbose:
					print "Going to put Tile #" + str(id) + " in the display queue."


				tile = g_tilesMap[id]
				# Queue the tile up for display
				g_tiles_to_display.put_nowait(tile)
				renderedTiles += 1
				renderedTilesId[id] = True

		#FIXME: almost likely not needed
		# Wait for MyGrid termination
		if g_options.verbose:
			print "Waiting for MyGrid ..."
		os.waitpid( mygridpid, 0 )
		if g_options.verbose:
			print "Waited for MyGrid"

		# update time stats
		#g_stop_time = time.time()
		self.stopTime = time.time()

		self.showStats()

		if g_options.verbose:
			print "Master Render Thread is done"

		pass

	def showStats(self):
		""" Show rendering statistics. """

		global g_options
		global g_num_x_tiles, g_num_y_tiles
		#global g_start_time, g_stop_time

		#totalTime = g_stop_time - g_start_time
		totalTime = self.stopTime - self.startTime
		( min, secs ) = divmod( totalTime, 60 )

		if not g_options.quiet:
			print ""
			print "--- Rendering Summary ----------------------------------------------------------"
			print "  Image Settings: " + str(g_num_x_tiles) + "x" + str(g_num_y_tiles) + " tiles"
			print "  Total Rendering time: " + str(int(min)) + "m " + str(int(secs)) + "s (" + str(totalTime) + "s)"
			print "--------------------------------------------------------------------------------"
			print ""
		pass

	def stop(self):
		""" Stops the thread. """

		global g_conf
		global g_imageFmtExt

		# Save scene
		#  save the image
		# FIXME:
		#  1. Parameterize file extension
		#  2. Parameterize output path
		g_pbmain.save( g_conf.povrayOutputFile(), g_imageFmtExt, {})
		MasterRenderThread.stopthread.set()

		pass

# -----------------------------------------------------------------------------

class DisplayThread(threading.Thread):
	""" Visualize tiles stored in the 'g_tiles_to_display' queue.
	    Its role is the consumer for the 'g_tiles_to_display' queue.
	"""

	stopthread = threading.Event() # When set, says the thread should terminate

	#def __init__(self, tile_q):
	def __init__(self):
		threading.Thread.__init__(self)
		#self.tile_q = tile_q
		pass

	def run(self):
		""" The thread body. """

		global g_options
		global g_conf
		global g_pbmain, g_image, g_progress_bar
		global g_tmpdir

		# loop until until terminated
		while (not DisplayThread.stopthread.isSet()) and (not MasterRenderThread.stopthread.isSet()):

			try:

				# block on queue and wait for a tile to become available
				#tile = self.tile_q.get()
				tile = g_tiles_to_display.get()
				if not tile: # case: tile == None
					break

				# If we got woken up on purpose so we can exit,
				# we want to exit here, before trying to display a fake tile
				if (DisplayThread.stopthread.isSet()):
					break

				# Update the progress bar

				progress = g_progress_bar.get_fraction()+1.0/(g_num_x_tiles*g_num_y_tiles)
				if progress > 1.0:
					progress = 1.0

				if g_options.verbose:
					print "Advancing progress: " + str(progress) + " (" + str(round(progress*100)) + "%)"

				g_progress_bar.set_fraction(progress);
				g_progress_bar.set_text(str(round(progress*100)) + "%");

				# Display the tile

				# Paste our tile into the appropriate location in the main pixbuf
				tid = int(tile['id'])
				sc = int(tile['sc'])
				ec = int(tile['ec'])
				sr = int(tile['sr'])
				er = int(tile['er'])                
				if g_options.verbose:
					print "tile: [" + str(tid) + "] = <" + str(sc) + "," + str(ec) + "," + str(sr) + "," + str(er) + ">";

				tile_width  = (ec-sc) + 1
				tile_height = (er-sr) + 1

				x_offset = sc - 1 # sc starts at 1
				y_offset = sr - 1 # sr starts at 1

				# Now that we have a file saved, create a gtk Pixbuf to hold our tile.

				tileFile = g_tmpdir + "/" + GenerateTileFileName( g_conf.povrayOutputFile(), tid )
				tileSentinelFile = g_tmpdir + "/" + GenerateTileSentinelFileName( g_conf.povrayOutputFile(), tid )
				if g_options.verbose:
					print "Loading image from: " + str( gtk.gdk.pixbuf_get_file_info( tileFile ) )

				gtk.gdk.threads_enter() # acquire lock

				# Create the pixbuf from the tile file
				tile_pb = gtk.gdk.pixbuf_new_from_file_at_size(
						tileFile,
						g_conf.sceneWidth(),
						g_conf.sceneHeight()
				)
				if g_options.verbose:
					print "Created pixbuf: " + str(tile_pb.get_width()) + "x" + str(tile_pb.get_height())
				#POV-Ray creates PNGs with incorrect size params
				# (the size of the original image). So we need to extract
				# our actual rendered region/
				# For now, only use vertical stripe tiles
				tile_pb.copy_area(
					x_offset, 0,#y_offset, # This hack is necessary to work with POV's screwed up PNG's
					tile_width, tile_height,
					g_pbmain,
					x_offset, y_offset
				)

				if g_options.verbose:
					print "Copied pixbuf portion " + str(tile_width) + "x" + str(tile_height) + " at (" + str(x_offset) + ", " + str(0) + ") to Main pixbuf at (" + str(x_offset) + ", " + str(y_offset) + ")"

				# update the main pixbuf                
				g_image.set_from_pixbuf(g_pbmain)

				if g_options.verbose:
					print "Updated image from pixbug"

				# With PyGTK, the pixbuf does not get destroyed
				# when we go out of scope, leading to increasing memory usage.
				# According to the FAQ,
				# the solution is to prod the garbage collector.
				# Hopefully this won't slow things down too much here.
				gc.collect()

				gtk.gdk.threads_leave() # release lock

				# delete the image file now that we don't need it anymore.
				os.remove( tileFile )
				os.remove( tileSentinelFile )
			# This should catch Decompression errors with POV's wierd PNGs
			except gobject.GError, msg:
				if not g_options.quiet:
					print "Caught exception in DisplayThread: " + str(msg) + " ... continuing"
				gtk.gdk.threads_leave() # release any lock
				continue
			except OSError, msg:
				if not g_options.quiet:
					print "Caught exception in DisplayThread: " + str(msg) + " ... continuing"
				gtk.gdk.threads_leave() # release any lock
				continue

		if g_options.verbose:
			print "Display Thread is done"

		pass

	def stop(self):
		""" Stops the thread. """

		DisplayThread.stopthread.set()
		# Put in a fake tile to unblock thread.
		#self.tile_q.put_nowait(None)       
		g_tiles_to_display.put_nowait(None)       

		pass

# -----------------------------------------------------------------------------

def GenerateTiles(img_w, img_h, nx, ny):
	""" Generates a tile according to the given parameters. """

	if g_options.verbose:
		print ">> Generating tiles: " + str(img_w) + "x" + str(img_h) + " <" + str(nx) + "," + str(ny) + ">"

	tileGrid = MakeTileGrid(img_w, img_h, nx, ny)   
	return MakeSpiralTileList(nx, ny, tileGrid)

# -----------------------------------------------------------------------------

def GenerateTileFilePrefix(outfile, tid):
	""" Generate a prefix for a tile file. """

	global g_pid

	(sceneBaseName, sceneExt) = os.path.splitext( outfile )
	return sceneBaseName + "-" + str( g_pid ) + "-tile-" + str( tid )

# -----------------------------------------------------------------------------

def GenerateTileFileName(outfile, tid):
	""" Generates a file name for the given tile. """

	global g_pid

	(sceneBaseName, sceneExt) = os.path.splitext( outfile )
	return GenerateTileFilePrefix(outfile, tid) + sceneExt

# -----------------------------------------------------------------------------

def GenerateTileSentinelFileName(outfile, tid):
	""" Generates a sentinel file name for the given tile. """

	global g_pid

	(sceneBaseName, sceneExt) = os.path.splitext( outfile )
	return GenerateTileFilePrefix(outfile, tid) + ".done"

# -----------------------------------------------------------------------------

def GeneratePovrayCmd():
	""" Generates a POV-Ray command string. """

	global g_conf

	povrayCmd = g_conf.povrayCmd()
	povrayCmd += " -D" # Disable visualization
	#povrayCmd += " -GA" # Disable all streams output (console, stats, ...)
	#povrayCmd += " -GD" # Disable all streams output (console, stats, ...)
	#povrayCmd += " -GF" # Disable all streams output (console, stats, ...)
	#povrayCmd += " -GR" # Disable all streams output (console, stats, ...)
	#povrayCmd += " -GS" # Disable all streams output (console, stats, ...)
	#povrayCmd += " -GW" # Disable all streams output (console, stats, ...)
	#povrayCmd += " -GI" # Disable INI output
	#povrayCmd += " -V" # Disable verbosity
	povrayCmd += " +F" + g_conf.sceneImageFormat() # Output format
	povrayCmd += " +W" + str( g_conf.sceneWidth() ) # Scene Width
	povrayCmd += " +H" + str( g_conf.sceneHeight() ) # Scene Height
	if g_conf.sceneBoundingThreshold():
		povrayCmd += " +MB" + str( g_conf.sceneBounding() ) # Scene Bounding Threshold
	if g_conf.sceneQuality():
		povrayCmd += " +Q" + str( g_conf.sceneQuality() ) # Scene Quality
	if g_conf.sceneAntialiasThreshold():
		povrayCmd += " +A0." + str( g_conf.sceneAntialiasThreshold() ) # Scene Anti-Alias Threshold
	if g_conf.sceneSamplingMethod():
		povrayCmd += " +AM." + str( g_conf.sceneSamplingMethod() ) # Scene Sampling Method
	if g_conf.sceneJitterAmount():
		povrayCmd += " +J" + str( g_conf.sceneJitterAmount() ) # Scene Jitter Amount
	if g_conf.sceneAntialiasDepth():
		povrayCmd += " +R" + str( g_conf.sceneAntialiasDepth() ) # Scene Anti-Alias Depth
	if g_conf.sceneOutputAlpha():
		povrayCmd += " +UA" + str( g_conf.sceneOutputAlpha() ) # Scene Output Alias
	if g_conf.sceneLightBuffer():
		povrayCmd += " +UL" + str( g_conf.sceneLightBuffer() ) # Scene Light Buffer
	if g_conf.sceneVistaBuffer():
		povrayCmd += " +UV" + str( g_conf.sceneVistaBuffer() ) # Scene Vista Buffer
	for povLib in g_conf.povrayLibs():
		povrayCmd += " +L" + str( povLib ) # povray library

	return povrayCmd

# -----------------------------------------------------------------------------

def GenerateJDF():
	""" Generates a JDF file. """

	global g_jdf
	global g_conf
	global g_tilesMap
	global g_tmpdir
	global g_povShs

	try:
		g_jdf = tempfile.NamedTemporaryFile( "w", 1, ".jdf" )
		g_jdf.write( "job:" + "\n" )
		g_jdf.write( "  label: " + g_conf.sceneLabel() + "\n" )
		#g_jdf.write( "  requirements: (environment = povray)\n" )
		g_jdf.write( "  requirements: (povray = true)\n" )
		if g_options.ncpu == 1:
			g_jdf.write( "  init:\n" )
			for locfn in g_conf.sceneFiles():
				remfn = g_conf.mygridJdfStorePath() + "/" + os.path.basename( locfn )
				g_jdf.write( "    " + g_conf.mygridJdfStoreMethod() + " " + locfn + " " + remfn + "\n" )
			g_jdf.write( "\n" )

		povrayCmd = GeneratePovrayCmd()

		if g_options.ncpu == 1:
			for tid in g_tilesMap.keys():
				tile = g_tilesMap[ tid ]
				povrayArgs = ""
				povrayArgs += " +SR" + str( tile['sr'] )
				povrayArgs += " +ER" + str( tile['er'] )
				povrayArgs += " +SC" + str( tile['sc'] )
				povrayArgs += " +EC" + str( tile['ec'] )

				g_jdf.write( "task:\n" )
				remoteStr = ""
				finalStr = ""
				for execStep in g_conf.povrayExecSteps():
					if remoteStr:
						remoteStr += "; "
					remoteStr += povrayCmd + " " + povrayArgs
					remoteStr += " +I" + g_conf.mygridJdfStorePath() + "/" + g_conf.povrayExecStepInputFile(execStep)
					if g_conf.povrayExecStepOutputFile(execStep):
						tileFName = GenerateTileFileName( g_conf.povrayExecStepOutputFile(execStep), tid )
						remoteFile = g_conf.mygridJdfTempPath() + "/" + tileFName + ".$JOB.$TASK"
						localFile = g_tmpdir + "/" + tileFName
						remoteStr += " +O" + remoteFile
						finalStr += "    get " + remoteFile + " " + localFile + "\n"
				# Note: before running POVRAY we need to move to the 'store' directory because
				#       it may happens some scene need to include other files (not distributed with
				#       POV-Ray but package with scene files)
				#g_jdf.write( "  remote: cwd=$PWD && cd " + g_conf.mygridJdfStorePath() + " && " + remoteStr + " && cd $cwd" + "\n" ) # FIXME: very good but less portable
				if not remoteStr:
					if not g_options.quiet:
						print "Nothing to do for rendering tile #" + tid
					continue

				##@{ FIXME: trick for avoiding cases where the display thread try to show a file while its download is not already terminated
				remoteSentinelFile = g_conf.mygridJdfTempPath() + "/" + GenerateTileSentinelFileName( g_conf.povrayOutputFile(), tid )
				localSentinelFile = g_tmpdir + "/" + GenerateTileSentinelFileName( g_conf.povrayOutputFile(), tid )
				remoteStr += "; "
				remoteStr += " echo 1 >" + remoteSentinelFile
				finalStr += "    get " + remoteSentinelFile + " " + localSentinelFile + "\n"
				##@} FIXME: trick for avoiding cases where the display thread try to show a file while its download is not already terminated

				g_jdf.write( "  remote: cd " + g_conf.mygridJdfStorePath() + "; " + remoteStr + "\n" )
				g_jdf.write( "  final: " + finalStr + "\n" )
		else:
			tids = g_tilesMap.keys()
			while len( tids ) > 0:
				remoteStr = ""
				finalStr = ""
				for execStep in g_conf.povrayExecSteps():
					# Creates a temp file for the povray wrapper shell script
					povWrapSh = tempfile.NamedTemporaryFile( "w", 1, ".sh" )
					# Addes the file handle to the global list (for clean-up purposes)
					g_povWrapShs.append( povWrapSh )

					## Moves to store path (i.e. where scene files are located)
					#povWrapSh.write( "cd " + g_conf.mygridJdfStorePath() + "\n" )

					pidsStr = ""
					for ncpu in range( g_options.ncpu ):
						if len( tids ) == 0:
							break

						tid = tids.pop(0)

						tile = g_tilesMap[ tid ]
						povrayArgs = ""
						povrayArgs += " +SR" + str( tile['sr'] )
						povrayArgs += " +ER" + str( tile['er'] )
						povrayArgs += " +SC" + str( tile['sc'] )
						povrayArgs += " +EC" + str( tile['ec'] )

						remoteCmd = ""
						remoteCmd += povrayCmd + " " + povrayArgs
						remoteCmd += " +I" + g_conf.mygridJdfStorePath() + "/" + g_conf.povrayExecStepInputFile(execStep)

						if g_conf.povrayExecStepOutputFile(execStep):
							tileFName = GenerateTileFileName( g_conf.povrayExecStepOutputFile(execStep), tid )
							#remoteFile = g_conf.mygridJdfTempPath() + "/" + tileFName + ".$JOB.$TASK"
							remoteFile = g_conf.mygridJdfTempPath() + "/" + tileFName
							localFile = g_tmpdir + "/" + tileFName
							remoteCmd += " +O" + remoteFile
							finalStr += "    get " + remoteFile + " " + localFile + "\n"
							#@{ FIXME: trick for avoiding cases where the display thread try to show a file while its download is not already terminated
							remoteSentinelFile = g_conf.mygridJdfTempPath() + "/" + GenerateTileSentinelFileName( g_conf.povrayOutputFile(), tid )
							localSentinelFile = g_tmpdir + "/" + GenerateTileSentinelFileName( g_conf.povrayOutputFile(), tid )
							finalStr += "    get " + remoteSentinelFile + " " + localSentinelFile + "\n"
							if remoteStr:
								remoteStr += "; "
							remoteStr += "echo 1 >" + remoteSentinelFile
							#@} FIXME: trick for avoiding cases where the display thread try to show a file while its download is not already terminated


						povWrapSh.write( remoteCmd + " & \n" )
						povWrapSh.write( "pid" + str( ncpu ) + "=$!\n" )
						if pidsStr:
							pidsStr += " "
						pidsStr += "$pid" + str( ncpu )

					if pidsStr:
						povWrapSh.write( "wait " + pidsStr + "\n" )
						povWrapSh.write( "exit $?\n" )

				g_jdf.write( "task:\n" )
				#g_jdf.write( "  init: " + g_conf.mygridJdfStoreMethod() + " " + povWrapSh.name + " " + g_conf.mygridJdfTempPath() + "/" + os.path.basename( povWrapSh.name ) + "\n" )
				g_jdf.write( "  init:\n" )
				for locfn in g_conf.sceneFiles():
					remfn = g_conf.mygridJdfStorePath() + "/" + os.path.basename( locfn )
					g_jdf.write( "    " + g_conf.mygridJdfStoreMethod() + " " + locfn + " " + remfn + "\n" )
				g_jdf.write( "    " + g_conf.mygridJdfStoreMethod() + " " + povWrapSh.name + " " + g_conf.mygridJdfTempPath() + "/" + os.path.basename( povWrapSh.name ) + "\n" )
				g_jdf.write( "\n" )
				g_jdf.write(
					"  remote: cd " + g_conf.mygridJdfStorePath()
					+ "; export STORAGE=$STORAGE"
					+ "; export PLAYPEN=$PLAYPEN"
##@{ DEBUG: Uncomment this for debugging purpose
#					+ "; echo \"### STORE_PATH: " + g_conf.mygridJdfStorePath() + " ###\" >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
#					+ "; ls " + g_conf.mygridJdfStorePath() + " >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
#					+ "; echo \"### TEMP_PATH: " + g_conf.mygridJdfTempPath() + " ###\" >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
#					+ "; ls " + g_conf.mygridJdfTempPath() + " >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
#					+ "; echo \"### STORAGE: $STORAGE ###\" >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
#					+ "; ls $STORAGE >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
#					+ "; echo \"### PLAYPEN: $PLAYPEN ###\" >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
#					+ "; ls $PLAYPEN >>" + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK;" #XXX
##@} DEBUG: Uncomment this for debugging purpose
					+ "; sh " + g_conf.mygridJdfTempPath() + "/" + os.path.basename( povWrapSh.name )
					+ "; " + remoteStr 
					+ "\n"
				)
##@{ DEBUG: Uncomment this for debugging purpose
#				finalStr += "get " + g_conf.mygridJdfStorePath() + "/debug.$JOB.$TASK debug.$JOB.$TASK\n" #XXX
##@} DEBUG: Uncomment this for debugging purpose

				g_jdf.write( "  final:\n" + finalStr + "\n" )
	finally:
		if not g_jdf:
			raise "Failed to create JDF file!"
	pass

# -----------------------------------------------------------------------------

def main_quit(obj):
	""" Handler for GUI window destroying. """

	global g_options

	if g_options.verbose:
		print "doing gtk.main_quit()"
	gtk.main_quit()
	if g_options.verbose:
		print "gtk.main_quit() done"

	pass

# -----------------------------------------------------------------------------

def InitGui():
	""" Initialize and show the GUI subsystem. """

	global g_options
	global g_name, g_version
	global g_pbmain, g_image, g_progress_bar
	global g_conf

	g_pbmain = gtk.gdk.Pixbuf(
			gtk.gdk.COLORSPACE_RGB,
			False,
			8,
			g_conf.sceneWidth(),
			g_conf.sceneHeight()
	)

	g_image = gtk.Image()
	g_image.set_from_pixbuf(g_pbmain)
	g_image.show()

	g_progress_bar = gtk.ProgressBar()
	g_progress_bar.set_text("0.0%")

	vbox = gtk.VBox(False, 0)
	#align = gtk.Alignment(0.5, 0.5, 0, 0)
	#vbox.pack_start(align, True, True, 5)
	#align.add(g_image)
	#align.show()
	vbox.pack_start(g_image);
	#align = gtk.Alignment(0.5, 0.5, 0, 0)
	#vbox.pack_end(align, True, True, 0)
	#align.add(g_progress_bar)
	#align.show()
	vbox.pack_end(g_progress_bar);
	vbox.show()

	window = gtk.Window(gtk.WINDOW_TOPLEVEL)
	window.add(vbox)
	window.connect('destroy', main_quit)
	if g_options.title:
		window.set_title( g_options.title )
	else:
		window.set_title( "GRID Render Preview - " + g_name + " " + g_version )
	window.show_all()

	pass

# -----------------------------------------------------------------------------

def main():
	""" Application starting point. """

	global g_options
	global g_conf
	global g_num_x_tiles, g_num_y_tiles
	global g_tiles_to_display
	global g_name, g_version
	#global g_stop_time
	global g_jdf
	global g_povWrapSH

	#if len(sys.argv) < 1:
	#    print "Usage: " + str(sys.argv[0]) + " <XML-conf-file>"
	#    sys.exit(1)
    
	optparser = OptionParser()
	optparser.add_option( "-c", "--conf" , dest="conf", help="XML Configuration file name" )
	optparser.add_option( "-n", "--ncpu" , dest="ncpu", action="store", type="int", help="Number of GuM cpus" )
	optparser.add_option( "-q", "--quiet" , dest="quiet", action="store_true", help="Do not display any message" )
	optparser.add_option( "-t", "--title" , dest="title", help="Render Preview window title" )
	optparser.add_option( "-v", "--verbose" , dest="verbose", action="store_true", help="Prints out diagnostic messages" )
	(g_options, args) = optparser.parse_args()
	if len( args ) != 0:
		optparser.error( "Incorrect number of arguments" )
	if not g_options.conf:
		optparser.error( "Configuration file needed" )
	if g_options.ncpu <= 0:
		g_options.ncpu = 1

	if not g_options.quiet:
		print ""
		print "--------------------------------------------------------------------------------"
		print g_name + " version " + g_version
		print "  Python GRID-based POV-Ray render"
		print "  by Marco Guazzone, <marco.guazzone@gmail.com>"
		print "  UPO -- Distributed Computing System Group [http://dcs.di.unipmn.it]"
		print "--------------------------------------------------------------------------------"
		print ""

	g_conf = gridpovconf( g_options.conf )

	g_num_x_tiles = g_conf.sceneWidth()  / g_conf.sceneBlockSize()
	g_num_y_tiles = g_conf.sceneHeight() / g_conf.sceneBlockSize()

	# sanity checks
	if g_num_x_tiles == 0:
		g_num_x_tiles = 1;
	if g_num_y_tiles == 0:
		g_num_y_tiles = 1;

	gtk.gdk.threads_init()

	InitGui()

	## See Master Render Thread for when we stop the timer.
	#g_start_time = time.time()

	threads = []

	try:
		if g_options.verbose:
			print ">> Creating Master Render Thread"
		masterRenderThread = MasterRenderThread()

		if g_options.verbose:
			print ">> Creating Display Thread"
		#displayThread = DisplayThread(g_tiles_to_display)
		displayThread = DisplayThread()

		threads.append(masterRenderThread)
		threads.append(displayThread)

		if g_options.verbose:
			print ">> Starting helper and work threads"
		for t in threads:
		    t.start()
		    
		if g_options.verbose:
			print ">> Main thread is going into gtk.main()"
		gtk.gdk.threads_enter()
		gtk.main()
		gtk.gdk.threads_leave()
		if g_options.verbose:
			print ">> Broke out from gtk.main()"

	finally:
		if g_options.verbose:
			print ">> Stopping threads"
		for t in threads:
		    t.stop()
		if g_options.verbose:
			print ">> Issued stop commmands"

		if g_options.verbose:
			print ">> Waiting for threads to finish"
		for t in threads:
		    t.join()
		if g_options.verbose:
			print ">> All threads finished"

		# Closes and removes JDF file
		if g_jdf:
			g_jdf.close()
	
		# Closes and removes povray wrapper script files
		for povWrapSh in g_povWrapShs:
			povWrapSh.close()

	if g_options.verbose:
		print ">> Exiting."

	pass

if __name__ == "__main__":
	main()
