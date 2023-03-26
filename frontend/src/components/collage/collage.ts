import { Subject } from 'rxjs';
import { add, multiply, oppositeAxis, functionOf, vectorOf } from './helpers';
import { BlockContentState, type Axis, type Block, type BlockLifecycleChangeEvent, type Point, type PresentationBlock, type Side, type Size } from './types';

/**
 * Manages a collage of tiles sourced from the web service.
 * 
 * This class simply manages the layout of blocks, ensuring blocks are ready and preloaded based on the current viewport,
 * it does not manage the animation or rendering at all.
 * 
 * The shift() method should be used to move the origin within the viewport.
 */
export class Collage<Metadata=void> {

    /**
     * The size of a single block in pixels.
     * Blocks must be square, hence there is only one defined dimension.
     */
    private blockSize: number = 150;

    /**
     * The underlying block set.
     */
    private blocks: Block<Metadata>[] = [];

    /**
     * The viewport size on which the collage is being presented.
     * Typically represents the size of a HTML <canvas> element.
     */
    private viewportSize: Size = vectorOf(0);

    /**
     * The origin relative to the starting condition that marks top top-left block
     * This measures blocks, not pixels.
     */
    private blockOrigin: Point = vectorOf(0);

    /**
     * The origin in pixels at which the grid will be painted onto the canvas.
     * Changed via shift() or setOrigin()
     */
    private origin: Point = vectorOf(0);

    /**
     * The number of blocks on each axis.
     */
    private blockCounts: Size = vectorOf(0);

    /**
     * The ID of the next block to be added.
     */
    private blockId: number = 0;

    /**
     * The distance from the viewport bounds in pixels to ensure blocks cover.
     * This can be set to 0 if block images are known to be instantly available, or a higher distance for slower-loading content.
     */
    private preloadDistance: number = 75;

    /**
     * A subject that emits batches of blocks as they change lifecycle state due to internal logic.
     * These blocks can be processed by external code, their lifecycle states updated and metadata modified.
     */
    private blockLifecycleChanges: Subject<BlockLifecycleChangeEvent<Block<Metadata>>> = new Subject(); 

    /**
     * Constructor.
     * 
     * @param defaultMetadata 
     */
    constructor(private defaultBlockMetadata: Metadata) {}

    /**
     * Initialise, or reinitialise, the collage state given the block size & size of the viewport it is to be presented in.
     */
    public init(blockSize: number, viewportSize: Size) {

        // Clear all blocks
        this.blocks.length = 0;
        this.blockId = 0;

        // Reset origins
        this.blockOrigin = vectorOf(0);
        this.origin = vectorOf(0);

        // Set block size
        this.blockSize = blockSize;

        // Set the viewport size
        this.viewportSize = viewportSize;

        // Recalculate sizes
        this.blockCounts = {
            x: Math.ceil(viewportSize.x / this.blockSize),
            y: Math.ceil(viewportSize.y / this.blockSize)
        }

        // Spawn-in the initial blocks
        for (let row = 0; row < this.blockCounts.y; row ++) {
            for (let col = 0; col < this.blockCounts.x; col ++) {
                this.addBlock({
                    x: col, y: row
                });
            }
        }
        
        // Introduce any required rows or columns - the initial loadout doesn't factor-in preloading
        this.introduce();

        // Emit lifecycle changes for the initial blocks
        this.blockLifecycleChanges.next({
            blocks: this.blocks,
            newState: BlockContentState.New
        });
    }

    /**
     * Shift the viewport origin by an amount.
     */
    public shiftOrigin(size: Size, inhibitBoundsCheck = false) {
        this.setOrigin(add(this.origin, size), inhibitBoundsCheck);
    }

    /**
     * Set the viewport origin to a position.
     */
    public setOrigin(position: Point, inhibitBoundsCheck = false) {
        this.origin = position;
        if (!inhibitBoundsCheck) {
            this.checkBounds();
        }
    }

    /**
     * Get the viewport origin.
     */
    public getOrigin(): Point {
        return this.origin;
    }


    /**
     * Get the current origin of the top-left corner of the grid relative to the canvas.
     */
    public getBlockOrigin(): Point {
        return {
            x: (this.origin.x + (this.blockOrigin.x * this.blockSize)),
            y: (this.origin.y + (this.blockOrigin.y * this.blockSize)) 
        };
    }

    /**
     * Get an observable that emits when blocks undergo lifecycle changes.
     */
    public getBlockLifecycleChanges(): Subject<BlockLifecycleChangeEvent<Block<Metadata>>> {
        return this.blockLifecycleChanges;
    }

