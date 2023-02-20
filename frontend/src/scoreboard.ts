/**
 * A really simple scoreboard to track scores during gameplay.
 */
export class Scoreboard {

    /**
     * Our current streak.
     */
    private static streak = 0;

    /**
     * The best streak we've had this session.
     */
    private static bestStreak: number = 0;


    public static win() {
        this.streak ++;

        if (this.streak > this.bestStreak) {
            this.bestStreak = this.streak;
        }
    }

    public static lose() {
        this.streak = 0;
    }

    public static getStreak() {
        return this.streak;
    }

    public static getBestStreak() {
        return this.bestStreak;
    }

}