#!/bin/bash

##
## Copyright (C) 2012  Distributed Computing System (DCS) Group, Computer
## Science Department - University of Piemonte Orientale, Alessandria (Italy).
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
## Author: Marco Guazzone, marco.guazzone@mfn.unipmn.it
##

basepath=$HOME/projects/dcspy-gridpov


#### Configuration for LOCAL execution

loc_povray=/usr/local/bin/povray
loc_libs=/usr/local/share/povray/include
loc_scene=${basepath}/test/scenes/1AG9.pov
loc_outimg=${basepath}/test/out/loc_molecule_64.png
loc_width=800 # image width
loc_height=600 # image height
loc_aliasts=3 # antialias threshold
loc_title="<LOCAL> Render Preview: molecule 64" # render window title
#loc_statfile=${basepath}/test/locstat.out


#### Configuration for REMOTE execution

rem_python=python
rem_gridpov=${basepath}/gridpov.py
rem_scene=${basepath}/test/conf/molecule_64.xml
rem_ncpu=1
rem_title="<REMOTE> Render Preview: molecule 64" # render window title
#rem_statfile=${basepath}/test/remstat.out
rem_mgroot=/usr/local/opt/OurGrid/mygrid


#### Checks

## Check for MyGrid
if [ "$MGROOT" == "" ]; then
	export MGROOT=$rem_mgroot
fi
mg_out=`$rem_mgroot/bin/mygrid status 2>&1 >/dev/null`
if [ $? != 0 ]; then
	echo "Error: MyGrid Not Running!"
	exit 1
fi


#### Commands

## Local command
xterm -T "$loc_title" -e \
"$loc_povray \
	+D \
	+W${loc_width} \
	+H${loc_height} \
	+A0.${loc_aliasts} \
	+L${loc_libs} \
	+FN8 \
	+I${loc_scene} \
	+O${loc_outimg} \
	-title '$loc_title'; read -p 'Press any key to continue ...'" &
#	+GS${loc_statfile}
#	>/dev/null 2>&1 &
#loc_pid=$!

## Remote command
xterm -T "$rem_title" -e \
$rem_python $rem_gridpov \
	--conf $rem_scene \
	--ncpu $rem_ncpu \
	--title "$rem_title" &
#	> $rem_statfile 2>&1 &
#rem_pid=$!

#wait $loc_pid $rem_pid

#echo "=== LOCAL execution ============================================================"
#cat $loc_statfile
#echo "================================================================================"

#echo ""

#echo "=== REMOTE execution ==========================================================="
#cat $rem_statfile
#echo "================================================================================"

#rm $loc_file $rem_file
