import json
import time

NO_VERBOSE = 0
HALF_VERBOSE = 1
FULL_VERBOSE = 2


def fix_register_name(register):
    """
    :param register: Register name to fix
    :return: Fixes names of registers like "A" to "AX"
    """
    if register == "IP":
        return "IP"
    return F"{register[0]}X"


def parse_action(action, verbose=False):
    """
    :param action: args of line
    :param verbose: print things?
    :return: None
    """
    match action:
        case "MOV", dst, src:
            try:
                data.set(dst, data.get(src))
                if verbose:
                    print(f"Moved {data.get(src)} into {dst}")
            except Exception as e:
                print(f"Failed moving {data.get(src)} into {dst}", e)

        case "ADD", dst, src:
            try:
                data.add(dst, data.get(src))
                if verbose:
                    print(f"Added {data.get(src)} into {dst}")
            except Exception as e:
                print(f"Failed adding {data.get(src)} into {dst}", e)

        case "AND", dst, src:
            try:
                data.set(dst, data.get(dst) & data.get(src))
                if verbose:
                    print(f"Bitwise-AND {data.get(src)} with {dst}")
            except Exception as e:
                print(f"Failed Bitwise-AND {data.get(src)} with {dst}", e)

        case "OR", dst, src:
            try:
                data.set(dst, data.get(dst) | data.get(src))
                if verbose:
                    print(f"Bitwise-OR {data.get(src)} with {dst}")
            except Exception as e:
                print(f"Failed Bitwise-OR {data.get(src)} with {dst}", e)

        case "XOR", dst, src:
            try:
                data.set(dst, data.get(dst) ^ data.get(src))
                if verbose:
                    print(f"Bitwise-XOR {data.get(src)} with {dst}")
            except Exception as e:
                print(f"Failed Bitwise-XOR {data.get(src)} with {dst}", e)
        case "DIV", value:
            try:
                value = data.get(value)
                data.set("DX", data.get("AX") // value)
                data.set("EX", data.get("AX") % value)
                if verbose:
                    print(f"DIV", data.get("AX"), value, data.get("DX"), data.get("EX"))

            except Exception as e:
                print("DIV Failed", e)

        case "NOT", dst:
            try:
                data.set(dst, ~data.get(dst))
                if verbose:
                    print(f"Bitwise-NOT {data.get(dst)}")
            except Exception as e:
                print(f"Failed Bitwise-NOT {data.get(dst)}", e)

        case "LSH", dst, amount:
            try:
                data.set(dst, data.get(dst) << amount)
                if verbose:
                    print(f"LSH {data.get(dst)} by {amount}")
            except Exception as e:
                print(f"Failed LSH {data.get(dst)} by {amount}", e)

        case "RSH", dst, amount:
            try:
                data.set(dst, data.get(dst) >> amount)
                if verbose:
                    print(f"RSH {data.get(dst)} by {amount}")
            except Exception as e:
                print(f"Failed RSH {data.get(dst)} by {amount}", e)

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
                val = data.get(src)
                try:
                    print(f"{src}={val}\t| {hex(val)}\t| {'{0:016b}'.format(val)}")
                except TypeError:
                    # Not string
                    print(f"IP {data.get('IP') + 1}: {src}")
        case "JUMP", label:
            try:
                data.set("IP", data.labels[label])
                if verbose:
                    print(f"Jumped to {label}")
            except KeyError:
                print(f"Failed to jump to {label}")
        case "DEF", name, value:
            try:
                value = int(value)
            except ValueError:
                value = data.get(value)

            if verbose:
                print(f"Setting {name} to {value}")
            data.set(name, value)
        case "LOOP", label:
            if data.get("CX") > 0:
                data.sub("CX", 1)
                data.set("IP", data.labels[label])


class DataBlock:
    """
    Dataseg class
    """
    def __init__(self):
        self.data = {  # data seg
            "AX": 0x0,
            "BX": 0x0,
            "CX": 0x0,
            "DX": 0x0,
            "EX": 0x0,
            "IP": 0x0
        }
        self.registers = {"AX", "BX", "CX", "DX", "EX", "IP"}  # registers in the code
        self.labels = {}  # labels to jump to in the code
        self.flags = {}  # idk i'll make flags later

    def add_label(self, name, IP):
        self.labels[name] = IP

    def get(self, src):
        """
        :param src: Name to fetch
        :return: Fetched value from dataseg,
                 if not found will return the value as it is
        """
        if src[-1] == "X":
            return self.data[fix_register_name(src)]
        elif src[-1] in ["H", "L"]:
            shift = 8 if src[-1] == "H" else 0
            return self.data[fix_register_name(src)] << shift
        else:
            if src in self.data:
                return self.data[src]
            else:
                try:
                    a = int(src, 0)
                    return a
                except ValueError:
                    return src

    def set(self, register, value):
        """
        :param register: Destination to set
        :param value: Value to set
        :return: None
        """
        if register[-1] == "X":
            # full register
            assert value <= 0xFFFF
            self.data[fix_register_name(register)] = value

        elif register[-1] == "L":
            # low
            assert value <= 0xFF
            # Remove low
            self.data[fix_register_name(register)] &= 0xF0
            # Set low
            self.data[fix_register_name(register)] += value

        elif register[-1] == "H":
            assert value <= 0xFF
            # Remove high
            self.data[fix_register_name(register)] &= 0x0F
            # Set high
            self.data[fix_register_name(register)] += (value << 4)
        else:
            # Variable
            self.data[register] = value

    def sub(self, register, value):
        self.add(register, -value)

    def add(self, register, value):
        assert value <= 0xFFFF
        if register[-1] == "H":
            assert value <= 0xFF
            value <<= 4

        fixed_name = fix_register_name(register)
        if fixed_name in self.registers:
            assert self.data[fixed_name] + value <= 0xFFFF
            self.data[fixed_name] += value
        else:
            assert self.data[register] + value <= 0xFFFF
            self.data[register] += value

    def inc_ip(self):
        self.data["IP"] += 1

    def __str__(self):
        return json.dumps(
            {k: hex_split(v) for k, v in self.data.items()},
            indent=2
        )


def hex_split(v):
    a = hex(v)[2:].zfill(4)
    return f"{a[:2]} {a[2:]}"


def init():
    with open('input.txt', 'r') as f:
        inp_str = [x.replace("\n", "") for x in f.readlines()]
    return inp_str


def run(inp_str, verbose=0):
    """
    :param inp_str: Code to run
    :param verbose: Verbose mode (0/1/2).
                    Verbose mode 0 only prints what the code requires to print.
                    Verbose mode 1 prints what line it's running
                    Verbose mode 2 prints all processes
    :return:
    """
    while data.data["IP"] < len(inp_str):
        line = inp_str[data.data["IP"]].split("#")[0]
        if verbose:
            print(f'{data.data["IP"] + 1}', end=":\t ")
            print(line)

        if line.endswith(":"):
            # Make a label
            data.labels[line[:-1]] = data.data["IP"]
        else:
            parse_action(line.split(), verbose == 2)

        data.inc_ip()


if __name__ == "__main__":
    data = DataBlock()
    run(init(), verbose=NO_VERBOSE)
