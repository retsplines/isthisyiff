import type { ImageRef } from "./image-ref"
import type { Rating } from "./rating"

/**
 * The shape of a "challenge" API response.
 */
export type Challenge = {
    uuid: string,
    crop: ImageRef
};
