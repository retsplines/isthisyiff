import type { ImageRef } from "./image-ref"

/**
 * The shape of a "preview" API response.
 */
export type Previews = {
    previews: PreviewItem[],
};

/**
 * A single preview.
 */
export type PreviewItem = {
    crop: ImageRef,
    uuid: string
};
