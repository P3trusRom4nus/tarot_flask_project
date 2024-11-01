

function updateButtonText() {
    var servicePrice = parseInt(document.getElementById('service').value);
    var checkoutButton = document.getElementById('checkout-button');
    var birthDetails = document.getElementById('birth-details');
    var messageContainer = document.getElementById('message-container');
    
    // Update button text
    checkoutButton.textContent = 'Pay for Your Reading - $' + servicePrice;

    // Show or hide birth details and message based on service selection
    if (servicePrice === 150 || servicePrice === 250) {
        birthDetails.classList.remove('hidden');
        messageContainer.classList.add('hidden');
    } else {
        birthDetails.classList.add('hidden');
        messageContainer.classList.remove('hidden');
    }
}

// Initialize button text and fields on load
document.getElementById('service').addEventListener('change', updateButtonText);
updateButtonText(); // Call on page load

function validateForm() {
    var isValid = true;

    var name = document.getElementById('name').value.trim();
    var email = document.getElementById('email').value.trim();
    var zodiacSign = document.getElementById('zodiac').value;
    var servicePrice = parseInt(document.getElementById('service').value);
    var dob = document.getElementById('dob').value;
    var tob = document.getElementById('tob').value;
    var pob = document.getElementById('pob').value;
    var message = document.getElementById('message').value.trim();

    // Clear error messages
    document.querySelectorAll('.error-message').forEach(el => el.classList.add('hidden'));

    // Name validation with regex (allowing only letters and spaces)
    var namePattern = /^[A-Za-zÀ-ÿ\s]+$/; // Allows letters (including accented) and spaces only
    if (!name || name.length < 2 || !namePattern.test(name)) {
        document.getElementById('name-error').classList.remove('hidden');
        isValid = false;
    }


    // Validate zodiac sign
    if (!zodiacSign) {
        document.getElementById('zodiac-error').classList.remove('hidden');
        isValid = false;
    }

    // Email validation with regex
    var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailPattern.test(email)) {
        document.getElementById('email-error').classList.remove('hidden');
        isValid = false;
    }

    // If the service requires birth details, validate those fields
    if (servicePrice === 150 || servicePrice === 250) {
        if (!dob) {
            document.getElementById('dob-error').classList.remove('hidden');
            isValid = false;
        }
        if (!tob) {
            document.getElementById('tob-error').classList.remove('hidden');
            isValid = false;
        }
        if (!pob) {
            document.getElementById('pob-error').classList.remove('hidden');
            isValid = false;
        }
    }
    // Additional message validation
    if (servicePrice != 150 && servicePrice != 250) {
        if (message === "") {
            document.getElementById('message-error').classList.remove('hidden');
            isValid = false;
        }
    } else {
        // Clear message error if valid input
        if (message !== "") {
            document.getElementById('message-error').classList.add('hidden');
        }
    }

    return isValid;
}

// Clear message error on input
document.getElementById('message').addEventListener('input', function () {
    document.getElementById('message-error').classList.add('hidden');
});

document.getElementById('checkout-button').addEventListener('click', function(e) {
    e.preventDefault(); // Prevent form submission

    if (!validateForm()) {
        return;
    }


    // Hide the loader when the page loads or is restored from the browser cache
    function hideLoaderOnLoad() {
        document.getElementById('loader').classList.add('hidden');
    }

    // Hide the loader on page load (for regular loads)
    document.addEventListener('DOMContentLoaded', hideLoaderOnLoad);

    // Hide the loader on pageshow (for when coming back from cache)
    window.addEventListener('pageshow', hideLoaderOnLoad);

    document.getElementById('loader').classList.remove('hidden');


var name = document.getElementById('name').value;
var email = document.getElementById('email').value;
var zodiacSign = document.getElementById('zodiac').value; // Capture zodiac sign
var servicePrice = document.getElementById('service').value;
var message = document.getElementById('message').value;
var dob = document.getElementById('dob').value;
var tob = document.getElementById('tob').value;
var pob = document.getElementById('pob').value;
var csrfToken = document.querySelector('input[name="csrf_token"]').value;

var requestData = {
        name: name,
        email: email,
        zodiacSign: zodiacSign,
        servicePrice: servicePrice,
        message: servicePrice == 150 || servicePrice == 250
            ? `Date of Birth: ${dob}, Time of Birth: ${tob}, Place of Birth: ${pob}`
            : message // Message for other services
    };
    
    fetch('/create-checkout-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            throw new Error(data.error || 'An error occurred');
        }
        return stripe.redirectToCheckout({ sessionId: data.id });
    })
    .then(result => {
        if (result.error) {
            throw new Error(result.error.message);
        }
    })
    .catch(error => {
        document.getElementById('loader').classList.add('hidden');
        if (error.errors) {
            // Handle validation errors
            Object.entries(error.errors).forEach(([field, message]) => {
                const errorElement = document.getElementById(`${field}-error`);
                if (errorElement) {
                    errorElement.textContent = message;
                    errorElement.classList.remove('hidden');
                }
            });
        } else {
            console.error('Error:', error);
            alert('');
        }
    });
});