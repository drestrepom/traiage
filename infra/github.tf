resource "github_repository" "triage" {
  name = "traiage"
}

resource "github_actions_secret" "openai_token" {
  repository      = github_repository.triage.name
  secret_name     = "OPENAI_API_KEY"
  plaintext_value = var.openai_token
}
