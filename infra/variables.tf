variable "openai_token" {
  description = "OpenAI API key injected as a GitHub Actions secret"
  type        = string
  sensitive   = true
}
