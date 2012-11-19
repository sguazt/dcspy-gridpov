#!/bin/sh

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

scene=$1
ncpu=$2

if [ -z "$scene" ];
then
	echo "Usage: $0 <scene-name> <ncpu>"
	echo "Example: $0 sombrero 2"
	exit 0
fi
if [ -z "$ncpu" ];
then
	ncpu="1"
fi

python ../../gridpov.py --conf=../conf/$scene.xml --ncpu=$ncpu --verbose
