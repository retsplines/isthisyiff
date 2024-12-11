<script setup lang="ts">

import { ref, onMounted, watch, onUnmounted } from 'vue'
import { Collage } from './collage';
import { BlockContentState, type Point, type PresentationBlock, type Size, type Vector } from './types';
import { invert, multiply, divide, add, subtract, vectorOf, functionOf } from './helpers';
import { BlockImageDownloader } from './downloader';
import { debounce, fromEvent, interval } from 'rxjs';
import type { FullGestureState } from '@vueuse/gesture';

const emit = defineEmits(['nextGamePlease']);

// Presentational metadata for blocks
type BlockMeta = {

    // The opacity of the block
    opacity: number,

    // The URL of the image to show in the block
    url: string | null,

    // A target UUID of a challenge to visit when the block is clicked in interactive mode
    uuid: string | null,

    // Prescaled versions of the block image to avoid re-scaling each draw
    prescaledImageCanvas: HTMLCanvasElement | null,
    prescaledForBlockSize: number | null
};

/**
 * Define the configurable component properties.
 */
const props = withDefaults(defineProps<{

    /**
     * Whether mouse control is allowed.
     */
    interactive: boolean

}>(), {
    // Defaults
    interactive: false
});


// Debug mode doesn't load images, just draws placeholders
const isDebugging = false;

// Define defaults & max/mins
const maxZoomLevel = 3;
const minZoomLevel = 1;
const defaultBlockSize = 150;

// The current drift rate
let driftRate: Vector = {
    x: 0,
    y: 0
};

// Canvas & context
const container = ref<HTMLDivElement | null>();  
const canvas = ref<HTMLCanvasElement | null>();
const context = ref<CanvasRenderingContext2D | null>();  

// The underlying managed collage layout
const collage = new Collage<BlockMeta>({
    opacity: 0,
    url: null,
    uuid: null,
    prescaledImageCanvas: null,
    prescaledForBlockSize: null
});

// A client for downloading block images
const blockImageDownloader = new BlockImageDownloader<BlockMeta>();

// Handle obtaining images for new blocks
collage.getBlockLifecycleChanges().subscribe(blockLifecycleChanges => {
    if (!isDebugging && blockLifecycleChanges.newState === BlockContentState.New) {
        blockImageDownloader.assignBlocks(blockLifecycleChanges.blocks);
    }
});

// The zoom level we're currently at
let zoomLevel = 1;

// The last mouse position
let lastMousePosition: Point|null = null;
let lastMousePositionTime: Date|null = null;

// Animation running?
const running = ref<boolean>(false);

// Are we automatically drifting?
let isDrifting = true;

// Keep a snapshot of the last time a frame was painted
let lastPaintAt: number|null = null;

// Keep a reference to the last animation frame request
let animationFrameHandle: number|null = null;

/**
 * Component mounted.
 */
onMounted(() => {

    if (!canvas.value) {
        return;
    }

    // Find the size of the canvas and initialise the view
    context.value = canvas.value.getContext('2d', { alpha: false });

    // Register for resize updates
    const resizes = fromEvent(window, 'resize');
    const debouncedResizes = resizes.pipe(
        debounce(resize => interval(100))
    );
    debouncedResizes.subscribe(resize);

    // Simulate an initial resize
    setTimeout(() => {

        // Initial resize
        resize();

        // Showtime
        start();

    });
    
});

/**
 * Component unmounted.
 */
onUnmounted(() => {
    stop();
    window.removeEventListener('resize', resize);
});

/**
 * Watch for control being enabled and disabled.
 */// When an answer is set, fade it in
watch(props, (newProps) => {
    if (!newProps.interactive) {
        isDrifting = true;
        collage.setBlockSize(defaultBlockSize);
    }
});

/**
 * Return the position of a view coordinate in the whole collage.
 */
function viewToCollage(position: Point): Point {
    return subtract(position, collage.getOrigin());
}

/**
 * Set the view to a requested zoom level (ratio to scale defaultBlockSize by).
 * 
 * @param delta 
 */
