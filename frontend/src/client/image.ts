/**
 * Preload an image, returning a function that resolves once the image is loaded.
 */
export function preloadImage(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
        let img = new Image()
        img.onload = () => resolve();
        img.onerror = reject;
        img.src = url;
    });
}
