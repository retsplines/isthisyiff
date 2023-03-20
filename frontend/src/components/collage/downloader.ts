import { GameClient } from "@/client/game";
import type { PreviewItem, Previews } from "@/client/model/preview";
import { BlockContentState, type Block } from "./types";

/**
 * A type describing block metadata containing a URL & UUID.
 */
export type BasicBlockMetadata = {
    url: string | null,
    uuid: string | null
};

/**
 * Assigns URLs and downloads images for blocks.
 */
export class BlockImageDownloader<BlockMetadata extends BasicBlockMetadata> {

    /**
     * The number of previews to request at once.
     */
    private readonly previewBatchSize = 250;

    /**
     * A pool of available preview URLs for assignment.
     * Note that the previews in this pool have not yet had content downloaded, they're just URL references & sizes.
     */
    private previewPool: PreviewItem[] = [];
    
    /**
     * A promise when a pending refillPool request is waiting.
     * This prevents concurrent refill requests from stacking up.
     */
    private pendingPoolRefillRequest: Promise<Previews>|null = null;

    /**
     * Request a batch of previews, filling the previewPool.
     */
    private async refillPool() {

        // Request already pending? wait for that one instead
        if (this.pendingPoolRefillRequest) {
            console.debug('Awaiting an ongoing refill request instead of issuing a new one');
            await this.pendingPoolRefillRequest;
            return;
        }

        // Get previews
        this.pendingPoolRefillRequest = GameClient.getPreviews(this.previewBatchSize);
        this.previewPool.push(...((await this.pendingPoolRefillRequest).previews));

        // No longer waiting
        this.pendingPoolRefillRequest = null;
    }

    /**
     * Given a set of blocks, assign a URL and start downloading.
     */
    public async assignBlocks(blocks: Block<BlockMetadata>[]) {

        // None to process?
        if (blocks.length === 0) {
            return;
        }

        try {

            // Obtain enough URLs to satisfy this request
            while (this.previewPool.length < blocks.length) {
                console.debug(`Only ${this.previewPool.length} previews remaining in pool, requesting ${this.previewBatchSize} more`);
                await this.refillPool();
            }

            // Use a preview for each block
            for (const block of blocks) {

                // Any previews left?
                const nextPreview = this.previewPool.shift();
                if (!nextPreview) {
                    // No more previews left - this shouldn't happen generally
                    // However, if consecutive assignBlocks() calls deplete the pool very fast, it could
                    throw Error(`Empty preview pool - wanted to satisfy ${blocks.length} blocks`);
                }

                // Start the download...
                block.metadata.url = nextPreview.crop.url;
                block.metadata.uuid = nextPreview.uuid;

                // Don't await the download so that we may obtain many images in parallel
                this.downloadImage(block).then(() => {});
            }
            
            console.debug(`Assigned ${blocks.length} blocks, ${this.previewPool.length} previews remaining in pool`);

        } catch (assignError) {
            // These blocks are all now Errored
            for (const block of blocks) {
                block.state = BlockContentState.Errored;
            }
        }
    }

    /**
     * Start a download for an image.
     */
    private async downloadImage(forBlock: Block<BlockMetadata>) {

        // Can't download without a URL
        if (!forBlock.metadata.url) {
            return;
        }

        // Set the block state
        forBlock.state = BlockContentState.Downloading;

        // Wait for the download
        const imageJpegData = await fetch(forBlock.metadata.url);

        // Create an image form the JPEG data
        forBlock.sourceImage = new Image();

        // When the image loads, set it 
        forBlock.sourceImage.onload = () => {
            forBlock.state = BlockContentState.Ready;
        };

        // Set the image URL to an Object URL reference to the downloaded blob
        forBlock.sourceImage.src = URL.createObjectURL(await imageJpegData.blob());
    }

}

