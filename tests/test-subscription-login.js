/**
 * Subscription Login Test
 * 
 * This script helps verify that users without an active subscription
 * cannot log in to the application.
 * 
 * To run:
 * 1. Install Node.js and npm
 * 2. Run: npm install node-fetch
 * 3. Execute: node test-subscription-login.js
 */

const fetch = require('node-fetch');

const API_URL = 'http://localhost:5000'; // Change to your backend URL
const TEST_USERNAME = 'test_user';
const TEST_PASSWORD = 'test_password';

async function testLoginWithoutSubscription() {
  console.log('Testing login without active subscription...');
  
  try {
    // Attempt to login
    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: TEST_USERNAME,
        password: TEST_PASSWORD
      })
    });
    
    const data = await response.json();
    
    if (response.status === 403 && data.subscription_required) {
      console.log('✅ Success: Login denied as expected due to missing subscription');
      console.log('Response:', data);
    } else if (response.status === 200) {
      console.log('❌ Failed: Login succeeded when it should have been blocked');
      console.log('Response:', data);
    } else {
      console.log(`❓ Unexpected response (${response.status}):`, data);
    }
  } catch (error) {
    console.error('Error during test:', error);
  }
}

// Run the test
testLoginWithoutSubscription(); 