function zoom(requestedLevel: number, zoomAtPoint: Point|null = null) {

    if (requestedLevel < minZoomLevel) {
        console.warn(`Requested zoom level ${requestedLevel} is too low`);
        return;
    }
    if (requestedLevel > maxZoomLevel) {
        console.warn(`Requested zoom level ${requestedLevel} is too high`);
        return;
    }

    // Compute the scale difference between zoom levels
    const zoomFactor = requestedLevel / zoomLevel;

    // Update the new zoom level
    zoomLevel = requestedLevel;

    // If a reference origin wasn't provided, just use the centre of the view
    const referenceOrigin = zoomAtPoint ? zoomAtPoint : divide(collage.getViewportSize(), vectorOf(2)); 

    // Capture the current mouse/touch position in world-space
    const currentCollagePosition = viewToCollage(referenceOrigin);

    // Compute where this will be after scaling
    const collagePositionAfterScaling = multiply(currentCollagePosition, vectorOf(zoomFactor));

    // Compute the difference of these
    const collagePositionDifference = subtract(currentCollagePosition, collagePositionAfterScaling);

    // Perform the zoom
    const newBlockSize = defaultBlockSize * zoomLevel;
    collage.setBlockSize(newBlockSize, true);

    // Apply the changes, only calculating bounds after both are done
    collage.shiftOrigin(collagePositionDifference);
}

/**
 * Handle a drag event
 * 
 * @param mouseEvent 
 */
 function handleDrag(mouseState: FullGestureState<'drag'>) {

    // Ignore events if not interactive
    if (!props.interactive || !canvas.value) {
        return;
    }

    // If multiple touches are active, they're likely pinching
    if (window.TouchEvent && mouseState.event instanceof TouchEvent && mouseState.event.touches.length > 1) {
        return;
    }

    // Mouse is down, we're dragging
    const distanceDragged: Size = invert(vectorOf(...mouseState.delta));

    // Last event in the drag?
    if(mouseState.last) {

        // Was this actually just a tap/click?
        if (mouseState.distance === 0) {

            // Adjust the mouse position
            const canvasMouse = subtract(vectorOf(...mouseState.xy), vectorOf(canvas.value.getBoundingClientRect().left, canvas.value.getBoundingClientRect().top));
            
            // Clicked - find the block at this position
            const clickedBlocks = collage.present().filter(presentationBlock =>
                canvasMouse.x >= presentationBlock.pixelPosition.x &&
                canvasMouse.y >= presentationBlock.pixelPosition.y &&
                canvasMouse.x <= (presentationBlock.pixelPosition.x + collage.getBlockSize()) &&
                canvasMouse.y <= (presentationBlock.pixelPosition.y + collage.getBlockSize())
            );

            if (clickedBlocks.length > 0) {
                emit('nextGamePlease', clickedBlocks[0].block.metadata.uuid);
            }

        } else {
            driftRate = multiply(vectorOf(...mouseState.velocities), vectorOf(300));
        }
    }

    collage.shiftOrigin(invert(distanceDragged));
}

/**
* Handle a pinch event.
* 
* @param mouseEvent 
*/
function handlePinch(pinchState: FullGestureState<'pinch'>) {

    // Ignore events if not interactive
    if (!props.interactive) {
        return;
    }

    zoom(zoomLevel * (pinchState.delta[0] > 0 ? 1.05 : 0.95), vectorOf(...pinchState.origin));

    if (pinchState.event) {
        pinchState.event.preventDefault();
        pinchState.event.stopPropagation();
    }

    return false;
}

/**
 * Handle the mouse wheel being scrolled.
 * 
 * @param wheelEvent 
 */
function handleWheel(wheelState: FullGestureState<'wheel'>) {

    if (!props.interactive || !(wheelState.event instanceof WheelEvent)) {
        return;
    }

    if (wheelState.event.offsetX === 0 && wheelState.event.offsetY === 0) {
        return;
    }

    const changeBy = wheelState.movement[1] < 0 ? 1.05 : 0.95;
    zoom(zoomLevel * changeBy, vectorOf(wheelState.event.offsetX, wheelState.event.offsetY));
    
    return false;
}

