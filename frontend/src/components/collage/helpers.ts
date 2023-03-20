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
