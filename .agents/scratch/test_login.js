async function test() {
  try {
    const res = await fetch('https://autobot-webapp-dev.gryd.in/gryd/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-GRYD-ENTERPRISE-ID': 'autocrm',
        'X-GRYD-SIGNUP-TOKEN': 'YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0'
      },
      body: JSON.stringify({
        user_id: 'dealership@iamdave.ai',
        password: 'wrongpassword',
        role: 'human_agent',
        attribute: 'email',
        application_id: 'autocrm'
      })
    });
    console.log('Status:', res.status);
    console.log('Headers:', Object.fromEntries(res.headers.entries()));
    const text = await res.text();
    console.log('Body:', text);
  } catch (err) {
    console.error('Error:', err);
  }
}

test();
