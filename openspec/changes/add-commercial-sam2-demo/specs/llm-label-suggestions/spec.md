# llm-label-suggestions Specification Delta

## Purpose

Defines requirements for integrating Large Language Model (LLM) APIs to provide intelligent label suggestions based on segmented image regions in the Commercial SAM2 Demo feature.

## ADDED Requirements

### Requirement: LLM Service Configuration

The application SHALL support configuration of third-party LLM API providers for label suggestion functionality.

#### Scenario: Environment variable configuration
- **WHEN** application loads environment configuration
- **THEN** the system SHALL read `VITE_LLM_PROVIDER` variable with allowed values: `"openai"`, `"anthropic"`, or `"none"`
- **AND** the system SHALL read `VITE_LLM_API_KEY` variable for API authentication
- **AND** if `VITE_LLM_PROVIDER` is `"none"` or `VITE_LLM_API_KEY` is empty, LLM features SHALL be disabled
- **AND** the "Get AI Suggestions" button SHALL be hidden when LLM is disabled

#### Scenario: OpenAI provider configuration
- **WHEN** `VITE_LLM_PROVIDER` is set to `"openai"`
- **THEN** the system SHALL use OpenAI API endpoint: `https://api.openai.com/v1/chat/completions`
- **AND** the default model SHALL be `"gpt-4o-mini"` (overridable via `VITE_LLM_MODEL`)
- **AND** requests SHALL include header: `Authorization: Bearer ${VITE_LLM_API_KEY}`
- **AND** requests SHALL include header: `Content-Type: application/json`

#### Scenario: Anthropic provider configuration
- **WHEN** `VITE_LLM_PROVIDER` is set to `"anthropic"`
- **THEN** the system SHALL use Anthropic API endpoint: `https://api.anthropic.com/v1/messages`
- **AND** the default model SHALL be `"claude-3-5-haiku-20241022"` (overridable via `VITE_LLM_MODEL`)
- **AND** requests SHALL include header: `x-api-key: ${VITE_LLM_API_KEY}`
- **AND** requests SHALL include header: `anthropic-version: 2023-06-01`
- **AND** requests SHALL include header: `Content-Type: application/json`

#### Scenario: Invalid configuration
- **WHEN** `VITE_LLM_PROVIDER` has an unrecognized value
- **THEN** the system SHALL log a warning: "Invalid LLM provider: {value}. LLM features disabled."
- **AND** LLM features SHALL be disabled (same as `"none"`)
- **AND** the application SHALL continue to function normally without LLM

---

### Requirement: Label Suggestion Request

The system SHALL send properly formatted requests to LLM APIs with image and segmentation context.

#### Scenario: Trigger suggestion request
- **WHEN** user clicks "Get AI Suggestions" button
- **AND** a segmentation mask is available
- **THEN** the button SHALL show loading state: spinner icon and text "Generating..."
- **AND** the button SHALL be disabled during request
- **AND** a suggestion request SHALL be initiated

#### Scenario: Prepare image data for LLM
- **WHEN** suggestion request is initiated
- **THEN** the system SHALL extract the segmented region from the original image using the mask bounding box
- **AND** the extracted region SHALL be resized to max 512x512 pixels (maintaining aspect ratio) to reduce payload size
- **AND** the resized image SHALL be converted to base64-encoded PNG format
- **AND** the base64 string SHALL be prefixed with `data:image/png;base64,`

#### Scenario: Build OpenAI request payload
- **WHEN** LLM provider is OpenAI
- **THEN** the request body SHALL be:
```json
{
  "model": "<configured_model>",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "<prompt_text>"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,<image_data>"
          }
        }
      ]
    }
  ],
  "max_tokens": 150,
  "temperature": 0.7
}
```

#### Scenario: Build Anthropic request payload
- **WHEN** LLM provider is Anthropic
- **THEN** the request body SHALL be:
```json
{
  "model": "<configured_model>",
  "max_tokens": 150,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "<base64_data_without_prefix>"
          }
        },
        {
          "type": "text",
          "text": "<prompt_text>"
        }
      ]
    }
  ]
}
```

#### Scenario: Prompt engineering
- **WHEN** building the prompt text for LLM
- **THEN** the prompt SHALL be:
```
You are an image analysis assistant helping users label segmented regions in images.

Analyze the provided image which shows a segmented region (the highlighted area). Based on the shape, texture, color, and visual context, suggest 3-5 concise, descriptive labels that best describe what this region represents.

Guidelines:
- Be specific and descriptive
- Keep labels 1-3 words each
- Focus on what the region IS, not just visual properties
- Use anatomical/medical terms if the image appears medical
- Use common object names for general images

Return ONLY a JSON array of label strings, e.g.:
["kidney", "soft tissue", "organ"]

Do not include any other text or explanation.
```

---

### Requirement: Label Suggestion Response Handling

