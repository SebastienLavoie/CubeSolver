import numpy as np
import logger as log
import logging
from enum import Enum
from pathlib import Path

logger = log.setup(name=str(Path(__file__).stem))
logger.setLevel(logging.DEBUG)


class CubeVals(Enum):
    """
    Each CubeVal contains it's RGB values
    """
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    ORANGE = (255, 153, 51)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    WHITE = (255, 255, 255)


class Face:
    def __init__(self, ndarray: np.ndarray[CubeVals] = None):
        if ndarray is None:
            self.values = np.zeros((3, 3))
        else:
            if not isinstance(ndarray[0][0], CubeVals) or ndarray.shape != (3, 3):
                raise ValueError("Face class takes a 3x3 array of CubeVals")
            else:
                self.values = ndarray
                self.center = ndarray[1][1]

    def _set_row(self, row: int, ndarray: np.ndarray) -> None:
        if ndarray.shape != (3,):
            raise ValueError(f"Expected array of shape (1, 3), got array of shape {ndarray.shape}")
        elif row > 2:
            raise ValueError(f"Row '{row}' is out of bounds, indexing starts at 0")
        else:
            if ndarray == self.values[row]:
                logger.warn("Got top row values identical to previous ones")
            self.values[row] = ndarray

    def _set_column(self, column: int, ndarray: np.ndarray) -> None:
        if ndarray.shape != (3,):
            raise ValueError(f"Expected array of shape (1, 3), got array of shape {ndarray.shape}")
        elif column > 2:
            raise ValueError(f"Row '{column}' is out of bounds, indexing starts at 0")
        else:
            if ndarray == self.values[:, column]:
                logger.warn("Got top row values identical to previous ones")
            self.values[:, column] = ndarray

    @property
    def top_row(self) -> np.ndarray:
        return self.values[0]

    @top_row.setter
    def top_row(self, ndarray: np.ndarray) -> None:
        self._set_row(0, ndarray)

    @property
    def bottom_row(self) -> np.ndarray:
        return self.values[2]

    @bottom_row.setter
    def bottom_row(self, ndarray: np.ndarray) -> None:
        self._set_row(2, ndarray)

    @property
    def left_column(self) -> np.ndarray:
        return self.values[:, 0]

    @left_column.setter
    def left_column(self, ndarray: np.ndarray) -> None:
        self._set_column(0, ndarray)

    @property
    def right_column(self) -> np.ndarray:
        return self.values[:, 2]

    @right_column.setter
    def right_column(self, ndarray: np.ndarray) -> None:
        self._set_column(2, ndarray)

    def rotate90(self, direction: str, k: int = 1) -> None:
        """
        :param direction: rotation direction, can be either CW or CCW
        :param k: Amount of times to rotate by 90 degrees
        :return: Nothing
        """
        if direction not in ["CW", "CCW"]:
            raise ValueError(f"Direction must be one of 'CW' or 'CCW', got '{direction}'")
        elif k % 4 == 0:
            logger.warn("Are you stupid?")
        elif direction == "CW":
            self.values = np.rot90(self.values, k * 3)  # Rotate 3 times because direction of np.rot90 is CCW
        else:
            self.values = np.rot90(self.values, k)
        logger.debug(f"Rotated {direction} {k} times")


class Cube:
    """
            WHITE

    BLUE    RED     GREEN   ORANGE

            YELLOW
    """