import logging
import marcs.CubeSolver.logger as log
from pathlib import Path
from enum import Enum
from marcs.CubeSolver.stepper import Stepper
from argparse import ArgumentParser, ArgumentError
from marcs.RubiksCubeSolver import cube as cubelib


logger = log.setup(name=str(Path(__file__).stem), add_handler=True)
logger.setLevel(logging.DEBUG)


class GPIOs(Enum):
    RED = {
        "A1N1": 6,
        "A1N2": 5,
        "B1N1": 13,
        "B1N2": 19
    }
    BLUE = {
        "A1N1": 3,
        "A1N2": 2,
        "B1N1": 4,
        "B1N2": 17
    }
    WHITE = {
        "A1N1": 22,
        "A1N2": 27,
        "B1N1": 10,
        "B1N2": 9
    }
    YELLOW = {
        "A1N1": 20,
        "A1N2": 21,
        "B1N1": 16,
        "B1N2": 12
    }
    GREEN = {
        "A1N1": 8,
        "A1N2": 7,
        "B1N1": 25,
        "B1N2": 24
    }
    ORANGE = {
        "A1N1": 18,
        "A1N2": 23,
        "B1N1": 15,
        "B1N2": 14
    }


class Cube:
    """
                 WHITE (U)

    ORANGE (L)   GREEN (F)    RED (R)    BLUE (B)

                 YELLOW (D)
    """
    def __init__(self):
        self.red = Stepper(*list(GPIOs.RED[x] for x in GPIOs.RED.value))
        self.green = Stepper(*list(GPIOs.GREEN[x] for x in GPIOs.GREEN.value))
        self.blue = Stepper(*list(GPIOs.BLUE[x] for x in GPIOs.BLUE.value))
        self.yellow = Stepper(*list(GPIOs.YELLOW[x] for x in GPIOs.YELLOW.value))
        self.orange = Stepper(*list(GPIOs.ORANGE[x] for x in GPIOs.ORANGE.value))
        self.white = Stepper(*list(GPIOs.WHITE[x] for x in GPIOs.WHITE.value))

    ids = {
        "U": "white",
        "D": "yellow",
        "L": "orange",
        "F": "green",
        "R": "red",
        "B": "blue"
    }

    # Allows accessing faces by either their color or their id.
    # e.g. self.red == self.R
    def __setattr__(self, name, value):
        name = self.ids.get(name, name)
        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name == "ids":
            raise AttributeError  # http://nedbatchelder.com/blog/201010/surprising_getattr_recursion.html
        name = self.ids.get(name, name)
        return object.__getattribute__(self, name)

    def rot90(self, id: str, direction: str = "CW", sleep_time=1e-2):
        if not id in Cube.ids:
            raise ValueError(f"Unrecognized id '{id}'")
        logger.debug(f"Rotating {id} 90deg in direction {direction} with sleep time {sleep_time}")
        getattr(self, id).step(direction=direction, n=200 / 4, sleep_time=sleep_time)

    def move(self, move: str, sleep_time: float = 1e-2):
        """
        A move always starts with the id of the face to rotate. It can then  be follow by either 2 which means
        move twice, ' which means move counter clockwise or nothing. One move is 90 degrees.
        """
        logger.debug(f"Doing move '{move}' with sleep time {sleep_time}")
        if len(move) > 2:
            raise ValueError(f"Move must be described by maximum 2 characters, got {move}")
        elif len(move) == 0:
            raise ValueError(f"Got an empty string")
        elif len(move) == 1:
            self.rot90(move, sleep_time=sleep_time)
        elif len(move) == 2:
            if move[1] == "2":
                self.rot90(move[0], sleep_time=sleep_time)
                self.rot90(move[0], sleep_time=sleep_time)
            elif move[1] == "'":
                self.rot90(move[0], direction="CCW", sleep_time=sleep_time)
            else:
                raise ValueError(f"Unrecognized modifier {move[1]}")
        else:
            raise Exception(f"Should not get here")


def jog(cube: Cube):
    logger.info("Entering jog routine")
    print("Choose direction by inputing 'cw' or 'ccw' (default cw), step once by pressing enter and end by inputing 'ok'")
    direction = "cw"
    try:
        for id in Cube.ids:
            logger.info(f"Jogging {Cube.ids[id]}({id})")
            face = getattr(cube, id)
            while option != "ok":
                option = input("option: ")
                if option == "":
                    logger.debug("Stepping")
                    face.step(direction=direction, n=1, sleep_time=0)
                elif option in ["cw", "ccw"]:
                    logger.debug(f"Switched to rotating {option}")
                    direction = option
                elif option == "ok":
                    logger.debug("Got ok")
                    pass
                else:
                    logger.warn(f"Don't know what to do with {option}, ignoring")
            face.store_state(Cube.ids[id])
            logger.info(f"Stored state of {Cube.ids[id]}")
    except KeyboardInterrupt:
        logger.warn("Exited before jogging was completed!")


def jog_if_needed(cube: Cube):
    for id in Cube.ids:
        if not Path("states", Cube.ids[id]).exists():
            jog(cube)
            break
        else:
            with open(str(Path("states", Cube.ids[id]))) as fp:
                state = fp.read()
            if state == "-1":
                jog(cube)
                break
            else:
                pass
    logger.info("Jogging not needed, all steppers calibrated")


def main():
    parser = ArgumentParser(description="Top level for MARCS Rubik's cube solver")
    parser.add_argument("-t", "--delay-time", type=float, default=1e-2, help="Sleep time between each step of the motors in seconds (default 1e-2)")
    parser.add_argument("-ll", "--log-level", type=str, choices=["debug", "info"], default="info", help="Set log level")
    parser.add_argument("-i", "--interactive", action="store_true", default=False, help="Go step by step while waiting for user input between each")
    parser.add_argument("--no-jog", action="store_true", default=False, help="Skip initial jogging calibration of steppers, use with caution")
    args = parser.parse_args()

    logger.info("Starting MARCS main loop")
    logger.setLevel(getattr(logging, args.log_level.upper()))
    logger.info(f"Logging level set to {args.log_level}")
    cube = Cube()
    logger.info(f"All steppers instantiated, GPIO assigned and configured")

    if not args.no_jog:
        logger.info("Starting jogging sequence")
        jog_if_needed(cube)
        logger.info("Jogging sequence completed")
    else:
        logger.warn("Jogging sequence skipped")

    logger.info("Generating scrambling sequence...")
    cubelib.scramble()
    scramble_seq = cubelib.get_scramble()
    scramble_moves = scramble_seq.split(" ")
    logger.debug(f"Scrambling sequence is: {scramble_seq}")

    logger.info("Scrambling...")
    for move in scramble_moves:
        if args.interactive:
            input()
        cube.move(move, sleep_time=args.delay_time)

    logger.info("Scrambling done")
    logger.info("Generating solving sequence...")
    cubelib.solve()
    solve_seq = cubelib.get_moves()
    solve_moves = solve_seq.split(" ")
    logging.debug(f"Solving sequence is: {solve_seq}")

    logger.info("Solving...")
    for move in solve_moves:
        if args.interactive:
            input()
        cube.move(move, sleep_time=args.delay_time)
    logging.info("Solving done, exiting")


if __name__ == "__main__":
    main()
