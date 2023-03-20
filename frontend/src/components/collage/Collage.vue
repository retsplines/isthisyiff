<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { Collage } from './collage';
import { BlockContentState, type Point, type PresentationBlock, type Size, type Vector } from './types';
import { invert, multiply, subtract, vectorOf } from './helpers';
import { BlockImageDownloader } from './downloader';
import { debounce, fromEvent, interval } from 'rxjs';

const emit = defineEmits(['nextGamePlease']);

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

// Define defaults & max/mins
const maxBlockSize = 500;
const minBlockSize = 100;
const defaultBlockSize = 250;
const driftRate: Vector = {
    x: -70,
    y: -70
};

// Presentational metadata for blocks
type BlockMeta = {

    // The opacity of the block
    opacity: number,

    // The URL of the image to show in the block
    url: string | null,

    // A target UUID of a challenge to visit when the block is clicked in interactive mode
    uuid: string | null
};

// Canvas & context
const container = ref<HTMLDivElement | null>();  
const canvas = ref<HTMLCanvasElement | null>();
const context = ref<CanvasRenderingContext2D | null>();  

// The underlying managed collage layout
const collage = new Collage<BlockMeta>({
    opacity: 0,
    url: null,
    uuid: null
});

// A client for downloading block images
const blockImageDownloader = new BlockImageDownloader<BlockMeta>();

// Handle obtaining images for new blocks
collage.getBlockLifecycleChanges().subscribe(blockLifecycleChanges => {
    if (blockLifecycleChanges.newState === BlockContentState.New) {
        blockImageDownloader.assignBlocks(blockLifecycleChanges.blocks);
    }
});

// The last mouse position
let lastMousePosition: Point|null = null;

// Animation running?
const running = ref<boolean>(false);

// Are we automatically drifting?
let isDrifting = true;

// The last location at which the mouse button up/down event fired
// Only one will be set at once
let mouseUpPosition: Point|null = null;
let mouseDownPosition: Point|null = null;

// The last position that the mouse moved to while dragging
let lastDragPosition: Point|null = null;

// Keep a snapshot of the last time a frame was painted so that we can move things on the right amount each frame
let lastPaintAt: DOMHighResTimeStamp|null = null;

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
    context.value = canvas.value.getContext('2d');

    // Register for resize updates
    const resizes = fromEvent(window, 'resize');
    const debouncedResizes = resizes.pipe(
        debounce(resize => interval(100))
    );
    debouncedResizes.subscribe(resize);


    // Simulate an initial resize
    resize();

    // Showtime
    start();
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
 * Handle the mouse wheel being scrolled.
 * 
 * @param wheelEvent 
 */
function handleWheel(wheelEvent: WheelEvent) {

    if (!props.interactive) {
        return;
    }

    // Stop auto-drifting
    isDrifting = false;

    const changePixels = wheelEvent.deltaY > 0 ? 15 : -15;
    const currentBlockSize = collage.getBlockSize();

    if (currentBlockSize + changePixels < minBlockSize || currentBlockSize + changePixels > maxBlockSize) {
        return;
    }

    const factor = (currentBlockSize / (currentBlockSize + changePixels));
    collage.setBlockSize(changePixels + currentBlockSize);

    // Also shift the origin by a displacment amount so it seems like we zoom into the cursor
    const currentOrigin = collage.getOrigin();
    collage.shiftOrigin({
        x: (wheelEvent.offsetX - currentOrigin.x) * (factor - 1),
        y: (wheelEvent.offsetY - currentOrigin.y) * (factor - 1)
    });
}

/**
 * Handle a touch event.
 * 
 * @param touchEvent 
 */
function handleTouch(touchEvent: TouchEvent) {

    // Ignore events if not interactive
    if (!props.interactive) {
        return;
    }

    switch (touchEvent.type) {
        case 'touchstart':
            mouseDown({
                x: touchEvent.touches[0].clientX,
                y: touchEvent.touches[0].clientY
            });
            break;
        case 'touchend':
            mouseUp({
                x: touchEvent.touches[0].clientX,
                y: touchEvent.touches[0].clientY
            });
            break;
        case 'touchmove':
            mouseMove({
                x: touchEvent.touches[0].clientX,
                y: touchEvent.touches[0].clientY
            });
            break;
    }
}

/**
 * Handle a touch event.
 * 
 * @param mouseEvent 
 */
function handleMouse(mouseEvent: MouseEvent) {

    // Ignore events if not interactive
    if (!props.interactive) {
        return;
    }

    switch (mouseEvent.type) {
        case 'mousedown':
            mouseDown({
                x: mouseEvent.offsetX,
                y: mouseEvent.offsetY
            });
            break;
        case 'mouseup':
            mouseUp({
                x: mouseEvent.offsetX,
                y: mouseEvent.offsetY
            });
            break;
        case 'mousemove':
            mouseMove({
                x: mouseEvent.offsetX,
                y: mouseEvent.offsetY
            });
            break;
    }
}

/**
 * Mouse down fired here.
 */
function mouseDown(position: Point) {

    // Not possible if control isn't allowed
    if (!props.interactive) {
        return;
    }

    mouseDownPosition = position;
    mouseUpPosition = null;
    isDrifting = false;
}


/**
 * Mouse up fired here.
 */
