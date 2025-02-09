

const sample_files_list = [];

sample_files_list.push(`console.log("--------------------------");
console.log("---------MATRICES---------");
console.log("----------14 pts----------");
console.log("--------------------------");

console.log("");
console.log("Creación de Matriz!");
const notas: number[][] = [
    [53, 88, 95, 89, 75],
    [81, 51, 57, 67, 93],
    [94, 74, 58, 84, 100]
];

console.log("");
console.log("Acceso:");
console.log("Esta suma debería ser 100: ", notas[1][0] + 19);
console.log("Esta suma debería ser 100: ", notas[0][4] + 25);
console.log("Esta suma debería ser 100: ", notas[2][0] + 6);
console.log("Esta suma debería ser 245: ", notas[0][1] + notas[1][2] + notas[2][4]);

console.log("");
const md: number[] = [1, 2, 3, 4, 5, 6];
console.log("Matriz de una dimensión: ", md[0]);

console.log("");
const mdd: number[][] = [
    [1, 2, 3, 4, 5, 6],
    [1, 2, 3, 4, 5, 6],
    [1, 2, 3, 4, 5, 6]
];
console.log("Matriz de dos dimensiones: ", mdd[0][1]);

console.log("");
const mddd: number[][][] = [
    [
        [1, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 6]
    ],
    [
        [1, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 6]
    ]
];
console.log("Matriz de tres dimensiones: ", mddd[0][1][2]);

console.log("");
var mdddd: number[][][][] = [
    [
        [
            [1, 2],
            [1, 2]
        ],
        [
            [1, 2],
            [1, 2]
        ]
    ],
    [
        [
            [1, 2],
            [1, 2]
        ],
        [
            [1, 2],
            [1, 2]
        ]
    ]
];
console.log("Matriz de N dimensiones: ", mdddd[0][1][1][1]);

console.log("");
console.log("Asignación:");
console.log("Valor inicial: ", mdddd[1][1][1][1]);
mdddd[1][1][1][1] = notas[0][4] + 25;
console.log("Valor final: ", mdddd[1][1][1][1]);

/*
--------------------------
---------MATRICES---------
----------14 pts----------
--------------------------

Creación de Matriz!

Acceso:
Esta suma debería ser 100:  100
Esta suma debería ser 100:  100
Esta suma debería ser 100:  100
Esta suma debería ser 245:  245

Matriz de una dimensión:  1

Matriz de dos dimensiones:  2

Matriz de tres dimensiones:  3

Matriz de N dimensiones:  2

Asignación:
Valor inicial:  2
Valor final:  100
*/`);


