import atexit
import logging as l
import sys
import numpy as np
from argparse import ArgumentParser
from enum import Enum
from pathlib import Path
from time import sleep, time

import RPi.GPIO as GPIO
from marcs.CubeSolver.logger import log, set_log_level
from marcs.CubeSolver.stepper import Stepper
from marcs.RubiksCubeSolver import cube as cubelib
from marcs.TwoPhaseSolver.solver import solve

GPIO.setmode(GPIO.BCM)


class GPIOs(Enum):
    GREEN = {
        "A1N1": 6,
        "A1N2": 5,
        "B1N1": 13,
        "B1N2": 19
    }
    YELLOW = {
        "A1N1": 3,
        "A1N2": 2,
        "B1N1": 4,
        "B1N2": 17
    }
    ORANGE = {
        "A1N1": 22,
        "A1N2": 27,
        "B1N1": 10,
        "B1N2": 9
    }
    WHITE = {
        "A1N1": 20,
        "A1N2": 21,
        "B1N1": 16,
        "B1N2": 12
    }
    RED = {
        "A1N1": 8,
        "A1N2": 7,
        "B1N1": 25,
        "B1N2": 24
    }
    BLUE = {
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
        self.red = Stepper(*list(GPIOs.RED.value[x] for x in GPIOs.RED.value))
        self.green = Stepper(*list(GPIOs.GREEN.value[x] for x in GPIOs.GREEN.value))
        self.blue = Stepper(*list(GPIOs.BLUE.value[x] for x in GPIOs.BLUE.value))
        self.yellow = Stepper(*list(GPIOs.YELLOW.value[x] for x in GPIOs.YELLOW.value))
        self.orange = Stepper(*list(GPIOs.ORANGE.value[x] for x in GPIOs.ORANGE.value))
        self.white = Stepper(*list(GPIOs.WHITE.value[x] for x in GPIOs.WHITE.value))

    ids = {
        "D": "white",
        "U": "yellow",
        "B": "orange",
        "R": "green",
        "F": "red",
        "L": "blue"
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

    @staticmethod
    def _opposite_direction(direction: str):
        if direction is "CW":
            return "CCW"
        elif direction is "CCW":
            return "CW"
        elif direction is "cw":
            return "ccw"
        elif direction is "ccw":
            return "cw"
        else:
            raise ValueError(f"{direction} is not a valid direction")

    def rot90(self, id: str, sleep_time: float, half_step: bool, direction: str = "CW"):
        if not id in Cube.ids:
            raise ValueError(f"Unrecognized id '{id}'")
        log(l.DEBUG, f"Rotating {id} 90deg in direction {direction} with sleep time {sleep_time} half step is {half_step}")
        stepper = getattr(self, id)
        stepper.arm()
        if half_step:
            rot_n = 101
            comp_n = 1
        else:
            rot_n = 53
            comp_n = 3
        stepper.step(direction=direction, n=rot_n, sleep_time=sleep_time, half_step=half_step)
        # To compensate the shaft tolerance issues
        stepper.step(direction=self._opposite_direction(direction), n=comp_n, sleep_time=sleep_time,
                     half_step=half_step)
        stepper.disarm()

    def rot180(self, id: str, sleep_time: float, half_step: bool, direction: str = "CW"):
        if not id in Cube.ids:
            raise ValueError(f"Unrecognized id '{id}'")
        log(l.DEBUG, f"Rotating {id} 180deg in direction {direction} with sleep time {sleep_time} half step is {half_step}")
        stepper = getattr(self, id)
        stepper.arm()
        if half_step:
            rot_n = 202
            comp_n = 2
        else:
            rot_n = 103
            comp_n = 2
        stepper.step(direction=direction, n=rot_n, sleep_time=sleep_time, half_step=half_step)
        # To compensate the shaft tolerance issues
        stepper.step(direction=self._opposite_direction(direction), n=comp_n, sleep_time=sleep_time,
                     half_step=half_step)
        stepper.disarm()

    def move(self, move: str, sleep_time: float, half_step: bool):
        """
        A move always starts with the id of the face to rotate. It can then  be follow by either 2 which means
        move twice, ' which means move counter clockwise or nothing. One move is 90 degrees.
        """
        log(l.DEBUG, f"Doing move '{move}' with sleep time {sleep_time} half step is {half_step}")
        if len(move) > 2:
            raise ValueError(f"Move must be described by maximum 2 characters, got {move}")
        elif len(move) == 0:
            raise ValueError(f"Got an empty string")
        elif len(move) == 1:
            self.rot90(move, sleep_time=sleep_time, half_step=half_step)
        elif len(move) == 2:
            if move[1] == "2":
                self.rot180(move[0], sleep_time=sleep_time, half_step=half_step)
            elif move[1] == "1":
                self.rot90(move[0], sleep_time=sleep_time, half_step=half_step)
            elif move[1] == "'" or move[1] == "3":
                self.rot90(move[0], direction="CCW", sleep_time=sleep_time, half_step=half_step)
            else:
                raise ValueError(f"Unrecognized modifier {move[1]}")
        else:
            raise Exception(f"Should not get here")


def jog(cube: Cube, half_step: bool):
    log(l.INFO, "Entering jog routine")
    print(
        "Choose direction by inputing 'cw', 'ccw' or 'r' to reverse direction (default cw), step once by pressing enter and end by inputing 'ok'")
    direction = "cw"
    try:
        for id in Cube.ids:
            log(l.INFO, f"Jogging {Cube.ids[id]}({id})")
            face = getattr(cube, id)
            option = input("option: ")
            while option != "ok":
                option = input("option: ")
                if option == "":
                    face.step(direction=direction.upper(), n=1, sleep_time=0, half_step=half_step)
                elif option in ["cw", "ccw"]:
                    log(l.DEBUG, f"Switched to rotating {option}")
                    direction = option
                elif option == "ok":
                    if half_step:
                        n = 1
                    else:
                        n = 3
                    log(l.DEBUG, f"Got ok, reversing {n} steps for tolerance compensation")
                    face.step(direction=(cube._opposite_direction(direction)).upper(), n=n, sleep_time=1e-2,
                              half_step=half_step)
                    pass
                elif option == "r":
                    if direction == "cw":
                        direction = "ccw"
                    else:
                        direction = "cw"
                    log(l.DEBUG, f"Reversing direction, now rotating {direction}")
                else:
                    log(l.WARNING, f"Don't know what to do with {option}, ignoring")
            face.store_state(Cube.ids[id])
            face.disarm()
            log(l.INFO, f"Stored state of {Cube.ids[id]}")
    except KeyboardInterrupt:
        log(l.WARNING, "Exited before jogging was completed!")
        raise KeyboardInterrupt


def jog_if_needed(cube: Cube, force=False, half_step: bool = False):
    jogged = False
    for id in Cube.ids:
        if force:
            jog(cube, half_step=half_step)
            jogged = True
            break
        elif not Path("states", Cube.ids[id]).exists():
            jog(cube, half_step=half_step)
            jogged = True
            break
        else:
            with open(str(Path("states", Cube.ids[id]))) as fp:
                state = fp.read()
            if state == "-1":
                jog(cube, half_step=half_step)
                jogged = True
                break
    if not jogged:
        log(l.INFO, "Jogging not needed, all steppers calibrated")
    else:
        log(l.INFO, "Jogging sequence completed")


def cleanup(cube):
    log(l.INFO, "Cleaning up and exiting")
    for id in Cube.ids:
        face = getattr(cube, id)
        face.arm()
        face.store_state(Cube.ids[id])
        face.state = 8  # De energize windings to preserve steppers
    GPIO.cleanup()


def main():
    parser = ArgumentParser(description="Top level for MARCS Rubik's cube solver")
    parser.add_argument("-t", "--delay-time", type=float, default=5e-3,
                        help="Sleep time between each step of the motors in seconds (default 1e-3)")
    parser.add_argument("-mdt", "--move-delay-time", type=float, default=5e-2,
                        help="Sleep time between each move (default 5e-2")
    parser.add_argument("-ll", "--log-level", type=str, choices=["debug", "info", "warning"], default="info",
                        help="Set log level")
    parser.add_argument("--test", default=False, action="store_true",
                        help="Test sequence, jog then do 90 deg rotations")
    parser.add_argument("-i", "--interactive", action="store_true", default=False,
                        help="Go step by step while waiting for user input between each")
    parser.add_argument("--no-jog", action="store_true", default=False,
                        help="Skip initial jogging calibration of steppers, use with caution")
    parser.add_argument("-j", "--jog", action="store_true", default=False, help="Redo jogging sequence")
    parser.add_argument("--full-step", dest="half_step", action="store_false", default=True,
                        help="Use full steps when moving (not recommended)")
    parser.add_argument("--max-speed", action="store_true", default=False, help="Use fastest settings")
    parser.add_argument("-c", "--cubestr", type=str, default="", help="Cube string to use for solving")
    args = parser.parse_args()

    log(l.INFO, "Starting MARCS main loop")
    log(l.DEBUG, f"Passed arguments: {sys.argv}")
    set_log_level(getattr(l, args.log_level.upper()))
    log(l.INFO, f"Logging level set to {args.log_level}")
    if args.log_level == "debug":
        log(l.WARNING, "WARNING: debug log level WILL slow down the solving")
    if args.max_speed:
        args.delay_time = 1e-3
        args.move_delay_time = 6e-2
        log(l.DEBUG, "Using max speed, get that CTRL+C ready")
    cube = Cube()
    atexit.register(cleanup, cube)
    log(l.INFO, f"All steppers instantiated, GPIO assigned and configured")
    try:
        if args.test:
            log(l.DEBUG, "Entering test sequence")
            jog(cube, half_step=args.half_step)
            while True:
                input()
                cube.move("U", sleep_time=args.delay_time, half_step=args.half_step)

        if not args.no_jog:
            log(l.INFO, "Starting jogging sequence")
            jog_if_needed(cube, force=args.jog, half_step=args.half_step)
        else:
            log(l.WARNING, "Jogging sequence skipped")

        if not args.cubestr:
            log(l.INFO, "Generating scrambling sequence...")
            cubelib.scramble()
            scramble_seq = cubelib.get_scramble()
            scramble_moves = scramble_seq.split(" ")
            log(l.DEBUG, f"Scrambling sequence is: {scramble_seq}")

            log(l.INFO, "Scrambling...")
            for move in scramble_moves:
                log(l.DEBUG, move)
                if args.interactive:
                    input()
                cube.move(move, sleep_time=args.delay_time, half_step=args.half_step)
                sleep(args.move_delay_time)

            log(l.INFO, "Scrambling done")
            conversion_dict = {
                "W": "D", "G": "R", "R": "F", "O": "B", "Y": "U", "B": "L"
            }
            cubestr = ""
            c = cubelib.a
            c[2] = np.rot90(c[2], 3)
            c[3] = np.rot90(c[3])
            c[5] = np.rot90(c[5], 2)
            for face in [0, 2, 1, 4, 3, 5]:
                for row in range(3):
                    for col in range(3):
                        cubestr += conversion_dict[c[face][row][col]]
        else:
            cubestr = args.cubestr

        log(l.INFO, "Generating solving sequence...")
        moves = solve(cubestr)
        solve_moves = moves.split(" ")[0:-1]
        log(l.INFO, f"Solving sequence is: {moves}")

        input("When ready to solve, press enter")
        start_time = time()
        log(l.INFO, "Solving...")
        for move in solve_moves:
            log(l.DEBUG, move)
            if args.interactive:
                input()
            cube.move(move, sleep_time=args.delay_time, half_step=args.half_step)
            sleep(args.move_delay_time)
        end_time = time()
        solve_time = end_time - start_time
        log(l.INFO, f"Solving done in {round(solve_time, 3)}s with {len(solve_moves)} moves, exiting")
    except KeyboardInterrupt:
        log(l.DEBUG, "Keyboard interrupt, exiting")
        exit(0)


if __name__ == "__main__":
    main()
