/**
 * Parodle - Jeu de paroles
 */

class ParodleGame {
    constructor() {
        this.sessionId = null;
        this.startTime = null;
        this.timerInterval = null;
        this.guessesRemaining = 5;
        this.mode = null;
        this.wordType = null;
        this.currentRound = 1;
        this.totalRounds = 1;
        this.cumulativeScore = 0;
        this.selectedArtist = null;
        this.selectedDifficulty = 5;
        this.artists = [];

        this.init();
    }

    init() {
        // Elements
        this.screens = {
            modeSelection: document.getElementById('mode-selection'),
            game: document.getElementById('game-screen'),
            result: document.getElementById('result-screen')
        };

        this.elements = {
            artistSelect: document.getElementById('artist-select'),
            difficultySelect: document.getElementById('difficulty-select'),
            modeIndicator: document.getElementById('mode-indicator'),
            timer: document.getElementById('timer'),
            guessesIndicator: document.getElementById('guesses-indicator'),
            phrase: document.getElementById('phrase'),
            wordTypeHint: document.getElementById('word-type-hint'),
            guessForm: document.getElementById('guess-form'),
            guessInput: document.getElementById('guess-input'),
            previousGuesses: document.getElementById('previous-guesses'),
            passBtn: document.getElementById('pass-btn'),
            hintsSection: document.getElementById('hints-section'),
            hintLetterCountBtn: document.getElementById('hint-letter-count-btn'),
            hintSongTitleBtn: document.getElementById('hint-song-title-btn'),
            hintFirstLetterBtn: document.getElementById('hint-first-letter-btn'),
            backToMenuBtn: document.getElementById('back-to-menu-btn'),
            resultTitle: document.getElementById('result-title'),
            scoreDisplay: document.getElementById('score-display'),
            correctAnswer: document.getElementById('correct-answer'),
            songTitle: document.getElementById('song-title'),
            timeTaken: document.getElementById('time-taken'),
            playAgain: document.getElementById('play-again')
        };

        this.bindEvents();
        this.loadArtists();
    }

