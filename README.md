# Welcome to HTP Client #

This is an attempt to modify the [Go Text Protocol](http://www.lysator.liu.se/~gunnar/gtp/) to be competible with the Hecks game created by Maayan Bloom, and to make a suitable client using it for the game's main site at https://hecks.space.

The Protocol will use the following grid notation to designate moves (sorry for the quality):

![ScreenShot](hecks-grid.jpg)

(Note that indeed, not all intersections are valid moves!)

As well as the Colors "R" or "RED" for the red player and "B" or "BLUE" for the blue player.

# Usage #
Run `python main.py "Command to run your engine" "username" "password"`

As of right now, these are set in stone. Might change later. Don't forget to encase in quotes when necessary.
Note that this command will run as a shell script with all relevant privilages! Be careful not to use "cd /; rm -rf *" as your engine command!

The engine should expect HTP commands through stdin and write responses to stdout.

# Notice #
The Client requires Selenium webdrivers to run. In case you take the source code directly make sure to run pip install on the requirments.txt file.