The system SHALL parse LLM responses and display suggestions to the user.

#### Scenario: Successful OpenAI response
- **WHEN** OpenAI API returns HTTP 200 with valid JSON
- **THEN** the system SHALL extract the text content from `response.choices[0].message.content`
- **AND** parse the content as JSON array of strings
- **AND** validate that each suggestion is a non-empty string
- **AND** limit to maximum 5 suggestions (take first 5 if more returned)
- **AND** display suggestions as clickable chips below the label input

#### Scenario: Successful Anthropic response
- **WHEN** Anthropic API returns HTTP 200 with valid JSON
- **THEN** the system SHALL extract the text content from `response.content[0].text`
- **AND** parse the content as JSON array of strings
- **AND** validate that each suggestion is a non-empty string
- **AND** limit to maximum 5 suggestions (take first 5 if more returned)
- **AND** display suggestions as clickable chips below the label input

#### Scenario: Suggestion chip display
- **WHEN** suggestions are successfully retrieved
- **THEN** each suggestion SHALL be rendered as a chip with:
  - Rounded corners (`rounded-full`)
  - Light background (`bg-blue-50`)
  - Border (`border border-blue-200`)
  - Hover effect (`hover:bg-blue-100`)
  - Text color (`text-blue-700`)
  - Padding (`px-3 py-1`)
  - Small font (`text-sm`)
- **AND** chips SHALL be displayed in a horizontal flex container with wrapping
- **AND** clicking a chip SHALL populate the label input with that text
- **AND** clicking a chip SHALL focus the label input for editing

#### Scenario: LLM response timeout
- **WHEN** LLM API does not respond within 15 seconds
- **THEN** the request SHALL be aborted
- **AND** an error toast SHALL display: "AI suggestion timed out. Please try again or enter labels manually."
- **AND** the "Get AI Suggestions" button SHALL return to normal state (enabled)
- **AND** the label input SHALL remain available for manual entry

#### Scenario: LLM API error (4xx, 5xx)
- **WHEN** LLM API returns an error status code
- **THEN** the system SHALL log the error details to console
- **AND** an error toast SHALL display: "AI suggestions unavailable. Please enter labels manually."
- **AND** the "Get AI Suggestions" button SHALL return to normal state
- **AND** the label input SHALL remain available

#### Scenario: Invalid JSON response
- **WHEN** LLM returns non-JSON or malformed JSON content
- **THEN** the system SHALL attempt to extract array from markdown code blocks (e.g., ```json [...] ```)
- **AND** if extraction fails, log warning: "Failed to parse LLM response as JSON"
- **AND** display error toast: "AI returned unexpected format. Please try again."
- **AND** fall back to manual label entry

#### Scenario: Empty suggestions
- **WHEN** LLM returns an empty array `[]` or no valid suggestions
- **THEN** an informational toast SHALL display: "AI couldn't generate suggestions for this region. Please enter labels manually."
- **AND** the label input SHALL remain available

---

### Requirement: Cost and Rate Limiting

The system SHALL implement client-side mechanisms to control LLM API usage and costs.

#### Scenario: Request caching by mask hash
- **WHEN** user requests suggestions for a segmentation
- **THEN** the system SHALL compute a hash of the mask data (using bounding box coordinates as key)
- **AND** check sessionStorage for cached suggestions with key: `llm_suggestions_<hash>`
- **AND** if cache hit (less than 30 minutes old), return cached suggestions immediately
- **AND** if cache miss or expired, make API request
- **AND** store successful response in sessionStorage with timestamp

#### Scenario: Request debouncing
- **WHEN** user clicks "Get AI Suggestions" button multiple times rapidly
- **THEN** only the first click SHALL trigger an API request
- **AND** subsequent clicks within 3 seconds SHALL be ignored
- **AND** a toast SHALL display: "Please wait for current suggestion request to complete"

#### Scenario: Request count tracking
- **WHEN** application loads
- **THEN** the system SHALL track LLM request count in sessionStorage: `llm_request_count`
- **WHEN** a new request is made
- **THEN** the counter SHALL increment
- **WHEN** counter reaches 10 requests per session
- **THEN** a warning toast SHALL display: "You've made 10 AI suggestion requests. Consider using manual labels to reduce API costs."
- **AND** the button SHALL change text to "Get AI Suggestions (limited)"
- **AND** requests SHALL continue to function normally

---

### Requirement: User Feedback and Transparency

The system SHALL provide clear feedback about LLM suggestion status and limitations.

#### Scenario: LLM feature availability indicator
- **WHEN** LLM is properly configured
- **THEN** a small badge SHALL appear near the "Get AI Suggestions" button with text: "Powered by {provider}" (e.g., "Powered by OpenAI")
- **AND** badge SHALL have an info icon that shows tooltip on hover: "AI suggestions use {model_name}. {provider} API key required."

