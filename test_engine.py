"""
This "engine" decides on the next move, when prompted with the "genmove" command,
by reading it from a file (given as first CLI arguments) and is used for testing purposes.

For any other command the "engine" will respond with success (=\n)
"""
import sys
import logging
logging.basicConfig(filename='logs/main.log', level=logging.DEBUG, format='%(asctime)s : %(name)s : %(levelname)s : %(message)s')
logging = logging.getLogger("engine")


if __name__ == "__main__":
    a = sys.argv[1]

    with open(a, "rt") as f:
        logging.debug("Reading from file: {}".format(a))
        has_data = True

        while has_data:
            in_data = input()
            logging.debug("got: " + in_data)

            if "genmove" in in_data:
                out = f.readline()
                logging.debug("Sending: {}".format(out))
                if not out:
                    print("? out of data\n")
                    has_data = False
                print(out.strip())
            else:
                print("=\n")

        sys.stdout.flush()