sample_files_list.push(`console.log("--------------------------");
console.log("---------ARREGLOS---------");
console.log("----------12 pts----------");
console.log("--------------------------");

console.log("");
console.log("=============================================");
console.log("================CREACIÓN=====================");
console.log("=============================================");
var arr1: number[] = [8, 4, 6, 2];
var arr2: number[] = [40, 21, 1, 3, 14, 4];
var arr3: number[] = [90, 3, 40, 10, 8, 5];
console.log("Se crean los arreglos arr1, arr2, arr3");
console.log("arr1: ", arr1);
console.log("arr2: ", arr2);
console.log("arr3: ", arr3);

console.log("");
console.log("=============================================");
console.log("=================ACCESO======================");
console.log("=============================================");

console.log("arr1: ", arr1[1]+4);
console.log("arr2: ", 5+8*5-arr2[2]);
console.log("arr3: ", arr3[4]*8);

console.log("=============================================");
console.log("================FUNCIONES====================");
console.log("=============================================");

console.log("============ PUSH");
console.log("arr1: ", arr1);
arr1.push(9);
console.log("arr1: ", arr1);

console.log("============ POP");
console.log("arr2: ", arr2);
console.log("pop arr2: ", arr2.pop());
console.log("arr2: ", arr2);

console.log("============ INDEXOF");
console.log("Posición 3: ", arr3.indexOf(10));
console.log("Posición -1: ", arr3.indexOf(666));

console.log("============ JOIN");
console.log("arr1: ", arr1.join());
console.log("arr2: ", arr2.join());
console.log("arr3: ", arr3.join());

console.log("============ LENGTH");
console.log("arr1: ", arr1, "length: ", arr1.length);
console.log("arr2: ", arr2, "length: ", arr2.length);
console.log("arr3: ", arr3, "length: ", arr3.length);
console.log("Eliminando indices: ", arr1.pop(), arr2.pop(), arr3.pop());
console.log("arr1: ", arr1, "length: ", arr1.length);
console.log("arr2: ", arr2, "length: ", arr2.length);
console.log("arr3: ", arr3, "length: ", arr3.length);

/*
--------------------------
---------ARREGLOS---------
----------12 pts----------
--------------------------

=============================================
================CREACIÓN=====================
=============================================
Se crean los arreglos arr1, arr2, arr3
arr1:  [ 8, 4, 6, 2 ]
arr2:  [ 40, 21, 1, 3, 14, 4 ]
arr3:  [ 90, 3, 40, 10, 8, 5 ]

=============================================
=================ACCESO======================
=============================================
arr1:  8
arr2:  44
arr3:  64
=============================================
================FUNCIONES====================
=============================================
============ PUSH
arr1:  [ 8, 4, 6, 2 ]
arr1:  [ 8, 4, 6, 2, 9 ]
============ POP
arr2:  [ 40, 21, 1, 3, 14, 4 ]
pop arr2:  4
arr2:  [ 40, 21, 1, 3, 14 ]
============ INDEXOF
Posición 3:  3
Posición -1:  -1
============ JOIN
arr1:  8,4,6,2,9
arr2:  40,21,1,3,14
arr3:  90,3,40,10,8,5
============ LENGTH
arr1:  [ 8, 4, 6, 2, 9 ] length:  5
arr2:  [ 40, 21, 1, 3, 14 ] length:  5
arr3:  [ 90, 3, 40, 10, 8, 5 ] length:  6
Eliminando indices:  9 14 5
arr1:  [ 8, 4, 6, 2 ] length:  4
arr2:  [ 40, 21, 1, 3 ] length:  4
arr3:  [ 90, 3, 40, 10, 8 ] length:  5
*/`
);

sample_files_list.push(`console.log("----------------------");
console.log("----ARCHIVO BASICO----");
console.log("--------16 pts--------");
console.log("----------------------");

var bol: boolean = false;
var bol2: boolean = !bol;
var cad1: string = "imprimir";
var cad2: string = "cadena valida";

var val1: number = 7 - (5 + 10 * (2 + 4 * (5 + 2 * 3)) - 8 * 3 * 3) + 50 * (6 * 2);
var val2: number = (2 * 2 * 2 * 2) - 9 - (8 - 6 + (3 * 3 - 6 * 5 - 7 - (9 + 7 * 7 * 7) + 10) - 5) + 8 - (6 - 5 * (2 * 3));
var val3: number = val1 + ((2 + val2 * 3) + 1 - ((2 * 2 * 2) - 2) * 2) - 2;

console.log("El valor de val1 es:", val1);
console.log("El valor de val2 es:", val2);
console.log("El valor de val3 es:", val3);
console.log("El resultado de la operación es:", val3);
console.log("El valor de bol es:", bol);
console.log("El valor de cad1 es:", cad1);
console.log("El valor de cad2 es:", cad2);
console.log("El valor de bol2:", bol2);

var a: number = 100;
var b: number = 100;
var c: number = 7;
var f: boolean = true;
var j: number = 10;
var k: number = 10;

console.log((a > b || b < c));

console.log((a == b && j == k) || 14 != c);

var val: number = 5;
var resp: number = 5;
var valorVerdadero: number = 100;

console.log((valorVerdadero == (50 + 50 + (val - val))) && (!(!true)));

var x1: number = 15;
console.log(x1 % 2 == 0);

/*
----------------------
----ARCHIVO BASICO----
--------16 pts--------
----------------------
El valor de val1 es: 214
El valor de val2 es: 412
El valor de val3 es: 1439
El resultado de la operación es: 1439
El valor de bol es: false
El valor de cad1 es: imprimir
El valor de cad2 es: cadena valida
El valor de bol2: true
false
true
true
false
valor nulo:  null
*/`);