    /**
     * Change the block size.
     */
    public setBlockSize(size: number, inhibitBoundsCheck = false) {
        this.blockSize = size;
        if (!inhibitBoundsCheck) {
            this.checkBounds();
        }
    }

    /**
     * Return the current block size.
     */
    public getBlockSize(): number {
        return this.blockSize;
    }

    /**
     * Return the current viewport size in pixels.
     */
    public getViewportSize(): Size {
        return this.viewportSize;
    }

    /**
     * Return the inner collage size in pixels.
     */
    public getCollageSize(): Size {
        return multiply(this.blockCounts, vectorOf(this.blockSize));
    }

    /**
     * Get blocks ready for presentation in the current viewport.
     */
    public present(): PresentationBlock<Metadata>[] {
        return this.blocks.map(block => {

            // Calculate the pixel position
            const pixelPosition: Point = add(
                multiply(block.position, vectorOf(this.blockSize)),
                this.origin
            );
            
            // Is the block on-screen now?
            const isOnScreen = ! (pixelPosition.x + this.blockSize < 0 || 
                pixelPosition.x > this.viewportSize.x ||
                pixelPosition.y + this.blockSize < 0 ||
                pixelPosition.y > this.viewportSize.y);

            return {
                pixelPosition,
                isOnScreen,
                block
            };
        });
    }

    /**
     * Spawn a block at the specified grid position.
     * 
     * @param x 
     * @param y 
     */
    private addBlock(position: Point): Block<Metadata> {

        const newBlock: Block<Metadata> = {
            position,
            id: this.blockId ++,
            state: BlockContentState.New,
            sourceImage: null,
            metadata: {...this.defaultBlockMetadata}
        };

        this.blocks.push(newBlock);
        return newBlock;
    }

    /**
     * Check if any blocks need to be added or removed.
     */
    private checkBounds() {

        // Add any new rows/columns
        let addedBlocks: Block<Metadata>[] = this.introduce();

        // Remove any old rows/columns
        let removedBlocks: Block<Metadata>[] = this.remove();

        // If any blocks were added then immediately removed, don't announce them at all
        const addedThenRemoved = addedBlocks.filter(Set.prototype.has, new Set(removedBlocks));
        if (addedThenRemoved.length > 0) {
            addedBlocks = addedBlocks.filter(addedBlock => !addedThenRemoved.includes(addedBlock));
            removedBlocks = removedBlocks.filter(removedBlock => !addedThenRemoved.includes(removedBlock));
        }

        // Emit these new blocks for processing
        if (addedBlocks.length > 0) {
            this.blockLifecycleChanges.next({
                blocks: addedBlocks,
                newState: BlockContentState.New
            });
        }

        // Emit removed blocks for processing
        if (removedBlocks.length > 0) {
            this.blockLifecycleChanges.next({
                blocks: removedBlocks,
                newState: BlockContentState.Removed
            });
        }
    }

    /**
     * Add any rows or columns of blocks where needed.
     * Returns any added blocks for post-processing.
     */
    private introduce(): Block<Metadata>[] {

        // Collect removed blocks
        const introducedBlocks: Block<Metadata>[] = [];

        // Re-perform the process until no more blocks need to be added
        let lastCycleIntroducedCount = 0;
        
        do {

            lastCycleIntroducedCount = introducedBlocks.length;
            
            // Calculate the current origin of the grid relative to the canvas
            const gridPixelOrigin: Point = {
                x: (this.origin.x + (this.blockOrigin.x * this.blockSize)),
                y: (this.origin.y + (this.blockOrigin.y * this.blockSize)) 
            };
            
            // Calculate the size of the grid
            const gridSize: Size = multiply(this.blockCounts, vectorOf(this.blockSize));

            // New columns needed right?
            if (gridPixelOrigin.x + gridSize.x < (this.viewportSize.x + this.preloadDistance)) {
                introducedBlocks.push(...this.extend('x', 'end'));
            }
            
            // New columns needed left?
            if (gridPixelOrigin.x > -this.preloadDistance) {
                introducedBlocks.push(...this.extend('x', 'start'));
            }
            
            // New rows needed bottom?
            if (gridPixelOrigin.y + gridSize.y < (this.viewportSize.y + this.preloadDistance)) {
                introducedBlocks.push(...this.extend('y', 'end'));
            }

            // New rows needed top?
            if (gridPixelOrigin.y > -this.preloadDistance) {
                introducedBlocks.push(...this.extend('y', 'start'));
            }

        } while (introducedBlocks.length !== lastCycleIntroducedCount);
        
        return introducedBlocks;
    }