/**
 * Mouse moved over the view.
 * 
 * @param wheelEvent 
 */
function handleMove(mouseState: FullGestureState<'move'>) {

    // Ignore events if not interactive
    if (!props.interactive || !canvas.value) {
        return;
    }

    // Adjust the mouse position
    const canvasMouse = subtract(
        vectorOf(...mouseState.xy),
        vectorOf(canvas.value.getBoundingClientRect().left, canvas.value.getBoundingClientRect().top)
    );

    lastMousePosition = canvasMouse;
    lastMousePositionTime = new Date();
}

/**
 * Start updating.
 */
function start() {
    // Start 
    running.value = true;
    requestAnimationFrame(update);
}

/**
 * Stop updating, if we are indeed updating.
 */
function stop() {

    // Cancel animation frame updates
    if (animationFrameHandle !== null) {
        cancelAnimationFrame(animationFrameHandle);
    }

    running.value = false;
}

/**
 * Update the view.
 */
function update(now: DOMHighResTimeStamp) {

    // Stopped already?
    if (!running.value) {
        return;
    }

    // First time around?
    if (lastPaintAt === null) {
        lastPaintAt = now;
    }

    const paintDelta = now - lastPaintAt;

    // Prevent unnecessary redraws
    if (paintDelta === 0) {
        // Re-request an update
        animationFrameHandle = requestAnimationFrame(update);
        return;
    }

    // Cubically reduce the drift rate
    if (driftRate.x !== 0 || driftRate.y !== 0) {
        driftRate = functionOf(driftRate, d => Math.floor(Math.abs(d) < 25 ? 0 : d * 0.95));
    }

    // Shift an appropriate amount for the passed time
    if (isDrifting) {
        collage.shiftOrigin(multiply(driftRate, vectorOf(paintDelta / 1000)));
    }

    // Always redraw
    draw(isDebugging);
    lastPaintAt = now;


    // Re-request an update
    animationFrameHandle = requestAnimationFrame(update);
}

/**
 * Resize the canvas to fit.
 */
function resize() {
    
    // Only continue if mounting was successful
    if (!context.value || !canvas.value || !container.value) {
        return;
    }

    stop();

    // Capture the old size
    const oldWidth = canvas.value.width;
    const oldHeight = canvas.value.height;

    // Set the new size
    canvas.value.width = container.value.clientWidth;
    canvas.value.height = container.value.clientHeight;

    // Did the size change?
    if (oldWidth !== canvas.value.width || oldHeight !== canvas.value.height) {
        console.debug(`Canvas container size adjusted to ${canvas.value.width} x ${canvas.value.height}`);
        collage.init(defaultBlockSize, {
            x: canvas.value.width,
            y: canvas.value.height
        });
    }

    // Zoom to 1x
    zoom(1);
    start();
}

/**
 * Draw the state of the collage to a canvas.
 */