sample_files_list.push(`console.log("--------------------------");
console.log("----ARCHIVO INTERMEDIO----");
console.log("----------15 pts----------");
console.log("--------------------------");

console.log("");
console.log("=======================================================================");
console.log("=============================IFs ANIDADOS==============================");
console.log("=======================================================================");
var a: number = 909;
var aux: number = 10;
if (aux > 0) {
    console.log("PRIMER IF CORRECTO");
    if (true && (aux == 1)) {
        console.log("SEGUNDO IF INCORRECTO");
    } else if (aux > 10) {
        console.log("SEGUNDO IF INCORRECTO");
    } else {
        console.log("SEGUNDO IF CORRECTO");
    }
} else if (aux <= 3) {
    console.log("PRIMER IF INCORRECTO");
    if (true && (aux == 1)) {
        console.log("SEGUNDO IF INCORRECTO");
    } else if (aux > 10) {
        console.log("SEGUNDO IF INCORRECTO");
    } else {
        console.log("SEGUNDO IF CORRECTO");
    }
} else if (aux == a) {
    console.log("PRIMER IF INCORRECTO");
    if (true && (aux == 1)) {
        console.log("SEGUNDO IF INCORRECTO");
    } else if (aux > 10) {
        console.log("SEGUNDO IF INCORRECTO");
    } else {
        console.log("SEGUNDO IF CORRECTO");
    }
}

console.log("");
console.log("=======================================================================");
console.log("=================================WHILE=================================");
console.log("=======================================================================");
var index: number = 0;
while (index >= 0) {
    if (index == 0) {
        index = index + 100;
    } else if (index > 50) {
        index = index / 2 - 25;
    } else {
        index = (index / 2) - 1;
    }
    console.log(index);
}

console.log("");
console.log("=======================================================================");
console.log("==================================FOR===================================");
console.log("=======================================================================");
for (var i: number = 0; i <= 9; i++) {
    var output: string = "";
    for (var j: number = 0; j <= (10 - i); j++) {
        output = output + " ";
    }
    for (var k: number = 0; k <= i; k++) {
        output = output + "* ";
    }
    console.log(output);
}

console.log("");
console.log("=======================================================================");
console.log("================================SWITCH=================================");
console.log("=======================================================================");
const numero: number = 2;
switch (numero) {
    case 1:
        console.log("Uno");
        break;
    case 2:
        console.log("Dos");
        break;
    case 3:
        console.log("Tres");
        break;
    default:
        console.log("Invalid day");
        break;
}

console.log("");
console.log("=======================================================================");
console.log("=============================TRANSFERENCIA=============================");
console.log("=======================================================================");
a = -1;
while (a < 5) {
    a = a + 1;
    if (a == 3) {
        console.log("a");
        continue;
    } else if (a == 4) {
        console.log("b");
        break;
    }
    console.log("El valor de a es:", a);
}
console.log("Se debió imprimir");


/*
--------------------------
----ARCHIVO INTERMEDIO----
----------15 pts----------
--------------------------

=======================================================================
=============================IFs ANIDADOS==============================
=======================================================================
PRIMER IF CORRECTO
SEGUNDO IF CORRECTO

=======================================================================
=================================WHILE=================================
=======================================================================
100
25
11.5
4.75
1.375
-0.3125

=======================================================================
==================================FOR===================================
=======================================================================
           * 
          * * 
         * * * 
        * * * * 
       * * * * * 
      * * * * * * 
     * * * * * * * 
    * * * * * * * * 
   * * * * * * * * * 
  * * * * * * * * * * 

=======================================================================
================================SWITCH=================================
=======================================================================
Dos

=======================================================================
=============================TRANSFERENCIA=============================
=======================================================================
El valor de a es: 0
El valor de a es: 1
El valor de a es: 2
a
b
Se debió imprimir
*/`);