function mouseUp(position: Point) {

    // Not possible if control isn't allowed
    if (!props.interactive) {
        return;
    }

    if (!lastDragPosition) {

        // No dragging took place, so this was a click
        // Find the block that was clicked
        const clickedBlocks: PresentationBlock<BlockMeta>[] = collage.present().filter(presentationBlock => (
            position.x >= presentationBlock.pixelPosition.x &&
            position.x <= presentationBlock.pixelPosition.x + collage.getBlockSize() &&
            position.y >= presentationBlock.pixelPosition.y &&
            position.y <= presentationBlock.pixelPosition.y + collage.getBlockSize()
        ));

        if (clickedBlocks.length === 0) {
            // Nothing clicked
            return;
        }

        emit('nextGamePlease', clickedBlocks[0].block.metadata.uuid);
    }

    mouseUpPosition = position;
    mouseDownPosition = null;
    lastDragPosition = null;
    isDrifting = false;
}

/**
 * Mouse move fired.
 */
function mouseMove(position: Point) {

    lastMousePosition = {
        x: position.x,
        y: position.y
    };

    if (mouseDownPosition) {

        if (!lastDragPosition) {
            lastDragPosition = position;
        }

        // Mouse is down, we're dragging
        const distanceDragged: Size = subtract(lastDragPosition, position);
        if (distanceDragged.x === 0 && distanceDragged.y === 0) {
            return;
        }

        collage.shiftOrigin(invert(distanceDragged));

        // Reset the drag start position
        lastDragPosition = position;
    }
  
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
function update(paintedAt: DOMHighResTimeStamp) {

    // Stopped already?
    if (!running.value) {
        return;
    }

    // First time around?
    if (lastPaintAt === null) {
        lastPaintAt = paintedAt;
    }

    // Calculate how much time passed
    const sinceLast = paintedAt - lastPaintAt;
    
    // Shift an appropriate amount for the passed time
    if (isDrifting) {
        collage.shiftOrigin(multiply(driftRate, vectorOf(sinceLast / 1000)));
    }

    // Redraw
    draw(false);
    lastPaintAt = paintedAt;
    
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
    
    start();
}

/**
 * Draw the state of the collage to a canvas.
 */
function draw(drawDebugLines: boolean = false) {
    
    // Only continue if mounting was successful
    if (!context.value) {
        return;
    }
    
    context.value.clearRect(0, 0, context.value.canvas.width, context.value.canvas.height);

    // A block that should be highlighted at the end, once all blocks are drawn
    let highlightedBlock: PresentationBlock<BlockMeta>|null = null;

    // The current block size
    const currentBlockSize = collage.getBlockSize();

    for (const presentationBlock of collage.present()) {

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
            context.value.fillStyle = 'grey';
            context.value.strokeStyle = 'black';
            context.value.fillRect(presentationBlock.pixelPosition.x, presentationBlock.pixelPosition.y, currentBlockSize, currentBlockSize);
            context.value.beginPath();
            context.value.rect(presentationBlock.pixelPosition.x, presentationBlock.pixelPosition.y, currentBlockSize, currentBlockSize);
            context.value.stroke();
        }

        // Draw the image if it's available
        if (presentationBlock.block.state === BlockContentState.Ready && presentationBlock.block.sourceImage) {

            if (presentationBlock.block.metadata.opacity < 1) {
                context.value.globalAlpha = Math.min(1, presentationBlock.block.metadata.opacity);
            }

            context.value.drawImage( 
                presentationBlock.block.sourceImage,
                presentationBlock.pixelPosition.x - 1, presentationBlock.pixelPosition.y - 1,
                currentBlockSize + 1, currentBlockSize + 1
            );

            if (presentationBlock.block.metadata.opacity < 1) {
                context.value.globalAlpha = 1;
                presentationBlock.block.metadata.opacity += 0.025;
            }
        }

        // Draw a box around the block if we're interactive and it's moused-over
        if (props.interactive && lastMousePosition) {
            if (lastMousePosition.x >= presentationBlock.pixelPosition.x &&
                lastMousePosition.x <= presentationBlock.pixelPosition.x + currentBlockSize &&
                lastMousePosition.y >= presentationBlock.pixelPosition.y &&
                lastMousePosition.y <= presentationBlock.pixelPosition.y + currentBlockSize
            ) {
                highlightedBlock = presentationBlock;
            }
        }

        if (drawDebugLines) {
            context.value.fillStyle = 'grey';
            context.value.strokeStyle = 'black';
            context.value.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + 10, presentationBlock.pixelPosition.y + 10);
            context.value.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + currentBlockSize - 10, presentationBlock.pixelPosition.y + 10);
            context.value.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + 10, presentationBlock.pixelPosition.y + currentBlockSize - 10);
            context.value.strokeText(presentationBlock.block.id.toString(10), presentationBlock.pixelPosition.x + currentBlockSize - 10, presentationBlock.pixelPosition.y + currentBlockSize - 10);
            context.value.strokeText(`${presentationBlock.block.id}`, presentationBlock.pixelPosition.x + currentBlockSize / 2, presentationBlock.pixelPosition.y + currentBlockSize / 2);
            context.value.stroke();
        }
    }

    // Draw a box around a highlighted block?
    if (highlightedBlock) {
        context.value.strokeStyle = 'white';
        context.value.lineWidth = 4;
        context.value.beginPath();
        context.value.rect(highlightedBlock.pixelPosition.x, highlightedBlock.pixelPosition.y, currentBlockSize - 3, currentBlockSize - 3);
        context.value.stroke();
    }
}

</script>

<style scoped="true" lang="scss">
    #canvas-container {
        width: 100%;
        height: 100%;
        overflow: hidden;
        canvas {
            position: absolute;
        }
    }
</style>

<template>
    <div id="canvas-container" ref="container">
        <canvas
            ref="canvas"
            @mousemove="handleMouse"
            @mousedown="handleMouse"
            @mouseup="handleMouse"
            @touchstart="handleTouch"
            @touchmove="handleTouch"
            @touchend="handleTouch"
            @wheel="handleWheel"
        ></canvas>
    </div>
</template>
