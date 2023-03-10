import type { Answer } from "./model/answer";
import type { Challenge } from "./model/challenge";
import type { Rating } from "./model/rating";
import type { ReportReason } from "./model/report-reason";

export class GameClient {

    /**
     * Request a challenge - either random or by UUID.
     */
    public static async getChallenge(uuid?: string): Promise<Challenge> {
        const response = await fetch(
            `${import.meta.env.VITE_ITY_BACKEND_URI}challenge${uuid ? '/' + uuid : ''}`
        );
        if (response.status !== 200) {
            throw Error('Failed to load the challenge');
        }
        return await response.json() as Challenge;
    }

    /**
     * Submit an answer.
     * @param guess
     */
    public static async submitAnswer(uuid: string, guess: Rating): Promise<Answer> {
        const submissionUrl = `${import.meta.env.VITE_ITY_BACKEND_URI}challenge/${uuid}/${guess}`;
        const response = await fetch(submissionUrl, {
            method: "POST"
        });
        if (response.status !== 200) {
            throw Error('Failed to load the answer');
        }
        return await response.json() as Answer;
    }

    /**
     * Submit a post report.
     * @param guess
     */
    public static async reportPost(uuid: string, reason: ReportReason): Promise<void> {
        const reportUrl = `${import.meta.env.VITE_ITY_BACKEND_URI}challenge/${uuid}/report/${reason}`;
        const response = await fetch(reportUrl, {
            method: "POST"
        });
        if (response.status !== 200) {
            throw Error('Failed to report the post');
        }
        return;
    }

}