sample_files_list.push(`console.log("--------------------------");
console.log("---FUNCIONES EMBEBIDAS----");
console.log("----------14 pts----------");
console.log("--------------------------");

console.log("");
console.log("--------- FUNCIÓN SUMA");
function suma(numero1: number, numero2: number): number {
    const resultado: number = numero1 + numero2;
    return resultado;
}

const resultado: number = suma(5, 3);
console.log("La suma es: ", resultado);

console.log("");
console.log("--------- MULTIPLES LLAMADAS");
function saludo3(){
    console.log("saludos!");
}

function saludo2(){
    console.log("mundo");
    saludo3();
}

function saludo1(){
    console.log("hola");
    saludo2();
}

saludo1();

console.log("");
function ejemplo2(a: number, b: number){
    console.log(a);
    console.log(b);
}

const precio1: number = 66;
const precio2: number = 77;
ejemplo2(precio1, precio2);

console.log("");
function addValue(x: number[], y: number){
    x.push(y);
}

var numeros: number[] = [1,2,3,4,5];
console.log("numeros inicial: ", numeros);
addValue(numeros, 6);
console.log("numeros final: ", numeros);

console.log("");
const num3: float = parseFloat("9.5");
const num4: float = parseFloat("3.6");
const num1: number = parseInt("20");
const num2: number = parseInt("20");
var temp1: float = num1 + num2;
var temp2: float = num3 - num4;
const sumaStr: string = temp1.toString();
const restaStr: string = temp2.toString();

const flag : boolean = true;
console.log("valor true: ", flag.toString());
console.log("valor false: ", false.toString());
console.log("valor 1: ", sumaStr);
console.log("valor 2: ", restaStr);
const letras: string = "hOlA MuNDo";
const min: string = letras.toLowerCase();
const may: string = letras.toUpperCase();
console.log("valor minusculas: ", min);
console.log("valor mayusculas: ", may);
console.log("Tipos de datos:");
console.log("---", typeof num1);
console.log("---", typeof letras);
console.log("---", typeof flag);

/*
--------------------------
---FUNCIONES EMBEBIDAS----
----------14 pts----------
--------------------------

--------- FUNCIÓN SUMA
La suma es:  8

--------- MULTIPLES LLAMADAS
hola
mundo
saludos!

66
77

numeros inicial:  [ 1, 2, 3, 4, 5 ]
numeros final:  [ 1, 2, 3, 4, 5, 6 ]

valor true:  true
valor false:  false
valor 1:  40
valor 2:  5.9
valor minusculas:  hola mundo
valor mayusculas:  HOLA MUNDO
Tipos de datos:
--- number
--- string
--- boolean
*/`);

sample_files_list.push(`function f(n: number): number {
    if (n < 2) {
        return 1;
    } else {
        return n * f(n - 1);
    }
}

function ack(m: number, n: number): number {
    if (m == 0) {
        return n + 1;
    } else if (n == 0) {
        return ack(m - 1, 1);
    } else {
        return ack(m - 1, ack(m, n - 1));
    }
}

console.log("--------------------------");
console.log("----ARCHIVO RECURSIVOS----");
console.log("--------------------------");

console.log("Factorial de 6: ", f(6));
console.log("Factorial de 4: ", f(4));
console.log("Factorial de 3: ", f(3));

console.log("");
console.log("Ackerman de 3,0: ", ack(3, 0));
console.log("Ackerman de 2,8: ", ack(2, 8));
console.log("Ackerman de 2,1: ", ack(2, 1));


/*
--------------------------
----ARCHIVO RECURSIVOS----
--------------------------
Factorial de 6:  720
Factorial de 4:  24
Factorial de 3:  6

Ackerman de 3,0:  5
Ackerman de 2,8:  19
Ackerman de 2,1:  5
*/`);

