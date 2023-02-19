<script setup lang="ts">
import { GameClient } from '@/client/game';
import { preloadImage } from '@/client/image';
import type { Challenge } from '@/client/model/challenge';
import type { Answer } from '@/client/model/answer';
import type { Rating } from '@/client/model/rating';
import { ref } from 'vue';
import ArtPane from './ArtPane.vue'

const emit = defineEmits(['nextGamePlease']);

const props = defineProps<{
    challenge: Challenge
}>()

const answer = ref<Answer|null>(null);

/**
 * Submit a guess.
 * 
 * @param guess
 */
async function makeGuess(guess: Rating) {
    const answerResponse = await GameClient.submitAnswer(props.challenge.uuid, guess);

    // Preload the image before revealling the answer
    console.log(`Preloading orig ${answerResponse.orig.url} before revealing...`);
    await preloadImage(answerResponse.orig.url);
    answer.value = answerResponse;
}

</script>


<style scoped="true" lang="scss">

@import '../assets/base.scss';

.game {
    width: 100%;
    margin: auto;
    text-align: center;
}

.controls {
    margin-top: 2rem;
    button {
        margin: 10px;
    }
}

.result {
    margin-top: 2rem;

    .answer {

        padding: 0.5rem 0;
        color: var(--ity-white);

        .headline {
            font-weight: bold;
            font-size: 1.65rem;
        }

        .detail, strong {
            color: var(--ity-white);
        }

        &.correct {
            background-color: $correct;
            border-bottom: 5px solid darken($correct, 10);
        }
        &.incorrect {
            background-color: $incorrect;
            border-bottom: 5px solid darken($incorrect, 10);
        }
    }

    .result-controls {
        margin-top: 1rem;

        a {
            color: var(--ity-white);
            text-decoration: underline;
        }
    }
}

</style>

<template>
    
    <div class="game">

        <ArtPane ref="art" :challenge="challenge" :answer="answer"></ArtPane>
        
        <div class="controls" v-if="!answer">
            <button class="button is-danger is-large" v-on:click="makeGuess('e')">YIFF</button>
            <button class="button is-success is-large" v-on:click="makeGuess('s')">Safe</button>
        </div>

        <div class="result" v-if="answer">
            
            <div class="answer" :class="answer.result.actual !== answer.result.guess ? 'incorrect' : 'correct'">
                <span class="headline">
                    {{ answer.result.actual !== answer.result.guess ? 'Nope, it was ' : 'Correct - it was ' }} 
                    {{ answer.result.actual === 'e' ? 'Yiff' : 'Safe' }}!
                </span>
                <p class="detail">
                    <span v-if="answer.statistics.correct_guesses + answer.statistics.incorrect_guesses === 0">
                        You're the first to guess this image!
                    </span>
                    <span v-else>
                        <strong>{{ answer.statistics.correct_guesses }}</strong> have guessed this image correctly,
                        <strong>{{ answer.statistics.incorrect_guesses }}</strong> have guessed incorrectly.
                    </span>
                </p>
            </div>
            
            <div class="result-controls">
                <a :href="answer.source.url" target="_blank">See it on e621</a> or play 
                <button class="button is-small" v-on:click="emit('nextGamePlease')">Another?</button>
            </div>
        </div>

    </div>

</template>
