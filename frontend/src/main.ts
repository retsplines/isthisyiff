import { createApp } from 'vue';
import { GesturePlugin } from '@vueuse/gesture'
import App from './App.vue';
import './assets/bulma.scss';
import './assets/base.scss';
import './assets/app.scss';
const app = createApp(App);
app.use(GesturePlugin);
app.mount('#app');