function draw(drawDebugLines: boolean = false) {
    
    // Only continue if mounting was successful
    const resolvedContext = context.value;
    if (!resolvedContext) {
        return;
    }

    // The current block size
    const currentBlockSize = collage.getBlockSize();
    
    // The draw time now
    const drawTime = new Date();

    // Time since mouse movement
    const sinceMouseMove = drawTime.getTime() - (lastMousePositionTime ? lastMousePositionTime.getTime() : 0);
    
    // A block that should be highlighted at the end, once all blocks are drawn
    let highlightedBlock: PresentationBlock<BlockMeta>|null = null;
    const blocksToDraw = collage.present();

    // Clear view
    resolvedContext.clearRect(0, 0, resolvedContext.canvas.width, resolvedContext.canvas.height);

    // Track an index throughout
    let blockIndex = -1;

    for (const presentationBlock of blocksToDraw) {

        blockIndex ++;

        // Do we need to draw this block?
        if (!presentationBlock.isOnScreen) {
            
            // If the block is still off-screen, but already ready, no need to ramp opacity up
            if (presentationBlock.block.state === BlockContentState.Ready) {
                presentationBlock.block.metadata.opacity = 1;
            }

            // No point doing anything with this block - it's not visible yet/anymore
            continue;
        }
 
        if (drawDebugLines) {
            resolvedContext.beginPath();
            resolvedContext.fillStyle = blockIndex % 2 == 0 ? 'grey' : 'white';
            resolvedContext.strokeStyle = 'black';
            resolvedContext.lineWidth = 1;
            resolvedContext.fillRect(presentationBlock.pixelPosition.x, presentationBlock.pixelPosition.y, currentBlockSize, currentBlockSize);
            resolvedContext.rect(presentationBlock.pixelPosition.x, presentationBlock.pixelPosition.y, currentBlockSize, currentBlockSize);
            resolvedContext.stroke();
        }

        // Draw the image if it's available
        if (presentationBlock.block.state === BlockContentState.Ready && presentationBlock.block.sourceImage) {

            if (presentationBlock.block.metadata.opacity < 1) {
                resolvedContext.globalAlpha = Math.min(1, presentationBlock.block.metadata.opacity);
            }

            resolvedContext.drawImage( 
                presentationBlock.block.sourceImage,
                presentationBlock.pixelPosition.x - 1, presentationBlock.pixelPosition.y - 1,
                currentBlockSize + 1, currentBlockSize + 1
            );

            if (presentationBlock.block.metadata.opacity < 1) {
                resolvedContext.globalAlpha = 1;
                presentationBlock.block.metadata.opacity += 0.025;
            }
        }

        // Draw a box around the block if we're interactive and it's moused-over
        if (props.interactive && sinceMouseMove < 250 && lastMousePosition) {
            if (lastMousePosition.x >= presentationBlock.pixelPosition.x &&
                lastMousePosition.x <= presentationBlock.pixelPosition.x + currentBlockSize &&
                lastMousePosition.y >= presentationBlock.pixelPosition.y &&
                lastMousePosition.y <= presentationBlock.pixelPosition.y + currentBlockSize
            ) {
                highlightedBlock = presentationBlock;
            }
        }

        if (drawDebugLines) {
            resolvedContext.strokeStyle = 'black';
            resolvedContext.lineWidth = 1;
            resolvedContext.beginPath();
            resolvedContext.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + 15, presentationBlock.pixelPosition.y + 15);
            resolvedContext.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + currentBlockSize - 25, presentationBlock.pixelPosition.y + 15);
            resolvedContext.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + 15, presentationBlock.pixelPosition.y + currentBlockSize - 15);
            resolvedContext.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + currentBlockSize - 25, presentationBlock.pixelPosition.y + currentBlockSize - 15);
            resolvedContext.stroke();
        }
    }

    // Draw a box around a highlighted block?
    if (highlightedBlock) {
        resolvedContext.beginPath();
        resolvedContext.strokeStyle = 'white';
        resolvedContext.lineWidth = 4;
        resolvedContext.rect(highlightedBlock.pixelPosition.x, highlightedBlock.pixelPosition.y, currentBlockSize - 3, currentBlockSize - 3);
        resolvedContext.stroke();
    }

    // Mark the centre of the collage
    if (drawDebugLines) {
        // Collage full size
        const collageSize = collage.getCollageSize();
        const collageCentre = add(multiply(collageSize, vectorOf(0.5)), collage.getBlockOrigin());
        resolvedContext.beginPath();
            resolvedContext.fillStyle = 'red';
            resolvedContext.beginPath();
            resolvedContext.fillRect(collageCentre.x - 5, collageCentre.y - 5, 10, 10);
            resolvedContext.stroke();
    }
}

function flick(x: number, y: number) {
    driftRate = vectorOf(x, y);
};

defineExpose({
    flick
});

</script>

<style scoped="true" lang="scss">
    #canvas-container {
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: var(--ity-white);
        canvas {
            position: absolute;
        }
    }
</style>

<template>
    <div id="canvas-container" ref="container">
        <canvas
            ref="canvas"
            v-move="handleMove"
            v-wheel="handleWheel"
            v-drag="handleDrag"
            v-pinch="handlePinch"
        ></canvas>
    </div>
</template>
