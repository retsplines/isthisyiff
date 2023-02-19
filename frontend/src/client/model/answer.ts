import type { ImageRef } from "./image-ref"
import type { Rating } from "./rating"

/**
 * The shape of an "answer" API response.
 */
export type Answer = {
    uuid: string,
    source: {
        id: number,
        url: string,
        fav_count: number,
        score: number
    },
    result: {
        actual: Rating,
        guess: Rating
    },
    orig: ImageRef,
    crop: ImageRef & {
        position: {
            left: number,
            top: number
        }
    },
    statistics: {
        correct_guesses: number,
        incorrect_guesses: number
    }
};
