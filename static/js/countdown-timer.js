// Countdown Timer functionality
document.addEventListener('DOMContentLoaded', function() {
    function updateCountdown() {
        // Set the date we're counting down to (June 20, 2025)
        const endDate = new Date("June 20, 2025 23:59:59").getTime();
        const now = new Date().getTime();
        const timeLeft = endDate - now;
        
        // Calculate time components
        const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
        const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
        
        // Display the countdown
        const timerElement = document.getElementById("countdown-banner-timer");
        if (timerElement) {
            timerElement.innerHTML = days + "D " + hours + "H " + minutes + "M " + seconds + "S";
        }
    }
    
    // Update the countdown every second
    setInterval(updateCountdown, 1000);
    updateCountdown(); // Initial call
});