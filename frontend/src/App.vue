<script setup lang="ts">
import { reactive } from 'vue';
import Intro from './components/Intro.vue'
</script>

<script lang="ts">


</script>

<template>
    <header>
        <nav>
            <div class="logo"></div>
        </nav>
    </header>
    <main>
        <!-- UI to allow creation of new games-->
        <Intro></Intro>
    </main>
    <footer>
        made with love by <a href="http://github.com/retsplines" target="_blank">@retsplines</a>
    </footer>
</template>