sample_files_list.push(`console.log("--------------------------");
console.log("--------INTERFACES--------");
console.log("----------10 pts----------");
console.log("--------------------------");

console.log(" ");
console.log("=============================================");
console.log("================DEFINICIÓN===================");
console.log("=============================================");

interface StructArr {
    datos: number;
}

interface CentroTuristico {
    nombre: string;
}

interface Carro {
    placa: string;
    color: string;
    tipo: string;
}

interface Personaje {
    nombre: string;
    edad: number;
    descripcion: string;
    carro: Carro;
    numeros: StructArr;
}

console.log(" ");
console.log("=============================================");
console.log("================INSTANCIACIÓN=================");
console.log("=============================================");

const centro1: CentroTuristico = { nombre: "Volcan de pacaya" };
const centro2: CentroTuristico = { nombre: "Rio dulce" };
const centro3: CentroTuristico = { nombre: "Laguna Luchoa" };
const centro4: CentroTuristico = { nombre: "Playa Blanca" };
const centro5: CentroTuristico = { nombre: "Antigua Guatemala" };
const centro6: CentroTuristico = { nombre: "Lago de Atitlan" };
const newCarro: Carro = { placa: "090PLO", color: "gris", tipo: "mecanico" };
const nums: StructArr = { datos: 0.0 };

var p1: Personaje = {
    nombre: "Jose",
    edad: 18,
    descripcion: "No hace nada",
    carro: newCarro,
    numeros: nums
};

const nums2: StructArr = { datos: parseFloat("23.43") };

console.log(" ");
console.log("=============================================");
console.log("========ASIGNACIÓN Y ACCESO==================");
console.log("=============================================");

console.log("El nombre del Centro turistico 1 es: ", centro1.nombre);
console.log("El nombre del Centro turistico 2 es: ", centro2.nombre);
console.log("El nombre del Centro turistico 3 es: ", centro3.nombre);
console.log("El nombre del Centro turistico 4 es: ", centro4.nombre);
console.log("El nombre del Centro turistico 5 es: ", centro5.nombre);
console.log("El nombre del Centro turistico 6 es: ", centro6.nombre);

console.log("Persona nombre: ", p1.nombre, ", edad: ", p1.edad, ", carroTipo: ", p1.carro.tipo, ", numeros: ", p1.numeros.datos);
p1.numeros = nums2;
console.log("Persona nombre: ", p1.nombre, ", edad: ", p1.edad, ", carroTipo: ", p1.carro.tipo, ", nuevos numeros: ", p1.numeros.datos);

console.log("");
console.log("=============================================");
console.log("=================FUNCIONES===================");
console.log("=============================================");
console.log("Llaves: ", Object.keys(newCarro));
console.log("Valores: ", Object.values(newCarro));

/*
--------------------------
--------INTERFACES--------
----------10 pts----------
--------------------------
 
=============================================
================DEFINICIÓN===================
=============================================
 
=============================================
================INSTANCIACIÓN=================
=============================================
 
=============================================
========ASIGNACIÓN Y ACCESO==================
=============================================
El nombre del Centro turistico 1 es:  Volcan de pacaya
El nombre del Centro turistico 2 es:  Rio dulce
El nombre del Centro turistico 3 es:  Laguna Luchoa
El nombre del Centro turistico 4 es:  Playa Blanca
El nombre del Centro turistico 5 es:  Antigua Guatemala
El nombre del Centro turistico 6 es:  Lago de Atitlan
Persona nombre:  Jose , edad:  18 , carroTipo:  mecanico , numeros:  0
Persona nombre:  Jose , edad:  18 , carroTipo:  mecanico , nuevos numeros:  23.43

=============================================
=================FUNCIONES===================
=============================================
Llaves:  [ 'placa', 'color', 'tipo' ]
Valores:  [ '090PLO', 'gris', 'mecanico' ]
*/`);

