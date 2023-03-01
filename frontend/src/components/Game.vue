<script setup lang="ts">
import { GameClient } from '@/client/game';
import { preloadImage } from '@/client/image';
import type { Challenge } from '@/client/model/challenge';
import type { Answer } from '@/client/model/answer';
import type { Rating } from '@/client/model/rating';
import type { ReportReason } from '@/client/model/report-reason';
import { Scoreboard } from '@/scoreboard';
import { ref } from 'vue';
import ArtPane from './ArtPane.vue'

const emit = defineEmits(['nextGamePlease']);

const props = defineProps<{
    challenge: Challenge
}>()

const guessMade = ref<boolean>(false);
const answer = ref<Answer|null>(null);
const missingImage = ref<boolean>(false);
const reportingState = ref<'closed'|'choosing'|'sending'|'thanks'>('closed');

/**
 * Submit a guess.
 * 
 * @param guess
 */
async function makeGuess(guess: Rating) {

    guessMade.value = true;
    const answerResponse = await GameClient.submitAnswer(props.challenge.uuid, guess);

    // Preload the image before revealling the answer
    console.log(`Preloading orig ${answerResponse.orig.url} before revealing...`);

    try {
        await preloadImage(answerResponse.orig.url);
        console.log(`Preloading of orig ${answerResponse.orig.url} complete`);
    } catch (preloadError) {
        // Stomp over the image with a generic "not found" placeholder.
        console.warn(`Error preloading orig`, preloadError);
        missingImage.value = true;
    }
    
    answer.value = answerResponse;

    if (answerResponse.result.actual === guess) {
        Scoreboard.win();
    } else {
        Scoreboard.lose();
    }
}

/**
 * Report the post.
 * 
 * @param reason
 */
async function reportPostFor(reason: ReportReason) {
    reportingState.value = 'sending';
    await GameClient.reportPost(props.challenge.uuid, reason);
    reportingState.value = 'thanks';
}

</script>


<style scoped="true" lang="scss">

@import '../assets/base.scss';

.game {
    width: 100%;
    margin: auto;
    text-align: center;
}

.missing {
    h3 {
        font-size: 2rem;
        font-weight: bold;
    }
}

.controls {
    margin-top: 2rem;
    button {
        margin: 10px;
        border-radius: 8px;
    }
}

.result {
    margin: 2rem auto auto auto;
    max-width: 500px;

    .answer {

        cursor: pointer;
        padding: 0.5rem 0;
        color: var(--ity-white);

        @media (min-width: 501px) {
            border-radius: 10px;
        }

        .headline {
            font-weight: bold;
            font-size: 1.65rem;
        }

        .detail, strong {
            color: var(--ity-white);
            &.streak {
                font-size: 0.875rem;
            }
        }

        &.correct {
            background-color: $correct;
            border-bottom: 5px solid darken($correct, 15);

            &:hover {
                border-bottom: 5px solid darken($correct, 5);
                background-color: lighten($correct, 5);
            }
        }
        &.incorrect {
            background-color: $incorrect;
            border-bottom: 5px solid darken($incorrect, 15);
            &:hover {
                border-bottom: 5px solid darken($incorrect, 5);
                background-color: lighten($incorrect, 5);
            }
        }
    }

    .result-controls {
        margin-top: 1rem;

        a {
            color: var(--color-text);
            text-decoration: underline;
        }

        .report-buttons {
            button {
                margin: 0 0.25rem;
            }
        }
    }
}

</style>

<template>
    
    <div class="game">

        <ArtPane v-if="!missingImage" ref="art" :challenge="challenge" :answer="answer"></ArtPane>
        
        <div class="missing" v-if="missingImage">
            <h3>ruh-roh</h3>
            <p>
                This image is missing, sorry about that.
            </p>
        </div>

        <div class="controls" v-if="!answer">
            <button v-bind:disabled="guessMade" class="button is-danger is-large" v-on:click="makeGuess('e')">YIFF</button>
            <button v-bind:disabled="guessMade" class="button is-success is-large" v-on:click="makeGuess('s')">Safe</button>
        </div>

        <div class="result" v-if="answer">
            
            <div class="answer" v-on:click.once="emit('nextGamePlease')" :class="answer.result.actual !== answer.result.guess ? 'incorrect' : 'correct'">
                <span class="headline">
                    {{ answer.result.actual !== answer.result.guess ? 'Nope, it was ' : 'Correct - it was ' }} 
                    {{ answer.result.actual === 'e' ? 'Yiff' : 'Safe' }}!
                </span>
                <p class="detail streak">
                    <span v-if="Scoreboard.getStreak() !== 0">On a streak of <strong>{{ Scoreboard.getStreak() }}</strong>&nbsp;</span>
                    <span v-if="Scoreboard.getBestStreak()">&nbsp;Best streak so far: <strong>{{ Scoreboard.getBestStreak() }}</strong></span>
                </p>
                <p class="detail">
                    <span v-if="answer.statistics.correct_guesses + answer.statistics.incorrect_guesses === 0">
                        You're the first to guess this image!
                    </span>
                    <span v-else>
                        <strong :title="answer.statistics.correct_guesses + ' correct, ' + answer.statistics.incorrect_guesses + ' incorrect'">
                            {{ Math.round((answer.statistics.correct_guesses / (answer.statistics.correct_guesses + answer.statistics.incorrect_guesses)) * 100) }}%
                        </strong> guessed this image correctly.
                    </span>
                    <strong> Play again? </strong>
                </p>
            </div>
            
            <div class="result-controls">
                <a :href="answer.source.url" target="_blank">See it on e621</a> &nbsp; | &nbsp;
                <a v-if="reportingState === 'closed'" v-on:click="reportingState = 'choosing'">Report Post</a>
                <span v-else-if="reportingState === 'choosing'" class="report-buttons">
                    <button class="button is-small" title="Shouldn't be shown on IsThisYiff" v-on:click="reportPostFor('unsuitable')">Unsuitable</button>
                    <button class="button is-small" title="Copyright complaint" v-on:click="reportPostFor('copyright')">Copyright</button>
                    <button class="button is-small" title="Has the wrong rating" v-on:click="reportPostFor('wrong_rating')">It's {{ answer.result.actual === 'e' ? 'Safe' : 'Yiff' }}!</button>
                </span>
                <span v-else-if="reportingState === 'sending'">
                    Please wait...
                </span>
                <span v-else-if="reportingState === 'thanks'">
                    Thanks, I'll look into this.
                </span>
            </div>
        </div>

    </div>

</template>
