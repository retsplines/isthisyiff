import type { Answer } from "./model/answer";
import type { Challenge } from "./model/challenge";
import type { Previews } from "./model/preview";
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

    /**
     * Get a number of previews, which are just crop images for stylistic use.
     * 
     * @param upto The number of previews to retrieve. We may not always deliver as many as requested.
     * @param startFrom Optionally, resume scanning from a UUID to avoid duplicates.
     */
    public static async getPreviews(upto: number, startFrom: string|null = null): Promise<Previews> {
        
        const params: Record<string, string> = {
            upto: upto.toString(10),
        };

        if (startFrom !== null) {
            params['start_from'] = startFrom;
        }

        const response = await fetch(
            `${import.meta.env.VITE_ITY_BACKEND_URI}preview?` + new URLSearchParams(params)
        );
        if (response.status !== 200) {
            throw Error('Failed to load the preview set');
        }
        return await response.json() as Previews;
    }

}
