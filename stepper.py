import RPi.GPIO as GPIO
import argparse
import ast
import logging as l
from marcs.CubeSolver.logger import log, set_log_level
from pathlib import Path
from time import sleep


class Winding:
    def __init__(self, pin1: int, pin2: int):
        self.pin1 = pin1
        self.pin2 = pin2
        self.energized = 0
        for pin in [pin1, pin2]:
            GPIO.setup(pin, GPIO.OUT)
        log(l.DEBUG, f"winding instantiated with pins [{pin1}, {pin2}]")

    def energize(self, direction: int = 1):
        if direction == 1:
            GPIO.output(self.pin1, GPIO.HIGH)
            GPIO.output(self.pin2, GPIO.LOW)
            self.energized = 1

        elif direction == -1:
            GPIO.output(self.pin1, GPIO.LOW)
            GPIO.output(self.pin2, GPIO.HIGH)
            self.energized = -1

        elif direction == 0:
            self.de_energize()

        else:
            raise ValueError(f"direction is either 1 or -1, got {direction}")

    def de_energize(self):
        GPIO.output(self.pin1, GPIO.LOW)
        GPIO.output(self.pin2, GPIO.LOW)
        self.energized = 0


class Stepper:
    def __init__(self, pinA1: int, pinA2: int, pinB1: int, pinB2: int):
        self.windingA = Winding(pinA1, pinA2)
        self.windingB = Winding(pinB1, pinB2)
        self.cached_state = -1
        self.state_dict = {
            "[1, 0]":   0,
            "[1, 1]":   1,
            "[0, 1]":   2,
            "[-1, 1]":  3,
            "[-1, 0]":  4,
            "[-1, -1]": 5,
            "[0, -1]":  6,
            "[1, -1]":  7,
            "[0, 0]":   8,  # Both windings off this won't happen at runtime
        }
        self.inverted_state_dict = {v: ast.literal_eval(k) for k, v in self.state_dict.items()}

    @property
    def state(self):
        return self.state_dict[str([self.windingA.energized, self.windingB.energized])]

    @state.setter
    def state(self, state):
        states = self.inverted_state_dict[state]
        self.windingA.energize(states[0])
        self.windingB.energize(states[1])

    def disarm(self):
        self.cached_state = self.state
        self.windingA.de_energize()
        self.windingB.de_energize()

    def arm(self):
        if not self.cached_state == -1:
            self.state = self.cached_state
        else:
            log(l.DEBUG, "Can't arm before disarm, ignoring")

    def get_next_state(self, half_step: bool = False, direction: str = "CW"):
        if not direction == "CW" and not direction == "CCW":
            raise ValueError(f"direction is either 'CW' or 'CCW', got '{direction}'")

        if not half_step:
            full_step_states = [0, 2, 4, 6]
            if direction == "CCW":
                return full_step_states[(int(self.state / 2) + 1) % 4]  # Uhhh yeah sorry about this code
            elif direction == "CW":
                return full_step_states[(int(self.state / 2) - 1) % 4]  # Only way I could think of to accommodate wraparound
        elif half_step:
            if direction == "CCW":
                return (self.state + 1) % 8  # move one state since half step
            elif direction == "CW":
                return (self.state + 15) % 8

    @staticmethod
    def create_state_file_if_needed(filename: str):
        if not Path("states").is_dir():
            Path("states").mkdir(parents=False)
        if not Path("states", filename).exists():
            with open(Path("states", filename), "w") as fp:
                fp.write("-1")

    def store_state(self, filename: str):
        self.create_state_file_if_needed(filename)
        with open(str(Path("states", filename)), "w") as fp:
            fp.write(f"{self.state}")

    def load_state(self, filename: str):
        if not Path("states", filename).exists():
            raise FileNotFoundError(f"No state file created for {filename}")

        with open(str(Path("states", filename)), "r") as fp:
            state = fp.read()

        try:
            state = int(state)
        except ValueError:
            raise ValueError(f"read state '{state}' is not an integer")

        if state not in list(range(8)):
            log(l.WARNING, f"Read invalid state '{state}' from '{filename}', not loading")
        else:
            winding_states = self.inverted_state_dict[state]
            self.windingA.energize(winding_states[0])
            self.windingB.energize(winding_states[1])

    def step(self, half_step: bool = False, direction: str = "CW", n: int = 1, sleep_time: float = 1e-2):
        for i in range(n):
            next_state = self.get_next_state(half_step=half_step, direction=direction)
            log(l.DEBUG, f"state: {next_state}")
            winding_states = self.inverted_state_dict[next_state]
            self.windingA.energize(winding_states[0])
            self.windingB.energize(winding_states[1])
            sleep(sleep_time)


if __name__ == "__main__":
    argParser = argparse.ArgumentParser(description="Stepper motor driver")
    argParser.add_argument("--spin", default=False, dest="spin", action="store_true", help="spin motor continuously")
    argParser.add_argument("--step", default=False, dest="step", action="store_true", help="Do a single step of the motor")
    argParser.add_argument("--half-step", default=False, dest="half_step", action="store_true", help="Do a half step of the motor")
    argParser.add_argument("--turn", default=False, dest="full_turn", action="store_true", help="Do one full turn")
    argParser.add_argument("-d", "--direction", type=str, default="CW", choices=["CW", "CCW"], help="spin CW or CCW")
    args = argParser.parse_args()

    set_log_level(l.DEBUG)
    log(l.INFO, "setting up GPIO")
    GPIO.setmode(GPIO.BCM)
    B1N1 = 24
    B1N2 = 23
    A1N1 = 25
    A1N2 = 8
    STBY = 7

    GPIO.setup(STBY, GPIO.OUT)
    GPIO.output(STBY, GPIO.HIGH)  # Standby needs to be high or motor is braked
    log(l.INFO, "motor armed")
    stepper = Stepper(A1N1, A1N2, B1N1, B1N2)
    wait_time = 1e-2
    if args.spin:
        log(l.INFO, "starting, press CTRL+C to exit")
        while True:
            try:
                stepper.step(half_step=False)
                sleep(wait_time)
            except KeyboardInterrupt:
                log(l.INFO, "Cleaning up GPIOS and exiting...")
                GPIO.cleanup()
                exit(0)
    elif args.step:  # FIXME this does not work because state resets to 0 every time, maybe store last state in file?
        stepper.step()

    elif args.half_step:
        stepper.step(half_step=True)

    elif args.full_turn:
        for i in range(200):
            stepper.step(half_step=True)
            sleep(wait_time)

    else:
        argParser.error("Must specify one of '--spin', '--step', '--half-step' or '--turn'")

    GPIO.cleanup()
