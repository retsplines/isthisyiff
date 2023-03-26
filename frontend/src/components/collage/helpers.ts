import type { Axis, Point, Size, Vector } from "./types";

/**
 * Given an axis, return the opposite one.
 * 
 * @param axis 
 */
export function oppositeAxis(axis: Axis): Axis {
    return axis === 'x' ? 'y' : 'x';
}

/**
 * Add two vectors.
 * 
 * @param a 
 * @param b 
 */
export function add(a: Vector, b: Vector): Vector {
    return {
        x: a.x + b.x,
        y: a.y + b.y
    };
}

/**
 * Subtracts two vectors.
 * 
 * @param a 
 * @param b 
 */
export function subtract(a: Vector, b: Vector): Vector {
    return {
        x: a.x - b.x,
        y: a.y - b.y
    };
}

/**
 * Divides two vectors.
 * 
 * @param a 
 * @param b 
 */
export function divide(a: Vector, b: Vector): Vector {
    // If the divisor is 0 in either dimension, the result is 0 in that dimension
    return {
        x: b.x === 0 ? 0 : (a.x / b.x),
        y: b.y === 0 ? 0 : (a.y / b.y)
    };
}

/**
 * Multiplies two vectors.
 * 
 * @param a 
 * @param b 
 */
export function multiply(a: Vector, b: Vector): Vector {
    return {
        x: a.x * b.x,
        y: a.y * b.y
    };
}

/**
 * Inverts a vector.
 * 
 * @param a
 * @returns 
 */
export function invert(a: Vector): Vector {
    return multiply(a, vectorOf(-1));
}

/**
 * Returns a vector with the given value in both dimensions; or with the given two dimensions.
 * 
 * @param value 
 * @returns 
 */
export function vectorOf(a: number = 0, b: number|null = null) {
    return {
        x: a,
        y: (b !== null ? b : a)
    };
}

/**
 * Returns the magnitude of a vector.
 * 
 * @param a 
 * @returns 
 */
export function magnitude(a: Vector): number {
    return Math.sqrt(a.x * a.x + a.y * a.y);
}

/**
 * Return a vector that is a function (f) of another vector (a).
 * 
 * @param a 
 * @param f 
 * @returns 
 */
export function functionOf(a: Vector, f: (d: number, v?: Vector) => number): Vector {
    return {
        x: f(a.x, a),
        y: f(a.y, a)
    };
}