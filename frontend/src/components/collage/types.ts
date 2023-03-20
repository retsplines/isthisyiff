/**
 * Describes the content loading state of a block.
 */
export enum BlockContentState {

    // Brand new, with no URL even requested
    New = 'new',

    // Content for this block is being downloaded
    Downloading = 'downloading',

    // Content has been set, the block is ready for presentation
    Ready = 'ready',
    
    // Removed (no longer needed, and associated resources may be freed)
    Removed = 'removed',

    // Content had a problem downloading
    // This state stops infinite retrys slamming the backend owo
    Errored = 'errored'
};

/**
 * Specifies an axis of 2D space.
 */
export type Axis = 'x' | 'y';

/**
 * Specifies the start or end of an axis.
 */
export type Side = 'start' | 'end';

/**
 * A general 2-vector.
 */
export type Vector = {
    [key in Axis]: number
};

/**
 * A position in 2D space.
 */
export type Point = Vector;

/**
 * The size of some 2D object.
 */
export type Size = Vector;

/**
 * A block within the canvas space.
 */
export type Block<MetadataType = void> = { 

    // The position of the block in the grid, denoted in block numbers not pixels
    position: Point,

    // The state of the blocks' content
    state: BlockContentState,

    // The image content downloaded for this block
    sourceImage: HTMLImageElement | null,

    // A unique incremental ID
    id: number,

    // Any metadata associated with the block, for example presentational characteristics
    metadata: MetadataType;
};

/**
 * A presentation block, wrapped with information required to draw the block in a given frame.
 */
export type PresentationBlock<MetadataType> = {
    
    // The inner block
    block: Block<MetadataType>,

    // The pixel location at which to draw the block
    pixelPosition: Point,

    // Whether the block is on-screen currently or not
    isOnScreen: boolean

};

/**
 * An event representing a change in lifecycle state for one or more blocks.
 */
export type BlockLifecycleChangeEvent<B> = {

    // Affected blocks
    blocks: B[],

    // The lifecycle state these blocks transitioned into
    newState: BlockContentState

};