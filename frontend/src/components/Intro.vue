<style scoped="true" lang="scss">

.intro {
    font-size: 20px;
    padding: 0 50px;
    max-width: 650px;
    margin: auto;
}

.intro {

    p {
        margin-top: 1.5rem;
        font-size: 1.1rem;
        &:first-child {
            font-size: 1.8rem;
            a {
                color: inherit;
            }
        }
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
        <p>
            
            <div class="buttons">
                <button class="button" v-on:click="newGame()">
                    I'm 18+
                </button>
                <a class="button" href="https://e926.net/">
                    Nope
                </a>
            </div>

        </p>
    </div>   
</template>
