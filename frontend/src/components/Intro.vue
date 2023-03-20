<script setup lang="ts">
import { ref } from 'vue';

const accepted = ref<boolean>(false);
const emit = defineEmits(['didAcceptIntro'])

</script>

<style scoped="true" lang="scss">


.intro {
    font-size: 20px;
    padding: 0 50px;
    max-width: 650px;
}

.intro {


    p {
        margin-top: 1.5rem;
        font-size: 1.1rem;
        text-shadow: 0px 0px 8px var(--color-background);

        &:first-child {
            font-size: 1.8rem;
            a {
                color: inherit;
            }
        }
    }

    .buttons {
        margin-top: 2rem;
    }

}

</style>


<template>
    <div class="intro">
        <p class="first">
            A guessing game using artwork from
            <a href="https://e621.net" target="_blank">e621.net</a>
        </p>    
        <p>
            Try to guess whether an image is yiff or not just based on a face-crop. Ready to play? You must be 18+ to continue.
        </p>
            
        <div class="buttons">
            <button class="button" v-bind:disabled="accepted" v-on:click="emit('didAcceptIntro'); accepted = true;">
                I'm 18+
            </button>
            <a class="button" v-if="!accepted" href="https://e926.net/">
                Nope
            </a>
        </div>

    </div>   
</template>
