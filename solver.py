import logging
import marcs.CubeSolver.logger as log
from pathlib import Path
from enum import Enum
from marcs.CubeSolver.stepper import Stepper
from argparse import ArgumentParser, ArgumentError
from marcs.RubiksCubeSolver import cube


logger = log.setup(name=str(Path(__file__).stem))
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

    def rot90(self, id: str, direction: str = "CW", sleep_time = 1e-2):
        if not id in Cube.ids:
            raise ValueError(f"Unrecognized id '{id}'")
        getattr(self, id).step(direction=direction, n = 200 / 4, sleep_time=sleep_time)

    def move(self, move: str):
        """
        A move always starts with the id of the face to rotate. It can then  be follow by either 2 which means
        move twice, ' which means move counter clockwise or nothing. One move is 90 degrees.
        """
        if len(move) > 2:
            raise ValueError(f"Move must be described by maximum 2 characters, got {move}")
        elif len(move) == 0:
            raise ValueError(f"Got an empty string")
        elif len(move) == 1:
            self.rot90(move)
        elif len(move) == 2:
            if move[1] == "2":
                self.rot90(move[0])
                self.rot90(move[0])
            elif move[1] == "'":
                self.rot90(move[0], direction="CCW")
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
                    face.step(direction=direction, n=1, sleep_time=0)
                elif option in ["cw", "ccw"]:
                    direction = option
                elif option == "ok":
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

