### PythonInAssembly
Assembly interpreter in assembly

Instruction set:

* DB   Defines a variable as a certain value (will be properly made in the future to actually be bytes)
* MOV  Moves (Copies) the second argument into the first.  MOV X Y => X = Y
* ADD  Adds the second argument into the first   ADD X Y => X += Y
* AND 
* OR
* XOR 
* NOT
* DIV Divides AX by a value, // goes into DX, % goes into EX.
* LSH and RSH Left/Right shift a value N times
* EL EH EQ NE Comparisons    Compare the first value to the second, if false skip the next line.

In main.py, there are 3 verbose levels.
NO_VERBOSE = Only prints what the program itself prints
HALF_VERBOSE = Prints what line it's on, and the IP
FULL_VERBOSE = Prints what the program prints, what line it's running, and a human-readable explanation of what the line does.