sample_files_list.push(`function fibonacci(num: number): number {
    if (num < 2) {
        return num;
    } else {
        return fibonacci(num-1) + fibonacci(num-2);
    }
}

for (var i: number = 0; i <= 15; i++) {
    console.log("fibonacci(", i, ") = ", fibonacci(i));
}`);

sample_files_list.push(`
function towerOfHanoi(n: number, source: string, target: string, auxiliary: string) {
    if (n > 0) {
        // Move n - 1 disks from source to auxiliary, so they are out of the way
        towerOfHanoi(n - 1, source, auxiliary, target);

        // Move the nth disk from source to target
        console.log("Move disk", n, "from", source, "to", target);

        // Move the n - 1 disks that we left on auxiliary to target
        towerOfHanoi(n - 1, auxiliary, target, source);
    }
}

// Example usage:
console.log("Hanoi towers with 3 disks");
console.log("");
towerOfHanoi(3, "A", "B", "C");  // A, B and C are the names of rods
console.log("");
console.log("Hanoi towers with 7 disks");
console.log("");
towerOfHanoi(7, "A", "B", "C");  // A, B and C are the names of rods
console.log("");`);

sample_files_list.push(`interface Comic {
    name: string;
    year: number;
    house: string;
    issues: number[];
}

var c1: Comic = { name: "Spider-Man", year: 1932, house: "marvel", issues: [120, 125, 45, 18] };
var c2: Comic = { name: "Super-Man", year: 1935, house: "dc", issues: [166, 44, 55, 98] };
var c3: Comic = { name: "Thor", year: 2010, house: "marvel", issues: [1, 2, 3, 4] };

var myComics: Comic[] = [c1, c2, c3];

for (var comic of myComics) {
    console.log(comic);
}`);

