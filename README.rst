Welcome to HTP Client
=====================

This is an attempt to modify the `Go Text Protocol`_ to be competible
with the Hecks game created by Maayan Bloom, and to make a suitable
client using it for the game’s main site at https://hecks.space.

Installation
============

Option 1
~~~~~~~~

-  Make sure you have python 3.4.2 or greated installed (not tested with
   other versions).
-  Download the source code from github and navigate a command line to
   it’s folder.
-  Run ``pip install -r requirments.txt`` (hopefully in a virtual
   environment)

Option 2
~~~~~~~~

-  Make sure you have python 3.4.2 or greated installed (not tested with
   other versions).
-  Run ``pip install htp-client``
-  Use your new cli command ``htpplay``. The signature is the same as in
   the usage section below.

Troubleshooting
---------------

For any issues with Selenium, use google, since it’s black magic for me.
For any other issues feel free to send me a message.

The protocol
============

The Protocol will use the following notation for the vertices of the board:
The rows created by taking all points in the lower half of each hexagon in the lower half of the board and upper half of
each hexagon in the upper half of the board (Giving zizagged lines) will be denoted by letters from 'a' to 'j' from
bottom to top.
The leftmost vertex of each row will be denoted with 1, with numbers increasing sequentially along the row to the right.

When writing the moves,letters precede numbers. I.E. “a3” is a valid move while “3a” is
not.

A few things to note here are:

-  The notation is case insensitive. "B5" and "b5" are the same vertex.
-  Not all rows have the same number of vertices. "e19" is a valid move, but "a19" is not.
-  We abolish the Go convention of skipping I in the notation, I comes
   before J as it should.
-  Same as the GTP, “pass” will denote passing one’s turn and “resign” a
   game resignation. These are also considered vertices for all purposes

The colors will be annotated as “R” or “RED” for the red player and “B”
or “BLUE” for the blue player.

A move is a color, followed by a vertex. They should be separated by a space

Currently supported commands (emitted by the controller) are:

-  genmove [color]

   -  Ask the engine to generate a move by itself and play it
      internally.
   -  Argument: color to generate move for.
   -  Success response: = [Vertex]
   -  Fail reasons: Game not initialized in engine. Not current player
      turn (this is optional as the enging is not required to keep track
      of turns).

-  play [Move]

   -  Ask the engine to play a move internally.
   -  Argument: Move to play.
   -  Fail reasons: Illegal move.

- clearboard
  
  - Ask the engine to clear the board and prepare for a new game
  - Fail reasons: None.

- quit

  - Tells the engine to quit.

Usage
=====

If you are running directly from source, from the main directory run:

``python htpplay.py "Command to run your engine" "username" "password"``

If you installed using pip, run:

``htpplay "Command to run your engine" "username" "password"``

| As of right now, these are set in stone. Might change later. Don’t
  forget to encase in quotes when necessary.
| Note that this command will run as a shell script with all relevant
  privilages! Be careful not to use “cd /; rm -rf \*" as your engine
  command!

The engine should expect HTP commands through stdin and write responses
to stdout.

For now a new folder called “logs” will be created, which will include
all logs, in the future support for custom log levels will be added.

Notice
======

The Client requires Selenium webdrivers to run. In case you take the
source code directly make sure to run pip install on the requirments.txt
file.

Required features before release 1.0.0
======================================

+ Multiple games per session, with default to infinite - Decided by CLI options or settings file.
+ Infinite game search, the site seems to stop the search after not finding a match for a while. (Bug on developer's site)
+ Close the program gracefully by sending quit to the engine. (Added in version 0.4.3)
+ Support for changing of time controls - Decided by CLI options or settings file.
+ Suport for resuming mid games - Maybe sending the kifu at the start of a new game somehow. At the engine side this is just sending "play move color" for all already played moves. This is also required for engine analysis.
+ Commands: clear_board, time_settings, time_left (clear_board added in version 0.4.3)

Possible features for the future
================================

+ Support for reg_genmove command and emission for game analysis.
+ CLI options to make calls to the showboard command.
+ Support for named pipes and sockets.

.. _Go Text Protocol: http://www.lysator.liu.se/~gunnar/gtp/

.. |ScreenShot| image:: http://i.imgur.com/JHoGBal.jpg