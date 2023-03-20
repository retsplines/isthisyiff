import type { ImageRef } from "./image-ref"

/**
 * The shape of a "challenge" API response.
 */
export type Challenge = {
    uuid: string,
    crop: ImageRef
};
