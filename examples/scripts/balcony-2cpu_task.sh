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
## Author: Marco Guazzone, marco.guazzone@gmail.com
##

/usr/local/bin/povray -D +FN8 +W800 +H600 +A0.3  +SR1 +ER67 +SC1 +EC67 +I$STORAGE/balcony.pov +O$PLAYPEN/balcony-14449-tile-1.png & 
pid0=$!
/usr/local/bin/povray -D +FN8 +W800 +H600 +A0.3  +SR1 +ER67 +SC68 +EC134 +I$STORAGE/balcony.pov +O$PLAYPEN/balcony-14449-tile-2.png & 
pid1=$!
wait $pid0 $pid1
exit $?
