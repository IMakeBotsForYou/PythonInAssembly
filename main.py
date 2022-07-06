import json
import os
import time
import math

NO_VERBOSE = 0
HALF_VERBOSE = 1
FULL_VERBOSE = 2


def by_value(src):
    return src[0] == "[" and src[-1] == "]"


def parse_action(action, verbose=False):
    """
    :param action: args of line
    :param verbose: print things?
    :return: None
    """
    match action:
        case "MOV", dst, src:
            try:
                # If we are moving an INT value into a register / var,
                # move the value.
                # Otherwise, move the pointer to the said source.

                data.set(dst, data.get(src))
                if verbose:
                    print(f"Moved {data.get(src)} into {dst}")
            except Exception as e:
                raise Exception(f"Failed moving {data.get(src)} into {dst}", e)

        case "ADD", dst, src:
            try:
                value = data.get(src)
                data.add(dst, value)
                if verbose:
                    print(f"Added {value} into {dst}")
            except Exception as e:
                raise Exception(f"Failed adding {data.get(src)} into {dst}", e)

        case "AND", dst, src:
            try:
                data.set(dst, data.get(dst) & data.get(src))
                if verbose:
                    print(f"Bitwise-AND {data.get(src)} with {dst}")
            except Exception as e:
                raise Exception(f"Failed Bitwise-AND {data.get(src)} with {dst}", e)

        case "OR", dst, src:
            try:
                data.set(dst, data.get(dst) | data.get(src))
                if verbose:
                    print(f"Bitwise-OR {data.get(src)} with {dst}")
            except Exception as e:
                raise Exception(f"Failed Bitwise-OR {data.get(src)} with {dst}", e)

        case "XOR", dst, src:
            try:
                data.set(dst, data.get(dst) ^ data.get(src))
                if verbose:
                    print(f"Bitwise-XOR {data.get(src)} with {dst}")
            except Exception as e:
                raise Exception(f"Failed Bitwise-XOR {data.get(src)} with {dst}", e)
        case "DIV", value:
            try:
                value = data.get(value)
                data.set("DX", data.get("AX", value=True) // value)
                data.set("EX", data.get("AX", value=True) % value)
                if verbose:
                    print(f"DIV", F'AX={data.get("AX", value=True)}, {value=}, '
                                  F'//={data.get("DX", value=True)}, '
                                  F'%={data.get("EX", value=True)}')

            except Exception as e:
                raise Exception("DIV Failed", e)

        case "NOT", dst:
            try:
                data.set(dst, ~data.get(dst))
                if verbose:
                    print(f"Bitwise-NOT {data.get(dst)}")
            except Exception as e:
                raise Exception(f"Failed Bitwise-NOT {data.get(dst)}", e)

        case "LSH", dst, amount:
            try:
                data.set(dst, data.get(dst) << amount)
                if verbose:
                    print(f"LSH {data.get(dst)} by {amount}")
            except Exception as e:
                raise Exception(f"Failed LSH {data.get(dst)} by {amount}", e)

        case "RSH", dst, amount:
            try:
                data.set(dst, data.get(dst) >> amount)
                if verbose:
                    print(f"RSH {data.get(dst)} by {amount}")
            except Exception as e:
                raise Exception(f"Failed RSH {data.get(dst)} by {amount}", e)

        case "EL" | "EH" | "EQ" | "NE", src, amount:
            # EL Equal Lower
            # EH Equal Higher
            # EQ Equal
            # NE Not Equal
            value = data.get(src)
            amount = data.get(amount)  # Parse int
            action = action[0]
            if verbose:
                print(f"{action} on {src}({data.get(src)}) and {amount}", end="\t")
            # If condition is not met,
            # We want to jump over the next line.
            if action == "NE" and amount != value:
                if verbose:
                    print("returned True.")
                return

            # Now handle the EQUAL clauses

            # "EL" | "EH" | "EQ"
            eq_type = action[1]
            if eq_type == "L" and value <= amount:
                if verbose:
                    print("EL returned True.")
                return
            if eq_type == "H" and value >= amount:
                if verbose:
                    print("EH returned True.")
                return
            if eq_type == "Q" and value == amount:
                if verbose:
                    print("EQ returned True.")
                return

            # Clause failed, skip next line

            data.inc_ip()
            if verbose:
                print(F"returned False")
            # Now we are *on* the next line.
            # This ensures that when we finish
            # Processing this line, we'll inc again,
            # Thus jumping over the next line.

        case "PRINT", *srcs:
            for src in srcs:
                print(data.get(src))

        case "JUMP", label:
            try:
                data.set("IP", data.labels[label])
                if verbose:
                    print(f"Jumped to {label}")
            except KeyError:
                raise Exception(f"Failed to jump to {label}")
        case "DB" | "DW", name, *args:
            if len(args) == 1:
                value = int(data.get(args[0]))
            else:
                value = " ".join(args)

            if verbose:
                print(f"Setting {name} to {value}")
            data.set(name, value)

        case "LOOP", label:
            if data.get("CX", value=True) > 0:
                data.sub("CX", 1)
                data.set("IP", data.labels[label])


class DataBlock:
    """
    Data seg class
    """

    def __init__(self, size=64):
        # This stores the location of data (pointers) in the virtual memory
        self.data = bytearray(size)
        self.pointers = {  # pointer, length of data
            "AX": [0, 2],
            "AL": [1, 1],
            "AH": [0, 1],

            "BX": [2, 2],
            "BL": [3, 1],
            "BH": [2, 1],

            "CX": [4, 2],
            "CL": [5, 1],
            "CH": [4, 1],

            "DX": [6, 2],
            "DL": [7, 1],
            "DH": [6, 1],

            "EX": [8, 2],
            "EL": [9, 1],
            "EH": [8, 1],

            "IP": [10, 2]
        }
        self.bump_pointer = 12
        self.registers = list(self.pointers.copy().keys())  # registers in the code
        self.labels = {}  # labels to jump to in the code
        self.flags = {}  # idk i'll make flags later

    def set(self, name, value):
        # Translate value into bytes
        new_bytes = None
        register = False
        little = False  # 2 byte | 1 bytes
        # Classify registers
        if name in self.registers:
            register = True
            if name[-1] != "X" and name != "IP":
                little = True

        try:
            # Int
            # Get appropriate amount of bytes
            if value > 1:
                length = math.ceil(math.log(value, 256))
                if value % 256 == 0:
                    length += 1
            else:
                length = 1

            if register:
                assert length <= 2
            if little:
                assert length == 1

            new_bytes = value.to_bytes(length, "big")

        except (AttributeError, TypeError):
            pass
        if not new_bytes:
            try:
                # Str
                new_bytes = (value + "\x00").encode()
            except AttributeError:
                pass

        if not new_bytes:
            new_bytes = value

        if name in self.pointers:
            start = self.pointers[name][0]
        else:
            self.pointers[name] = [self.bump_pointer, len(new_bytes)]
            start = self.pointers[name][0]
            self.bump_pointer += len(new_bytes)

        assert self.bump_pointer + self.pointers[name][1] < len(self.data)

        if not register or little:
            for i, v in enumerate(new_bytes):
                self.data[start + i] = v
        elif not little:
            # fill to 2 bytes
            new_bytes = b'\x00' * (2 - len(new_bytes)) + new_bytes
            for i, v in enumerate(new_bytes):
                self.data[start + i] = v

    def get(self, src, value=None):
        """
        Get a value from a pointer
        value   Value | Pointer
        """
        if value is None:
            value = by_value(src)
            if value:
                src = src[1:-1]

        if src in self.registers:
            start, length = self.pointers[src]
            if not value:
                return start

            end = start + length

            if self.data[end-1] == "\x00":
                return self.data[start:end].decode()
            else:
                return int.from_bytes(self.data[start:end], byteorder='big')

        if src in self.pointers:
            # Return value
            start, length = self.pointers[src]
            if not value:
                return start
            end = start + length
            if self.data[end-1] == "\x00":
                return self.data[start:end].decode()
            else:
                return int.from_bytes(self.data[start:end], byteorder='big')

        try:
            return int(src)
        except ValueError:
            return src

    def add_label(self, name, IP):
        self.labels[name] = IP

    def sub(self, register, value):
        self.add(register, -value)

    def add(self, register, value: int):
        # Takes in int value and adds to memory
        value += data.get(register, value=True)
        self.set(register, value)

    def inc_ip(self):
        """
        Increment the IP value by one
        """
        self.add("IP", 1)

    def __str__(self):
        """
        Dump the data segment and format it
        """
        get_group = lambda p: "".join([f'{k} ' + f'{data.get(k, value=True)}'.ljust(5)
                                       + f'{hex(data.get(k, value=True))}'.ljust(7)
                                       for k in [f'{p}X', f'{p}H', f'{p}L']])

        registers = ['A', 'B', 'C', 'D', 'E']
        ret = "\n".join([json.dumps(get_group(r)) for r in registers])
        ret += f"\nIP: {data.get('IP', value=True)}"
        return ret


def init():
    """
    Load the code into memory
    """
    with open('input.txt', 'r') as f:
        inp_str = [x.replace("\n", "") for x in f.readlines()]
    return inp_str


def run(inp_str, verbose=0):
    """
    :param inp_str: Code to run
    :param verbose: Verbose mode (0/1/2).
                    Verbose mode 0 only prints what the code requires printing.
                    Verbose mode 1 prints what line it's running
                    Verbose mode 2 prints all processes
    :return:
    """
    current_ip = data.get("IP", value=True)
    print(F"#### {len(inp_str)} lines. ####")
    while current_ip < len(inp_str):
        line = inp_str[current_ip].split("#")[0]
        if verbose:
            print(f'{current_ip + 1}', end=":\t ")
            print(line)

        if line.endswith(":"):
            # Make a label
            data.labels[line[:-1]] = current_ip
        else:
            parse_action(line.split(), verbose == 2)

        data.inc_ip()
        current_ip = data.get("IP", value=True)


if __name__ == "__main__":
    data = DataBlock()
    run(init(), verbose=NO_VERBOSE)
