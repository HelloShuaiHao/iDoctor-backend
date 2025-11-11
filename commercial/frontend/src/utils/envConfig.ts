/**
 * Environment configuration service for the demo feature
 */

import type { DemoConfig, LLMProvider } from '../types/demo';

const VALID_PROVIDERS: LLMProvider[] = ['openai', 'anthropic', 'none', 'mock'];

/**
 * Get and validate environment configuration
 * @returns Validated configuration object
 */
export function getEnvConfig(): Readonly<DemoConfig> {
  const provider = (import.meta.env.VITE_LLM_PROVIDER || 'none') as string;
  const apiKey = import.meta.env.VITE_LLM_API_KEY || '';
  const model = import.meta.env.VITE_LLM_MODEL || '';
  const debug = import.meta.env.VITE_LLM_DEBUG === 'true';

  // Validate provider
  let validatedProvider: LLMProvider = 'none';
  if (VALID_PROVIDERS.includes(provider as LLMProvider)) {
    validatedProvider = provider as LLMProvider;
  } else if (provider !== 'none') {
    console.warn(
      `[Demo Config] Invalid LLM provider: "${provider}". Defaulting to "none". Valid options: ${VALID_PROVIDERS.join(', ')}`
    );
  }

  // Warn if provider is set but API key is missing
  if (validatedProvider !== 'none' && validatedProvider !== 'mock' && !apiKey) {
    console.warn(
      `[Demo Config] LLM provider is set to "${validatedProvider}" but VITE_LLM_API_KEY is not configured. LLM features will be disabled.`
    );
    validatedProvider = 'none';
  }

  // Set default model based on provider
  let defaultModel = model;
  if (!defaultModel) {
    if (validatedProvider === 'openai') {
      defaultModel = 'gpt-4o-mini';
    } else if (validatedProvider === 'anthropic') {
      defaultModel = 'claude-3-5-haiku-20241022';
    }
  }

  const config: DemoConfig = {
    llmProvider: validatedProvider,
    llmApiKey: apiKey,
    llmModel: defaultModel,
    llmDebug: debug,
  };

  if (debug) {
    console.log('[Demo Config] Configuration loaded:', {
      ...config,
      llmApiKey: apiKey ? '[REDACTED]' : '(not set)',
    });
  }

  return Object.freeze(config);
}

/**
 * Check if LLM features are enabled
 * @param config Configuration object
 * @returns True if LLM features should be available
 */
export function isLLMEnabled(config: DemoConfig): boolean {
  return config.llmProvider !== 'none' && !!config.llmApiKey;
}