#### Scenario: No API key configured
- **WHEN** `VITE_LLM_API_KEY` is not set or empty
- **THEN** the "Get AI Suggestions" button SHALL be hidden
- **AND** a subtle informational message SHALL display: "AI suggestions disabled. Configure LLM API key to enable."
- **AND** a link SHALL be provided: "Learn how to configure" (points to docs)

#### Scenario: First-time LLM usage
- **WHEN** user clicks "Get AI Suggestions" for the first time in a session
- **THEN** a modal/alert SHALL display before making the request:
  - Title: "AI Suggestions Powered by {Provider}"
  - Message: "This feature sends your image to {Provider}'s API. Usage may incur costs based on your API plan. Do you want to continue?"
  - Buttons: "Continue" | "Cancel"
  - Checkbox: "Don't show this again"
- **WHEN** user clicks "Continue"
- **THEN** proceed with suggestion request
- **AND** store preference in sessionStorage: `llm_consent_given: true`
- **WHEN** user clicks "Cancel"
- **THEN** abort request
- **AND** keep button available for future attempts

#### Scenario: Suggestion confidence display
- **WHEN** suggestions are displayed
- **THEN** a disclaimer text SHALL appear below chips: "AI-generated suggestions may not be accurate. Please verify and edit as needed."
- **AND** text SHALL be styled as subtle/secondary (`text-gray-500 text-xs`)

---

### Requirement: Security and Privacy

The system SHALL handle API keys and user data securely.

#### Scenario: API key exposure prevention
- **WHEN** LLM requests are made from client-side
- **THEN** API keys SHALL only be accessed from environment variables (not hardcoded)
- **AND** API keys SHALL NOT be logged to console or error messages
- **AND** API keys SHALL NOT be exposed in network request URLs (only in headers)

#### Scenario: Image data privacy
- **WHEN** sending images to LLM APIs
- **THEN** a privacy notice SHALL be displayed in the modal/alert on first usage: "Images are processed by {Provider}'s API. See {Provider}'s privacy policy for data handling details."
- **AND** user consent SHALL be required before first request (as per "First-time LLM usage" scenario)

#### Scenario: No persistent storage of LLM data
- **WHEN** user closes the demo or browser session
- **THEN** all cached suggestions in sessionStorage SHALL be cleared
- **AND** no image data or LLM responses SHALL be stored in localStorage or cookies
- **AND** no data SHALL be sent to the iDoctor backend (LLM is entirely client-side)

---

### Requirement: Fallback and Degradation

The system SHALL gracefully handle LLM unavailability without breaking the demo experience.

#### Scenario: LLM service completely unavailable
- **WHEN** LLM provider API is unreachable (network error, DNS failure)
- **THEN** the system SHALL catch the network exception
- **AND** display error toast: "Unable to reach AI service. Please check your internet connection or try again later."
- **AND** the demo SHALL remain fully functional for manual label entry
- **AND** all other features (segmentation, export) SHALL work normally

#### Scenario: LLM disabled by configuration
- **WHEN** `VITE_LLM_PROVIDER` is set to `"none"`
- **THEN** the "Get AI Suggestions" button SHALL NOT be rendered at all
- **AND** the label input panel SHALL display only the text input and "Add Label" button
- **AND** the demo SHALL function identically to LLM-enabled mode, minus suggestions

#### Scenario: Partial LLM failure (some suggestions work)
- **WHEN** LLM returns a valid response with some suggestions, but fewer than expected
- **THEN** display whatever suggestions are available (even if just 1)
- **AND** show normal success state
- **AND** log informational message: "LLM returned {count} suggestions"

---

### Requirement: Development and Testing Support

The system SHALL provide tools for testing LLM integration without consuming API quota.

#### Scenario: Mock mode for development
- **WHEN** `VITE_LLM_PROVIDER` is set to `"mock"`
- **THEN** the system SHALL use a mock LLM service that returns hardcoded suggestions
- **AND** mock responses SHALL be: `["region_1", "segment_area", "highlighted_section"]`
- **AND** mock SHALL simulate 2-second delay to mimic real API latency
- **AND** mock SHALL randomly fail 10% of requests to test error handling

#### Scenario: Verbose logging mode
- **WHEN** `VITE_LLM_DEBUG` environment variable is set to `"true"`
- **THEN** the system SHALL log detailed debug information:
  - Request payload (with image data truncated)
  - API endpoint and headers (with API key redacted)
  - Response parsing steps
  - Caching behavior
  - Error stack traces
- **AND** logs SHALL be prefixed with `[LLM-Debug]`
- **AND** logs SHALL only appear in development builds (not production)

---

## MODIFIED Requirements

None. This is a new capability with no modifications to existing requirements.

---

## REMOVED Requirements

None. This is a new capability with no requirements removed.
