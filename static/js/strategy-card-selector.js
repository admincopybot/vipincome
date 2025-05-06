// Script to make iframe content select the corresponding strategy on click
document.addEventListener('DOMContentLoaded', function() {
    // For each strategy card
    document.querySelectorAll('.strategy-card').forEach(function(card) {
        // When the entire card is clicked (including the iframe)
        card.addEventListener('click', function() {
            // Find the radio button inside this card and check it
            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
            }
        });
    });
});