    /**
     * Remove rows or columns of blocks where needed.
     * Returns any removed blocks for post-processing.
     */
    private remove(): Block<Metadata>[] {
        
        // Collect removed blocks
        const removedBlocks: Block<Metadata>[] = [];

        // Re-perform the process until no more blocks need to be removed
        let lastCycleRemovedCount = 0;
        
        do {
            lastCycleRemovedCount = removedBlocks.length;

            // Calculate the current origin of the grid relative to the canvas
            const gridPixelOrigin: Point = {
                x: (this.origin.x + (this.blockOrigin.x * this.blockSize)),
                y: (this.origin.y + (this.blockOrigin.y * this.blockSize)) 
            };
            
            // Calculate the size of the grid
            const gridSize: Size = multiply(this.blockCounts, vectorOf(this.blockSize));

            // Remove rows from the bottom?
            if (gridPixelOrigin.y + gridSize.y > (this.viewportSize.y + this.blockSize * 2)) {
                removedBlocks.push(...this.shrink('y', 'end'));
            }

            if (gridPixelOrigin.y < -(this.blockSize * 2)) {
                removedBlocks.push(...this.shrink('y', 'start'));
            }

            if (gridPixelOrigin.x + gridSize.x > (this.viewportSize.x + this.blockSize * 2)) {
                removedBlocks.push(...this.shrink('x', 'end'));
            }
            
            if (gridPixelOrigin.x < -(this.blockSize * 2)) {
                removedBlocks.push(...this.shrink('x', 'start'));
            }

        } while (removedBlocks.length !== lastCycleRemovedCount);
            
        return removedBlocks;
    }

    /**
     * Add a row or column to the start or end of the grid.
     * Returns any added blocks for post-processing.
     * 
     * @param axis 
     * @param side 
     */
    private extend(axis: Axis, side: Side): Block<Metadata>[] {

        const introducedBlocks: Block<Metadata>[] = [];

        // For each block on the opposite axis
        for (let p = 0; p < this.blockCounts[oppositeAxis(axis)]; p ++) {

            const newBlockPosition: Point = {

                // Is this the axis we're actually adding to?
                x: (axis === 'x') ? 

                    // Yes - We're adding a column of blocks
                    (side === 'start' ? this.blockOrigin.x - 1 : this.blockOrigin.x + this.blockCounts.x) :

                    // No - We're adding a row of blocks
                    this.blockOrigin.x + p,

                y: (axis === 'y') ?

                    // We're adding a row of blocks
                    (side === 'start' ? this.blockOrigin.y - 1 : this.blockOrigin.y + this.blockCounts.y):

                    // We're adding a column of blocks
                    this.blockOrigin.y + p

            };

            introducedBlocks.push(this.addBlock(newBlockPosition));
        }

        // Bigger in this dimension now
        this.blockCounts[axis] ++;

        // Origin moves if blocks added to the start of either axis
        if (side === 'start') {
            this.blockOrigin[axis] --;
        }

        console.debug(`Added ${axis === 'x' ? 'column' : 'row'} to ${side}. Origin now`, this.blockOrigin, 'block dim', this.blockCounts, 'count', this.blocks.length);

        return introducedBlocks;
    }

    /**
     * Remove a row or column at the start or end of the grid.
     * Returns any removed blocks for post-processing.
     * 
     * @param axis
     * @param side 
     */
    private shrink(axis: Axis, side: Side): Block<Metadata>[] {

        const rowOrColumnIndex = side === 'start' ?
            this.blockOrigin[axis] :
            this.blockOrigin[axis] + this.blockCounts[axis] - 1;

        // Track blocks to remove
        const blocksForRemoval: Block<Metadata>[] = [];

        // Calculate the criteria for block removal
        for (const block of this.blocks) {
            if (block.position[axis] === rowOrColumnIndex) {
                blocksForRemoval.push(block);
            }
        }

        // remove the blocks that were in the column
        for (const removedBlock of blocksForRemoval) {
            this.blocks.splice(this.blocks.indexOf(removedBlock), 1);
        }

        // Smaller in this dimension now
        this.blockCounts[axis] --;

        // Origin moves if blocks removed from the start of either axis
        if (side === 'start') {
            this.blockOrigin[axis] ++;
        }

        console.debug(`Removed ${axis === 'x' ? 'column' : 'row'} from ${side}. Origin now`, this.blockOrigin, 'block dim', this.blockCounts, 'count', this.blocks.length);

        return blocksForRemoval;
    }

}