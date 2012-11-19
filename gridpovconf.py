""" Class for accessing to gridpov configuration parameters.

    Copyright (C) 2012  Distributed Computing System (DCS) Group, Computer
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

    Author: Marco Guazzone, <marco.guazzone@mfn.unipmn.it>
"""

#    ChangeLog:
#      [2007-05-14]: Release Version 0.0.2
#      [2007-05-01]: Initial Release (Version 0.0.1)

import os
import os.path
import re
import xml.dom.minidom

g_version = "0.0.2"

class gridpovconf:
	""" Give access to gridpov configurations. """

	def __init__(self, confFile):
		""" The constructor """

		self.java = {} # Java section
		self.mygridwrapper = {} # MyGridWrapper section
		self.mygrid = {} # MyGrid section
		self.povray = {} # POV-Ray section
		self.scene = {} # Scene section
		self.defOutDir = os.getcwd() # default output dir

		dom = xml.dom.minidom.parse( confFile )

		## Java section

		nodes = dom.getElementsByTagName( "dcs:java-cmd" )
		if len( nodes ) > 0:
			self.java["java-cmd"] = self.__getText(
				nodes[0].childNodes
			)
		else:
			self.java["java-cmd"] = ""

		nodes = dom.getElementsByTagName( "dcs:javac-cmd" )
		if len( nodes ) > 0:
			self.java["javac-cmd"] = self.__getText(
				nodes[0].childNodes
			)
		else:
			self.java["javac-cmd"] = ""

		self.java["cp"] = ""
		for node in dom.getElementsByTagName( "dcs:java-cp-item" ):
			if self.java["cp"]:
				self.java["cp"] += ":"

			self.java["cp"] += self.__getText(
				node.childNodes
			)

		## MyGridWrapper section

		nodes = dom.getElementsByTagName( "dcs:mygridwrapper-class" )
		if len( nodes ) > 0:
			self.mygridwrapper["class"] = self.__getText(
				nodes[0].childNodes
			)
		else:
			self.mygridwrapper["class"] = ""

		## MyGrid section

		nodes = dom.getElementsByTagName( "dcs:mygrid-cmd" )
		if len( nodes ) > 0:
			self.mygrid["cmd"] = self.__getText(
				nodes[0].childNodes
			)
		else:
			self.mygrid["cmd"] = ""

		if len(self.mygrid["cmd"]) == 0:
			if len(os.environ["MGROOT"]) > 0:
				# Retrieve mygrid from the env var
				self.mygrid["cmd"] = os.environ["MGROOT"] + "/bin/mygrid"
			else:
				# Assume the 'mygrid' is in the bin path
				self.mygrid["cmd"] = "mygrid"

		nodes = dom.getElementsByTagName( "dcs:mygrid-jdf-store-path" )
		if len( nodes ) > 0:
			self.mygrid["jdf-store-path"] = self.__getText(
				nodes[0].childNodes
			)
		else:
			self.mygrid["jdf-store-path"] = ""

		nodes = dom.getElementsByTagName( "dcs:mygrid-jdf-store-method" )
		if len( nodes ) > 0:
			self.mygrid["jdf-store-method"] = self.__getText(
				nodes[0].childNodes
			)
			if not self.mygrid["jdf-store-method"] in [ "store", "put" ]:
				raise "JDF Store Method not known."
		else:
			self.mygrid["jdf-store-method"] = ""

		nodes = dom.getElementsByTagName( "dcs:mygrid-jdf-tmp-path" )
		if len( nodes ) > 0:
			self.mygrid["jdf-tmp-path"] = self.__getText(
				nodes[0].childNodes
			)
		else:
			self.mygrid["jdf-tmp-path"] = ""

		## POV-Ray section

		nodes = dom.getElementsByTagName( "dcs:povray-cmd" )
		if len( nodes ) > 0:
			self.povray["cmd"] = self.__getText(
				nodes[0].childNodes
			)
		else:
			# Assume the 'povray' is in the remote bin path
			self.povray["cmd"] = "povray"

		nodes = dom.getElementsByTagName( "dcs:povray-libs" )
		if len( nodes ) > 0:
			self.povray["libs"] = [];
			for node in nodes:
				self.povray["libs"].append(
					self.__getText(node.childNodes)
				)
		else:
			self.povray["libs"] = ""

		self.povray["exec-steps"] = []
		self.povray["outfile"] = "" # the output of last exec step
		for esnode in dom.getElementsByTagName( "dcs:povray-exec-step" ):
			esdata = {}
			nodes = esnode.getElementsByTagName( "dcs:povray-exec-step-infile" )
			if len( nodes ) > 0:
				esdata["infile"] = os.path.basename(
					self.__getText(
						nodes[0].childNodes
					)
				)
			else:
				esdata["infile"] = ""
			nodes = esnode.getElementsByTagName( "dcs:povray-exec-step-outfile" )
			if len( nodes ) > 0:
				esdata["outfile"] = os.path.basename(
					self.__getText(
						nodes[0].childNodes
					)
				)
			else:
				esdata["outfile"] = ""
			self.povray["exec-steps"].append( esdata )
			self.povray["outfile"] = esdata["outfile"]

		## Scene section

		nodes = dom.getElementsByTagName( "dcs:scene" )
		if len( nodes ) > 0:
			self.scene["label"] = nodes[0].getAttribute( "label" )

			nodes = dom.getElementsByTagName( "dcs:scene-width" )
			if len( nodes ) > 0:
				self.scene["width"] = int(
					nodes[0].getAttribute("value")
				)
			else:
				self.scene["width"] = ""

			nodes = dom.getElementsByTagName( "dcs:scene-height" )
			if len( nodes ) > 0:
				self.scene["height"] = int(
					nodes[0].getAttribute("value")
				)
			else:
				self.scene["height"] = ""

			nodes = dom.getElementsByTagName( "dcs:scene-quality" )
			if len( nodes ) > 0:
				self.scene["quality"] = int(
					nodes[0].getAttribute("value")
				)
			else:
				self.scene["quality"] = ""

			nodes = dom.getElementsByTagName( "dcs:scene-bounding" )
			if len( nodes ) > 0:
				self.scene["bound-threshold"] = int(
					nodes[0].getAttribute("threshold")
				)
			else:
				self.scene["bound-threshold"] = ""

			nodes = dom.getElementsByTagName( "dcs:scene-antialias" )
			if len( nodes ) > 0:
				if nodes[0].hasAttribute("threshold"):
					self.scene["aa-threshold"] = int(
						nodes[0].getAttribute("threshold")
					)
				else:
					self.scene["aa-threshold"] = ""
				if nodes[0].hasAttribute("method"):
					self.scene["aa-method"] = int(
						nodes[0].getAttribute("method")
					)
				else:
					self.scene["aa-method"] = ""
				if nodes[0].hasAttribute("jitter"):
					self.scene["aa-jitter"] = float(
						nodes[0].getAttribute("jitter")
					)
				else:
					self.scene["aa-jitter"] = ""
				if nodes[0].hasAttribute("depth"):
					self.scene["aa-depth"] = int(
						nodes[0].getAttribute("depth")
					)
				else:
					self.scene["aa-depth"] = ""
			else:
				self.scene["aa-threshold"] = ""
				self.scene["aa-method"] = ""
				self.scene["aa-jitter"] = ""
				self.scene["aa-depth"] = ""

			nodes = dom.getElementsByTagName( "dcs:scene-alpha" )
			if len( nodes ) > 0:
				self.scene["out-alpha"] = True
			else:
				self.scene["out-alpha"] = False

			nodes = dom.getElementsByTagName( "dcs:scene-lightbuf" )
			if len( nodes ) > 0:
				self.scene["lightbuf"] = True
			else:
				self.scene["lightbuf"] = False

			nodes = dom.getElementsByTagName( "dcs:scene-vistabuf" )
			if len( nodes ) > 0:
				self.scene["vistabuf"] = True
			else:
				self.scene["vistabuf"] = False

			nodes = dom.getElementsByTagName( "dcs:scene-blocksize" )
			if len( nodes ) > 0:
				self.scene["blocksize"] = int(
					nodes[0].getAttribute("value")
				)
			else:
				self.scene["blocksize"] = ""

			nodes = dom.getElementsByTagName( "dcs:scene-imagefmt" )
			if len( nodes ) > 0:
				self.scene["imagefmt"] = nodes[0].getAttribute("type") + nodes[0].getAttribute("bits")
			else:
				self.scene["imagefmt"] = ""

			self.scene["files"] = []
			for f in dom.getElementsByTagName( "dcs:scene-file" ):
				self.scene["files"].append(
					os.path.abspath(
						self.__getText(f.childNodes)
					)
				)

		dom.unlink()
		dom = 0

		self.__applyDefaults()
		pass

	def __applyDefaults(self):
		""" Apply default values. """

		if not self.java["javac-cmd"]:
			self.java["javac-cmd"] = "javac"
		if not self.java["java-cmd"]:
			self.java["java-cmd"] = "java"
		if not self.java["cp"]:
			self.java["cp"] = "."

		if not self.mygridwrapper["class"]:
			self.mygridwrapper["class"] = "MyGridWrapper"

		if not self.mygrid["cmd"]:
			self.mygrid["cmd"] = "mygrid"

		if not self.scene["label"]:
			for ifn in self.scene["infiles"]:
				if re.match( ".*\.pov$",  ifn, re.IGNORECASE ) != None:
					lbl = os.path.basename( ifn ) # file name
					lbl = os.path.splitext( lbl )[0] # remove ext
					self.scene["label"] = lbl

		if not self.povray["outfile"]:
			self.povray["outfile"] = self.scene["label"] + "." + self.__imgFmtToExt(self.scene["imagefmt"])
		pass

	def javaCmd(self):
		""" Returns the Java "java" executable path. """

		return self.java["java-cmd"]

	def javacCmd(self):
		""" Returns the Java "javac" executable path. """

		return self.java["javac-cmd"]

	def javaClasspath(self):
		""" Returns the Java "classpath" settings. """

		return self.java["cp"]

	def mygridwrapperClass(self):
		""" Returns the MyGridWrapper class name. """

		return self.mygridwrapper["class"]

	def mygridCmd(self):
		""" Returns the MyGrid executable path. """

		return self.mygrid["cmd"]

	def mygridJdfStorePath(self):
		""" Returns the store path used in the JDF file (same meaning of OurGrid $STORAGE variable). """

		return self.mygrid["jdf-store-path"]

	def mygridJdfStoreMethod(self):
		""" Returns the store method used in the JDF file. """

		return self.mygrid["jdf-store-method"]

	def mygridJdfTempPath(self):
		""" Returns the temporary path used in the JDF file (same meaning of OurGrid $PLAYPEN variable). """

		return self.mygrid["jdf-tmp-path"]

	def povrayCmd(self):
		""" Returns the POV-Ray executable path. """

		return self.povray["cmd"]

	def povrayLibs(self):
		""" Returns the POV-Ray library path prefix. """

		return self.povray["libs"]

	def povrayOutputFile(self):
		""" Returns the POV-Ray final output file. """

		return self.povray["outfile"]

	def povrayExecSteps(self):
		""" Returns the list of POV-Ray steps to be executed. """

		return self.povray["exec-steps"]

	def povrayExecStepInputFile(self, execStep):
		""" Returns the input file of given POV-Ray step. """

		return execStep["infile"]

	def povrayExecStepOutputFile(self, execStep):
		""" Returns the output file of given POV-Ray step. """

		return execStep["outfile"]

	def sceneLabel(self):
		""" Returns the scene label. """

		return self.scene["label"]

	def sceneWidth(self):
		""" Returns the scene image width. """

		return self.scene["width"]

	def sceneHeight(self):
		""" Returns the scene image height. """

		return self.scene["height"]

	def sceneBoundingThreshold(self):
		""" Returns the scene bounding threshold value. """

		return self.scene["bound-threshold"]

	def sceneQuality(self):
		""" Returns the scene quality value. """

		return self.scene["quality"]

	def sceneAntialiasThreshold(self):
		""" Returns the scene antialias threshold. """

		return self.scene["aa-threshold"]

	def sceneSamplingMethod(self):
		""" Returns the scene antialias sampling method. """

		return self.scene["aa-method"]

	def sceneJitterAmount(self):
		""" Returns the scene antialias jitter amount. """

		return self.scene["aa-jitter"]

	def sceneAntialiasDepth(self):
		""" Returns the scene antialias depth. """

		return self.scene["aa-depth"]

	def sceneOutputAlpha(self):
		""" Returns a boolean value telling if alpha channel should be used for the scene. """

		return self.scene["out-alpha"]

	def sceneLightBuffer(self):
		""" Returns a boolean value telling if light buffer should be used for the scene. """

		return self.scene["lightbuf"]

	def sceneVistaBuffer(self):
		""" Returns a boolean value telling if vista buffer should be used for the scene. """

		return self.scene["vistabuf"]

	def sceneBlockSize(self):
		""" Returns the scene block size, i.e. the size of scene tiles. """

		return self.scene["blocksize"]

	def sceneImageFormat(self):
		""" Returns the scene output image format. """

		return self.scene["imagefmt"]

	def sceneFiles(self):
		""" Returns a list of scene files. """

		return self.scene["files"]

	def __getText(self,nodelist):
		""" Extracts text from a DOM Node object. """

		rc = ""
		for node in nodelist:
			if node.nodeType == node.TEXT_NODE:
				rc = rc + node.data
		return rc

	def __imgFmgToExt(self,imgfmt):
		""" Composes the image format string. """

		if imgfmt[0] == "N":
			return "png"

		raise "Uknown image format: '" + imgfmt + "'"
