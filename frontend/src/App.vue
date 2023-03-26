<script setup lang="ts">
import { type CSSProperties, ref } from 'vue';
import Intro from './components/Intro.vue'
import Game from './components/Game.vue'
import Collage from './components/collage/Collage.vue';
import { GameClient } from './client/game'
import type { Challenge } from './client/model/challenge'
import { preloadImage } from './client/image';
import { Scoreboard } from './scoreboard';

const challenges = ref<Challenge[]>([]);
const backdropStyle = ref<CSSProperties>({});

// Component refs
const collage = ref<InstanceType<typeof Collage> | null>();

// Should main content be displayed, or the nice slideshow?
const slideshowMode = ref<boolean>(hasPassedAgeCheck());

// A queued challenge UUID
let queuedChallengeUuid: string|undefined = undefined;

// Decide if we have a fragment to start a challenge immediately
const hash = window.location.hash;
const challengeDeeplinkUuid = hash.substring(hash.indexOf('#') + 1);

if (challengeDeeplinkUuid.length >= 36) {
    // We have a deeplinked challenge, go straight to it
    console.log(`Got deeplinked challenge ${challengeDeeplinkUuid}`);

    // Has the user already passed the age check?
    if (hasPassedAgeCheck()) {
        // Start the challenge immediately
        console.log('Age check already passed, starting it immediately...');
        nextChallenge(challengeDeeplinkUuid);
    } else {
        console.log('Waiting for age check...');
        queuedChallengeUuid = challengeDeeplinkUuid;
    }
} else {
    if (hasPassedAgeCheck()) {
        nextChallenge();
    }
}

/**
 * Check whether the user has passed the age check.
 */
function hasPassedAgeCheck() {
    return document.cookie.indexOf('passed-age-check=1') === 0;
}

/**
 * Mark the user as having passed the age check.
 */
function passAgeCheck() {
    console.log('Age check passed');
    document.cookie = 'passed-age-check=1; max-age=31536000; path=/';
}

/**
 * The user accepted the intro.
 */
function acceptIntro() {
    passAgeCheck();
    nextChallenge(queuedChallengeUuid);
    queuedChallengeUuid = undefined;
}

/**
 * Preload a challenge.
 */
async function preloadChallenge(uuid?: string): Promise<Challenge> {

    console.log('Getting a challenge...');
    const challenge = await GameClient.getChallenge(uuid);

    try {
        // Preload the image
        console.log(`Preloading crop ${challenge.crop.url} for challenge ${challenge.uuid}...`);
        await preloadImage(challenge.crop.url);
        console.log(`Preloading of crop ${challenge.crop.url} complete`);
    } catch (preloadError) {
        console.warn(`Error preloading crop`, preloadError);
    }

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
        // Return to the intro
        challenges.value.length = 0;
        return;
    }

    // Once it's loaded, swap to it
    if (challenges.value.length !== 0) {
        challenges.value.length = 0;
    }
    
    // Stop displaying slideshow
    slideshowMode.value = false;

    challenges.value.push(newChallenge);

    // Update the URL
    history.replaceState({
        challenge: newChallenge.uuid
    }, "", "/challenge/" + newChallenge.uuid);
    
    // Update the backdrop to match
    backdropStyle.value.backgroundImage = `url('${newChallenge.crop.url}')`;

}

/**
 * Return to the intro.
 */
function backToIntro() {

    if (challenges.value.length > 0 && collage.value) {

        // Give the collage a little flick to show that it's draggable
        collage.value.flick(500, 500);

        // Reset our score
        Scoreboard.lose();
    }
    
    challenges.value.length = 0;
    history.replaceState({}, "", "/");
    backdropStyle.value.backgroundImage = 'none';
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

footer {
    user-select: none;
}

.backdrop {
    transition: all 0.4s ease;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    position: relative;
    width: 100%;
    height: 100%;

    &.blurred {
        opacity: 0.30;
        filter: blur(10px);
    }
}


</style>

<template>

    <header>
        <nav>
            <div class="logo" v-on:click="backToIntro()"></div>
        </nav>
    </header>
    <main>

        <div class="backdrop" :class="{'blurred': !hasPassedAgeCheck() || challenges.length > 0}">
            <Collage ref="collage" v-on:next-game-please="nextChallenge" :interactive="challenges.length === 0 && hasPassedAgeCheck()"></Collage>
        </div>

        <TransitionGroup>

            <!-- Show the intro if there are no challenges yet, and we haven't passed the age-check -->
            <Intro v-if="challenges.length === 0&& !hasPassedAgeCheck()" @did-accept-intro="acceptIntro" :key="'intro-text'" class="slide"></Intro>

            <!-- Show nothing, revealling the collage behind otherwise -->
            <div v-if="challenges.length === 0 && hasPassedAgeCheck()" class="slide"></div>

            <!-- Show the challenge from the list otherwise-->
            <Game v-for="challenge in challenges" :challenge="challenge" :key="challenge.uuid" v-on:next-game-please="nextChallenge" class="slide"></Game>

        </TransitionGroup>

    </main>

    <footer>
        made with love by <a href="https://github.com/retsplines/isthisyiff" target="_blank">@retsplines</a>
    </footer>

</template>

