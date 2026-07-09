import 'server-only';

function getEnv(key: string, fallback: string): string {
  return (typeof process !== 'undefined' && process.env && process.env[key]) as string || fallback;
}

export const serverConfig = {
  grydEndpoint: getEnv('GRYD_ENDPOINT', 'http://localhost:3456'),
  grydModel: getEnv('GRYD_MODEL', 'gcp-gemini-3.1-flash-lite-preview'),
  grydSignupToken: getEnv('GRYD_SIGNUP_TOKEN', ''),
  corsProxyUrl: getEnv('CORS_PROXY_URL', ''),
  llmBatchSize: parseInt(getEnv('LLM_BATCH_SIZE', '30')),
  llmMaxConcurrent: parseInt(getEnv('LLM_MAX_CONCURRENT', '5')),
  llmMaxRetries: parseInt(getEnv('LLM_MAX_RETRIES', '1')),
  llmRequestTimeoutMs: parseInt(getEnv('LLM_REQUEST_TIMEOUT_MS', '45000')),
  llmPromptCharLimit: parseInt(getEnv('LLM_PROMPT_CHAR_LIMIT', '1200')),
  llmMaxOutputTokens: parseInt(getEnv('LLM_MAX_OUTPUT_TOKENS', '1600')),
  llmDispositionBatchSize: parseInt(getEnv('LLM_DISPO_BATCH_SIZE', '25')),
  llmDispositionMaxConcurrent: parseInt(getEnv('LLM_DISPO_MAX_CONCURRENT', '5')),
  llmDispositionTimeoutMs: parseInt(getEnv('LLM_DISPO_TIMEOUT_MS', '60000')),
  llmDispositionPromptCharLimit: parseInt(getEnv('LLM_DISPO_PROMPT_CHAR_LIMIT', '2500')),
  llmDispositionMaxOutputTokens: parseInt(getEnv('LLM_DISPO_MAX_OUTPUT_TOKENS', '1800')),
};
