<script setup lang="ts">
import { type CSSProperties, ref } from 'vue';
import Intro from './components/Intro.vue'
import Game from './components/Game.vue'
import { GameClient } from './client/game'
import type { Challenge } from './client/model/challenge'
import { preloadImage } from './client/image';


</script>

<script lang="ts">

const challenges = ref<Challenge[]>([]);
const backdropStyle = ref<CSSProperties>({});

// Decide if we have a fragment to start a challenge immediately
const hash = window.location.hash;
const challengeDeeplinkUuid = hash.substring(hash.indexOf('#') + 1);

if (challengeDeeplinkUuid.length >= 36) {
    // We have a deeplinked challenge, go straight to it
    console.log(`Going directly to deeplinked challenge ${challengeDeeplinkUuid}`);
    nextChallenge(challengeDeeplinkUuid);
}


/**
 * Preload a challenge.
 */
async function preloadChallenge(uuid?: string): Promise<Challenge> {

    console.log('Getting a challenge...');
    const challenge = await GameClient.getChallenge(uuid);

    // Preload the image
    console.log(`Preloading crop ${challenge.crop.url} for challenge ${challenge.uuid}...`);
    await preloadImage(challenge.crop.url);

    return challenge;
}

/**
 * Start a new challenge.
 */
async function nextChallenge(uuid?: string) {
    
    // Load a new challenge
    let newChallenge: Challenge;

    try {
        newChallenge = await preloadChallenge(uuid);
    } catch {
        challenges.value.length = 0;
        return;
    }

    // Once it's loaded, swap to it
    if (challenges.value.length !== 0) {
        challenges.value.length = 0;
    }

    challenges.value.push(newChallenge);

    // Update the URL
    window.location.hash = '#' + newChallenge.uuid;
    
    // Update the backdrop to match
    backdropStyle.value.backgroundImage = `url('${newChallenge.crop.url}')`;

}

/**
 * Return to the intro.
 */
async function backToIntro() {
    challenges.value.length = 0;
}

</script>

<style scoped="true" lang="scss">

.v-enter-active, .v-leave-active {
  transition: all 0.5s ease;
}

.v-leave-to {
  opacity: 0;
  z-index: 2;
  transform: translateX(-200%);
}

.v-enter-from {
  opacity: 0;
  z-index: -1;
  transform: translateX(200%);
}

.slide {
    position: fixed;
}

.backdrop {
    transition: all 1s ease;
    background-size: cover;
    background-repeat: no-repeat;
    position: relative;
    width: 100%;
    height: 100%;
    opacity: 0.25;
    filter: blur(20px);
}

</style>

<template>
    <header>
        <nav>
            <div class="logo" v-on:click="backToIntro"></div>
        </nav>
    </header>
    <main>

        <div class="backdrop" v-bind:style="backdropStyle"></div>

        <TransitionGroup>

            <!-- Show the intro if there are no challenges yet -->
            <Intro v-if="challenges.length === 0" @did-accept-intro="nextChallenge" :key="'intro-text'" class="slide"></Intro>

            <!-- Show the challenge from the list otherwise-->
            <Game v-for="challenge in challenges" :challenge="challenge" :key="challenge.uuid" v-on:next-game-please="nextChallenge" class="slide"></Game>

        </TransitionGroup>

    </main>
    <footer>
        made with love by <a href="http://github.com/retsplines" target="_blank">@retsplines</a>
    </footer>
</template>