sample_files_list.push(`/*

 https://en.wikipedia.org/wiki/Brainfuck
 
 From wikipedia:

 Brainfuck is an esoteric programming language created in 1993 by Swiss student Urban Müller. Designed to be extremely
 minimalistic, the language consists of only eight simple commands,
 a data pointer, and an instruction pointer.
*/

// Create a new 10,000 size array, with each cell initialized with the value of 0. Memory can expand.
const MEMORY_SIZE: number = 10000;
var memory: number[] = [0]; // TODO: fix the empty array implementatio in the interpreter!!!
memory.pop();
// zeroed the memory
for (var i:number = 0; i < MEMORY_SIZE; i++) {
	memory.push(0);
}

//Instruction pointer (Points to the current instruction)
var ipointer:number = 0;
// Memory pointer (Points to a cell in memory)
var mpointer:number = 0;
// Address stack. Used to track addresses (index) of left brackets
var astack: number[] = [0]; 
astack.pop();

// The brainf@ck code
var program_as_string: string = "++++++++[>+>++>+++>++++>+++++>++++++>+++++++>++++++++>+++++++++>++++++++++>+++++++++++>++++++++++++>+++++++++++++>++++++++++++++>+++++++++++++++>++++++++++++++++<<<<<<<<<<<<<<<<-]>>>>>>>>>.<<<<<<<<<>>>>>>>>>>>>>>-.+<<<<<<<<<<<<<<>>>>>>>>>>>>>>----.++++<<<<<<<<<<<<<<>>>>>>>>>>>>+.-<<<<<<<<<<<<>>>>.<<<<>>>>>>>>>>>>>>---.+++<<<<<<<<<<<<<<>>>>>>>>>>>>>>>---.+++<<<<<<<<<<<<<<<>>>>>>>>>>>>>>--.++<<<<<<<<<<<<<<>>>>>>>>>>>>>----.++++<<<<<<<<<<<<<>>>>>>>>>>>>>>-.+<<<<<<<<<<<<<<.";
var program: string[] = [""];
program.pop();

// For convenience transform the input program into a array of strings
for (var current of program_as_string) {
	program.push(current);
}

// The input for the program, if required
var input: string = "";
// the output of the program
var output: string = "";

// Since we don't have any builtin function to get the ASCII value of an integer
function intToASCII(value: number): string {
    
    // return the empty string since this will not affect the output
    if (value < 32 || value > 126) {
	    return "";
    }
    // Keep it simple ... numbers and letters.
    switch (value) {
	case 32: return " ";
        case 48: return "0"; case 49: return "1"; case 50: return "2"; case 51: return "3";
        case 52: return "4"; case 53: return "5"; case 54: return "6"; case 55: return "7"; 
	case 56: return "8"; case 57: return "9"; case 65: return "A"; case 66: return "B";
        case 67: return "C"; case 68: return "D"; case 69: return "E"; case 70: return "F";
        case 71: return "G"; case 72: return "H"; case 73: return "I"; case 74: return "J";
	case 75: return "K"; case 76: return "L"; case 77: return "M"; case 78: return "N";
        case 79: return "O"; case 80: return "P"; case 81: return "Q"; case 82: return "R";
        case 83: return "S"; case 84: return "T"; case 85: return "U"; case 86: return "V";
        case 87: return "W"; case 88: return "X"; case 89: return "Y"; case 90: return "Z";
        case 97: return "a"; case 98: return "b"; case 99: return "c"; case 100: return "d"; 
	case 101: return "e"; case 102: return "f"; case 103: return "g"; case 104: return "h";
	case 105: return "i"; case 106: return "j"; case 107: return "k"; case 108: return "l";
        case 109: return "m"; case 110: return "n"; case 111: return "o"; case 112: return "p";
	case 113: return "q"; case 114: return "r"; case 115: return "s"; case 116: return "t";
        case 117: return "u"; case 118: return "v"; case 119: return "w"; case 120: return "x";
	case 121: return "y"; case 122: return "z";
        default: return "";
    }
}

// The function to evaluate the brainf@uck code
function interpret() {
	var end: boolean = false;
	while (!end) {
		if (ipointer >= program.length) {
			break;
		}
		var op: string = program[ipointer];
		switch (op) {
			case ">":
				if (mpointer == memory.length - 1) {
					// If we tried to access memory beyond what we have just add more memory
					for (var i: number = 0; i < 5; i++) {
						memory.push(0);
					}
				}
				mpointer = mpointer + 1;
				break;
			case "<":
				if (mpointer > 0) {
					mpointer = mpointer - 1;
				}
				break;
			case "+":
				memory[mpointer] = memory[mpointer] + 1;
				break;
			case "-":
				memory[mpointer] = memory[mpointer] - 1;
				break;
			case ".":
				output = output + intToASCII(memory[mpointer]);
				break;
			case ",":
				// TODO: since the instruction , reads from stdin in most interpreters.
				break;
			case "[":
				if (memory[mpointer] != 0) { // if non zero
					astack.push(ipointer);
				} else { // Skip to matching right bracket
					var count: number = 0;
					while (true) {
						ipointer = ipointer + 1;
						if (ipointer > program.length) {
							break;
						}
						if (program[ipointer] == "[") {
							count = count + 1;
						} else if (program[ipointer] == "]") {
							if (count != 0) {
								count = count - 1;
							} else {
								break;
							}
						}
					}
				}
				break;
			case "]":
				//Pointer is automatically incremented every iteration, therefore we must decrement to get the correct value
		                ipointer = astack.pop() - 1;
				break;
			default:
				// do nothing
				break;
		}
		ipointer = ipointer + 1;
	}
}

// evuatate the brainf@ck code
interpret();
// print the text stored in output
console.log(output);`);
