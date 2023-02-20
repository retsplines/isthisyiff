<script setup lang="ts">
import type { Answer } from '@/client/model/answer';
import type { Challenge } from '@/client/model/challenge';
import { ref, watch, type CSSProperties } from 'vue';

const props = defineProps<{
    challenge: Challenge,
    answer: Answer | null
}>();

const artboxStyle = ref<CSSProperties>({
    backgroundImage: `url('${props.challenge.crop.url}')`
});

// When an answer is set, fade it in
watch(props, (newProps) => {
    if (newProps.answer) {
        artboxStyle.value.backgroundImage = `url('${newProps.answer.orig.url}')`;
    }
});

function goToPost() {
    if (props.answer) {
        window.open(props.answer.source.url);
    }
}

</script>

<style scoped="true" lang="scss">

.artbox {
    transform: translate3d(0, 0, 0);
    transition: background-image 0.75s ease;
    background-repeat: no-repeat;
    background-position: center center;
    background-size: contain;
    height: 47.5vh;
    max-width: 100%;
    margin: auto;
    filter: drop-shadow(0 0 4px rgba(0,0,0,0.2));

    &.has-answer {
        cursor: pointer;
    }
}

</style>

<template>
    
        <div class="artbox"
            v-on:click="goToPost"
            v-bind:class="answer ? 'has-answer': ''"
            v-bind:style="artboxStyle"></div>

</template>
