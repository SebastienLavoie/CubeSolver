import numpy as np
import logger as log
import logging
from enum import Enum
from pathlib import Path
import tkinter as tk

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
    def __init__(self, ndarray: np.ndarray = None):
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


class GUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.entries = {}
        self.tableheight = 3
        self.tablewidth = 3
        self.create_widgets()


    def create_widgets(self):
        counter = 0
        middle = tk.StringVar()
        for row in range(self.tableheight):
            for column in range(self.tablewidth):
                if counter == 4:
                    self.entries[counter] = tk.Entry(self, width=10, textvariable=middle, state="disabled")
                else:
                    self.entries[counter] = tk.Entry(self, width=10)
                self.entries[counter].grid(row=row, column=column)
                counter += 1
        middle.set("W")

    def print_table(self):
        print(self.entries[4].get())

class Cube:
    """
               WHITE (U)

  ORANGE (L)   GREEN (F)    RED (R)    BLUE (B)

              YELLOW (D)
    """
    def __init__(self, state):
        

if __name__ == "__main__":
    root = tk.Tk()
    app = GUI(master=root)
    app.mainloop()
    while True:
        try:
            app.update_idletasks()
            app.update()
            app.print_table()
        except KeyboardInterrupt:
            exit(0)
