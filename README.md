dcspy-gridpov
=============

This project is focused on performing distributed rendering by means of [POV-Ray](http://www.povray.org "The Persistence of Vision Raytracer") over a grid computing platform.

Distributed rendering is done by splitting the rendering job in several rendering task, each of which is assigned to a (remote) machine via a grid scheduler.
The current implementation only supports the [OurGrid](http://www.ourgrid.org "OurGrid Middleware") MyGrid scheduler.

This project is based on [MegaPOV XRS](http://www.gammaburst.com/xrs) (broken link), by George Pantazopoulos.
George is unfortunately passed away and the link above no longer works. The Web Archive has a copy of the site [here] (http://web.archive.org/web/20070505055558/http://www.gammaburst.net/xrs/).

If you're looking for similar projects, then you should take a look at [HTTPov](http://columbiegg.com/httpov/).