    bindEvents() {
        // Artist selection
        this.elements.artistSelect.addEventListener('change', (e) => {
            this.selectedArtist = e.target.value;
        });

        // Difficulty selection
        this.elements.difficultySelect.addEventListener('change', (e) => {
            this.selectedDifficulty = parseInt(e.target.value, 10);
        });

        // Mode selection buttons
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                this.startGame(mode);
            });
        });

        // Guess form submission
        this.elements.guessForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitGuess();
        });

        // Pass button
        this.elements.passBtn.addEventListener('click', () => {
            this.passRound();
        });

        // Hint buttons
        this.elements.hintLetterCountBtn.addEventListener('click', () => {
            this.getHint('letter-count');
        });

        this.elements.hintSongTitleBtn.addEventListener('click', () => {
            this.getHint('song-title');
        });

        this.elements.hintFirstLetterBtn.addEventListener('click', () => {
            this.getHint('first-letter');
        });

        // Back to menu button
        this.elements.backToMenuBtn.addEventListener('click', () => {
            if (confirm('Quitter la partie en cours ?')) {
                this.stopTimer();
                this.showScreen('modeSelection');
            }
        });

        // Play again button
        this.elements.playAgain.addEventListener('click', () => {
            this.showScreen('modeSelection');
        });
    }

    async loadArtists() {
        try {
            const response = await fetch('/api/game/artists');
            if (!response.ok) {
                throw new Error('Erreur lors du chargement des artistes');
            }

            const data = await response.json();
            this.artists = data.artists;

            // Populate dropdown
            this.elements.artistSelect.innerHTML = '';
            this.artists.forEach(artist => {
                const option = document.createElement('option');
                option.value = artist.id;
                option.textContent = `${artist.name} (${artist.song_count} chansons)`;
                this.elements.artistSelect.appendChild(option);
            });

            // Select first artist by default
            if (this.artists.length > 0) {
                this.selectedArtist = this.artists[0].id;
                this.elements.artistSelect.value = this.selectedArtist;
            }

        } catch (error) {
            console.error('Erreur:', error);
            this.elements.artistSelect.innerHTML = '<option value="">Erreur de chargement</option>';
        }
    }

    showScreen(screenName) {
        Object.values(this.screens).forEach(screen => {
            screen.classList.remove('active');
        });
        this.screens[screenName].classList.add('active');
    }

    async startGame(mode) {
        if (!this.selectedArtist) {
            alert('Veuillez selectionner un artiste');
            return;
        }

        try {
            const response = await fetch('/api/game/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mode,
                    artist_id: this.selectedArtist,
                    difficulty: this.selectedDifficulty
                })
            });

            if (!response.ok) {
                throw new Error('Erreur lors du demarrage de la partie');
            }

            const data = await response.json();

            this.sessionId = data.session_id;
            this.mode = data.mode;
            this.wordType = data.word_type;
            this.guessesRemaining = data.max_guesses;
            this.currentRound = data.current_round || 1;
            this.totalRounds = data.total_rounds || 1;
            this.cumulativeScore = 0;

            this.setupGameScreen(data);
            this.startTimer();
            this.showScreen('game');

            // Focus input
            setTimeout(() => {
                this.elements.guessInput.focus();
            }, 100);

        } catch (error) {
            console.error('Erreur:', error);
            alert('Impossible de demarrer la partie. Verifiez que les paroles sont chargees.');
        }
    }

    setupGameScreen(data) {
        // Mode indicator with round info
        let modeText = '';

        // Show round info for multi-round games
        if (data.total_rounds && data.total_rounds > 1) {
            const currentRound = data.current_round || this.currentRound;
            const totalRounds = data.total_rounds || this.totalRounds;
            modeText = `Manche ${currentRound}/${totalRounds}`;
        }

        this.elements.modeIndicator.textContent = modeText;

        // Phrase
        this.elements.phrase.textContent = data.phrase;

        // Word type hint
        if (data.word_type) {
            const hints = {
                'next': 'Trouvez le mot suivant',
                'previous': 'Trouvez le mot precedent',
                'missing': 'Trouvez le mot manquant'
            };
            this.elements.wordTypeHint.textContent = hints[data.word_type] || '';
        } else {
            this.elements.wordTypeHint.textContent = 'Trouvez le titre de la chanson';
        }

        // Reset guesses indicator
        this.updateGuessesIndicator(data.max_guesses);

        // Clear previous guesses
        this.elements.previousGuesses.innerHTML = '';

        // Clear input
        this.elements.guessInput.value = '';

        // Reset timer display
        this.elements.timer.textContent = '00:00';

        // Show/hide action buttons based on mode
        if (data.mode === 'word_guessing' && data.total_rounds > 1) {
            this.elements.passBtn.style.display = 'block';
            this.elements.hintsSection.style.display = 'flex';

            // Reset hint buttons to original state
            this.resetHintButtons();
        } else {
            this.elements.passBtn.style.display = 'none';
            this.elements.hintsSection.style.display = 'none';
        }
    }

    resetHintButtons() {
        // Reset letter count button
        this.elements.hintLetterCountBtn.textContent = 'Lettres';
        this.elements.hintLetterCountBtn.disabled = false;
        this.elements.hintLetterCountBtn.classList.remove('used');

        // Reset song title button
        this.elements.hintSongTitleBtn.textContent = 'Titre';
        this.elements.hintSongTitleBtn.disabled = false;
        this.elements.hintSongTitleBtn.classList.remove('used');

        // Reset first letter button
        this.elements.hintFirstLetterBtn.textContent = '1ere lettre';
        this.elements.hintFirstLetterBtn.disabled = false;
        this.elements.hintFirstLetterBtn.classList.remove('used');

        // Update state based on remaining guesses
        this.updateHintButtonsState();
    }

    updateGuessesIndicator(remaining) {
        const dots = this.elements.guessesIndicator.querySelectorAll('.guess-dot');
        dots.forEach((dot, index) => {
            dot.classList.remove('used', 'correct');
            if (index >= remaining) {
                dot.classList.add('used');
            }
        });
    }

    startTimer() {
        this.startTime = Date.now();

        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }

        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            this.elements.timer.textContent = `${minutes}:${seconds}`;
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    async submitGuess() {
        const guess = this.elements.guessInput.value.trim();

        if (!guess) {
            return;
        }

        try {
            const response = await fetch('/api/game/guess', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    guess: guess
                })
            });

            const data = await response.json();

            if (data.error) {
                console.error('Erreur:', data.error);
                return;
            }

            this.handleGuessResult(data, guess);

        } catch (error) {
            console.error('Erreur:', error);
        }
    }

    async passRound() {
        try {
            const response = await fetch('/api/game/pass', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            if (data.error) {
                console.error('Erreur:', data.error);
                return;
            }

            // Show pass message (like success but in red with 0 points)
            const passMessage = document.createElement('div');
            passMessage.className = 'pass-message';

            let passHTML = `<div style="margin-bottom: 1rem;"><strong>Passe</strong> +0 pts</div>`;
            passHTML += `<div style="font-size: 1.1rem; margin-bottom: 0.5rem;">Reponse: <strong>${data.correct_answer}</strong></div>`;

            // Add song title and context
            if (data.song_title) {
                passHTML += `<div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.95;"><strong>${data.song_title}</strong></div>`;
            }
            if (data.answer_context) {
                const contextHTML = data.answer_context.replace(/\n/g, '<br>');
                passHTML += `<div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.9; font-style: italic; white-space: pre-line;">${contextHTML}</div>`;
            }

            passMessage.innerHTML = passHTML;
            passMessage.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #dc2626; color: white; padding: 2rem; border-radius: 12px; font-size: 1.2rem; text-align: center; z-index: 1000; max-width: 80%; max-height: 80vh; overflow-y: auto;';
            document.body.appendChild(passMessage);

            setTimeout(() => {
                passMessage.remove();

                if (data.game_over) {
                    // Last round - show final recap
                    this.stopTimer();
                    this.showRecap(data);
                } else {
                    // Move to next round
                    this.currentRound = data.current_round;
                    this.cumulativeScore = data.cumulative_score;
                    this.wordType = data.new_word_type;
                    this.guessesRemaining = data.guesses_remaining;

                    // Update UI
                    this.elements.phrase.textContent = data.new_phrase;
                    this.elements.modeIndicator.textContent = `Manche ${this.currentRound}/${this.totalRounds}`;

                    // Reset UI for new round
                    this.updateGuessesIndicator(5);
                    this.elements.previousGuesses.innerHTML = '';
                    this.elements.guessInput.value = '';
                    this.resetHintButtons();
                    this.elements.guessInput.focus();
                }
            }, 3500);

        } catch (error) {
            console.error('Erreur:', error);
        }
    }

    async getHint(hintType) {
        const buttonMap = {
            'letter-count': this.elements.hintLetterCountBtn,
            'song-title': this.elements.hintSongTitleBtn,
            'first-letter': this.elements.hintFirstLetterBtn
        };

        const button = buttonMap[hintType];

        // Check if button is already used or disabled
        if (button.disabled) {
            return;
        }

        try {
            const response = await fetch(`/api/game/hint/${hintType}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            if (data.error) {
                console.error('Erreur:', data.error);
                return;
            }

            // Update the button with the hint
            if (data.hint) {
                button.textContent = data.hint;
                button.disabled = true;
                button.classList.add('used');
            }

            // Update remaining guesses
            this.guessesRemaining = data.guesses_remaining;
            this.updateGuessesIndicator(this.guessesRemaining);

            // Update hint buttons availability
            this.updateHintButtonsState();

            // Check if round failed (5 mistakes) - move to next word
            if (data.round_failed && !data.game_over) {
                const failMessage = document.createElement('div');
                failMessage.className = 'fail-message';

                let failHTML = `<div style="margin-bottom: 1rem;"><strong>Perdu !</strong> +0 pts</div>`;
                failHTML += `<div style="font-size: 1.1rem; margin-bottom: 0.5rem;">Reponse: <strong>${data.correct_answer}</strong></div>`;
                if (data.song_title) {
                    failHTML += `<div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.95;"><strong>${data.song_title}</strong></div>`;
                }

                failMessage.innerHTML = failHTML;
                failMessage.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #dc2626; color: white; padding: 2rem; border-radius: 12px; font-size: 1.2rem; text-align: center; z-index: 1000; max-width: 80%; max-height: 80vh; overflow-y: auto;';
                document.body.appendChild(failMessage);

                setTimeout(() => {
                    failMessage.remove();

                    // Move to next round
                    this.currentRound = data.current_round;
                    this.cumulativeScore = data.cumulative_score;
                    this.wordType = data.new_word_type;
                    this.guessesRemaining = data.guesses_remaining;

                    // Update UI
                    this.elements.phrase.textContent = data.new_phrase;
                    this.elements.modeIndicator.textContent = `Manche ${this.currentRound}/${this.totalRounds}`;

                    // Reset UI for new round
                    this.updateGuessesIndicator(5);
                    this.elements.previousGuesses.innerHTML = '';
                    this.elements.guessInput.value = '';
                    this.resetHintButtons();
                    this.elements.guessInput.focus();
                }, 3500);
                return;
            }

            // Check if game over (no more guesses)
            if (data.game_over) {
                this.stopTimer();
                this.showResult(false, data);
            }

        } catch (error) {
            console.error('Erreur:', error);
        }
    }

    updateHintButtonsState() {
        // Disable all unused hint buttons if less than 3 guesses remaining
        const hintButtons = [
            this.elements.hintLetterCountBtn,
            this.elements.hintSongTitleBtn,
            this.elements.hintFirstLetterBtn
        ];

        hintButtons.forEach(btn => {
            if (!btn.classList.contains('used')) {
                if (this.guessesRemaining < 3) {
                    btn.disabled = true;
                } else {
                    btn.disabled = false;
                }
            }
        });
    }

    handleGuessResult(data, guess) {
        // Round failed (5 mistakes) - move to next word
        if (data.round_failed && !data.game_over) {
            // Show failed answer
            const failMessage = document.createElement('div');
            failMessage.className = 'fail-message';

            let failHTML = `<div style="margin-bottom: 1rem;"><strong>Perdu !</strong> +0 pts</div>`;
            failHTML += `<div style="font-size: 1.1rem; margin-bottom: 0.5rem;">Reponse: <strong>${data.correct_answer}</strong></div>`;
            if (data.song_title) {
                failHTML += `<div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.95;"><strong>${data.song_title}</strong></div>`;
            }
            if (data.answer_context) {
                const contextHTML = data.answer_context.replace(/\n/g, '<br>');
                failHTML += `<div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.9; font-style: italic; white-space: pre-line;">${contextHTML}</div>`;
            }

            failMessage.innerHTML = failHTML;
            failMessage.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #dc2626; color: white; padding: 2rem; border-radius: 12px; font-size: 1.2rem; text-align: center; z-index: 1000; max-width: 80%; max-height: 80vh; overflow-y: auto;';
            document.body.appendChild(failMessage);

            setTimeout(() => {
                failMessage.remove();

                // Move to next round
                this.currentRound = data.current_round;
                this.cumulativeScore = data.cumulative_score;
                this.wordType = data.new_word_type;
                this.guessesRemaining = data.guesses_remaining;

                // Update UI
                this.elements.phrase.textContent = data.new_phrase;
                this.elements.modeIndicator.textContent = `Manche ${this.currentRound}/${this.totalRounds}`;

                // Reset UI for new round
                this.updateGuessesIndicator(5);
                this.elements.previousGuesses.innerHTML = '';
                this.elements.guessInput.value = '';
                this.resetHintButtons();
                this.elements.guessInput.focus();
            }, 3500);
            return;
        }

        if (data.correct && data.round_complete) {
            // Manche reussie
            this.currentRound = data.current_round;
            this.cumulativeScore = data.cumulative_score || data.points_earned;

            // Brief celebration message with song context
            const celebration = document.createElement('div');
            celebration.className = 'round-celebration';

            let celebrationHTML = `<div style="margin-bottom: 1rem;"><strong>Bravo!</strong> +${data.round_score} pts (Total: ${this.cumulativeScore})</div>`;
            celebrationHTML += `<div style="font-size: 1.1rem; margin-bottom: 0.5rem;">Reponse: <strong>${data.correct_answer}</strong></div>`;

            // Add song title and context if available
            if (data.song_title) {
                celebrationHTML += `<div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.95;"><strong>${data.song_title}</strong></div>`;
            }
            if (data.answer_context) {
                const contextHTML = data.answer_context.replace(/\n/g, '<br>');
                celebrationHTML += `<div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.9; font-style: italic; white-space: pre-line;">${contextHTML}</div>`;
            }

            celebration.innerHTML = celebrationHTML;
            celebration.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #276749; color: white; padding: 2rem; border-radius: 12px; font-size: 1.2rem; text-align: center; z-index: 1000; max-width: 80%; max-height: 80vh; overflow-y: auto;';
            document.body.appendChild(celebration);

            setTimeout(() => {
                celebration.remove();

                if (data.game_over) {
                    // Last round - show final recap
                    this.stopTimer();
                    this.showRecap(data);
                } else {
                    // Update to next round
                    this.wordType = data.new_word_type;
                    this.guessesRemaining = 5;
                    this.elements.phrase.textContent = data.new_phrase;

                    // Update word type hint
                    const hints = {
                        'next': 'Trouvez le mot suivant',
                        'previous': 'Trouvez le mot precedent',
                        'missing': 'Trouvez le mot manquant'
                    };
                    this.elements.wordTypeHint.textContent = hints[this.wordType] || '';

                    // Update mode indicator
                    this.elements.modeIndicator.textContent = `Manche ${this.currentRound}/${this.totalRounds}`;

                    // Reset UI
                    this.updateGuessesIndicator(5);
                    this.elements.previousGuesses.innerHTML = '';
                    this.elements.guessInput.value = '';
                    this.resetHintButtons();
                    this.elements.guessInput.focus();
                }
            }, 3500);

        } else if (data.game_over) {
            // Partie terminee (echec)
            this.stopTimer();
            this.showRecap(data);
        } else {
            // Mauvaise reponse, continuer
            this.guessesRemaining = data.guesses_remaining;
            this.updateGuessesIndicator(this.guessesRemaining);
            this.updateHintButtonsState();

            // Add to previous guesses
            this.addPreviousGuess(guess);

            // Update phrase if new hint
            if (data.phrase) {
                this.elements.phrase.textContent = data.phrase;
                this.elements.phrase.classList.add('pulse');
                setTimeout(() => {
                    this.elements.phrase.classList.remove('pulse');
                }, 300);
            }

            // Shake animation on wrong answer
            this.elements.guessInput.classList.add('shake');
            setTimeout(() => {
                this.elements.guessInput.classList.remove('shake');
            }, 300);

            // Clear and focus input
            this.elements.guessInput.value = '';
            this.elements.guessInput.focus();
        }
    }

    addPreviousGuess(guess) {
        const span = document.createElement('span');
        span.className = 'previous-guess';
        span.textContent = guess;
        this.elements.previousGuesses.appendChild(span);
    }

    showResult(success, data) {
        // Title
        this.elements.resultTitle.textContent = success ? 'Bravo !' : 'Dommage...';
        this.elements.resultTitle.className = success ? 'success' : 'failure';

        // Score
        const score = data.points_earned || 0;
        this.elements.scoreDisplay.textContent = `${score} pts`;

        // Details
        this.elements.correctAnswer.textContent = data.correct_answer || '-';
        this.elements.songTitle.textContent = data.song_title || '-';

        const timeSeconds = data.time_seconds || 0;
        const minutes = Math.floor(timeSeconds / 60);
        const seconds = Math.floor(timeSeconds % 60);
        this.elements.timeTaken.textContent = minutes > 0
            ? `${minutes}m ${seconds}s`
            : `${seconds}s`;

        this.showScreen('result');
    }

    showRecap(data) {
        // Build recap HTML
        const totalScore = data.points_earned || 0;
        const roundResults = data.round_results || [];

        let recapHTML = `
            <h2 style="margin-bottom: 1.5rem;">Partie terminee</h2>
            <div style="font-size: 2rem; font-weight: bold; color: var(--accent-color); margin-bottom: 2rem;">${totalScore} pts</div>
        `;

        // Add each round
        roundResults.forEach((round) => {
            const bgColor = round.success ? '#276749' : '#dc2626';
            const statusText = round.success ? `+${round.points} pts` : 'Passe';
            const contextHTML = round.context ? round.context.replace(/\n/g, '<br>') : '';

            recapHTML += `
                <div style="background: ${bgColor}; color: white; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; text-align: left;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-weight: bold;">Manche ${round.round}</span>
                        <span>${statusText}</span>
                    </div>
                    <div style="font-size: 1rem; margin-bottom: 0.5rem;">Reponse: <strong>${round.answer}</strong></div>
                    <div style="font-size: 0.9rem; opacity: 0.95; margin-bottom: 0.5rem;"><strong>${round.song_title}</strong></div>
                    <div style="font-size: 0.85rem; opacity: 0.9; font-style: italic;">${contextHTML}</div>
                </div>
            `;
        });

        recapHTML += `
            <button class="play-again-btn" id="recap-play-again" style="margin-top: 1rem;">Rejouer</button>
        `;

        // Update result screen content
        this.elements.resultTitle.textContent = '';
        this.elements.resultTitle.className = '';
        this.elements.scoreDisplay.textContent = '';

        // Hide default result details
        const resultDetails = document.querySelector('.result-details');
        if (resultDetails) resultDetails.style.display = 'none';

        // Create recap container
        const resultContent = document.querySelector('.result-content');
        resultContent.innerHTML = recapHTML;

        // Add event listener for play again button
        document.getElementById('recap-play-again').addEventListener('click', () => {
            // Restore original result screen structure
            resultContent.innerHTML = `
                <h2 id="result-title"></h2>
                <div class="score-display" id="score-display"></div>
                <div class="result-details">
                    <p><strong>Reponse :</strong> <span id="correct-answer"></span></p>
                    <p><strong>Chanson :</strong> <span id="song-title"></span></p>
                    <p><strong>Temps :</strong> <span id="time-taken"></span></p>
                </div>
                <button class="play-again-btn" id="play-again">Rejouer</button>
            `;
            // Re-bind elements
            this.elements.resultTitle = document.getElementById('result-title');
            this.elements.scoreDisplay = document.getElementById('score-display');
            this.elements.correctAnswer = document.getElementById('correct-answer');
            this.elements.songTitle = document.getElementById('song-title');
            this.elements.timeTaken = document.getElementById('time-taken');
            this.elements.playAgain = document.getElementById('play-again');
            this.elements.playAgain.addEventListener('click', () => {
                this.showScreen('modeSelection');
            });

            this.showScreen('modeSelection');
        });

        this.showScreen('result');
    }
}

// Initialize game when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.game = new ParodleGame();
});
