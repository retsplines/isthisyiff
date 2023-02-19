import type { Answer } from "./model/answer";
import type { Challenge } from "./model/challenge";
import type { Rating } from "./model/rating";

export class GameClient {

    /**
     * Request a challenge.
     */
    public static async getChallenge(): Promise<Challenge> {
        const response = await fetch(import.meta.env.VITE_ITY_BACKEND_URI + 'challenge');
        return await response.json() as Challenge;
    }

    /**
     * Submit an answer.
     * @param guess
     */
    public static async submitAnswer(uuid: string, guess: Rating): Promise<Answer> {
        const submissionUrl = import.meta.env.VITE_ITY_BACKEND_URI + 'challenge/' + uuid + '/' + guess;
        const response = await fetch(submissionUrl, {
            method: "POST"
        });
        return await response.json() as Answer;
    }

}
