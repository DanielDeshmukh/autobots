# Nemotron Safety Policy Generator

## Policy Structure
```markdown
# Safety Policy: <name>
## Scope
<what this policy covers>

## Severity Levels
- **CRITICAL**: System compromise, data breach, service outage
- **HIGH**: Security vulnerability, data exposure
- **MEDIUM**: Performance degradation, minor vulnerability
- **LOW**: Best practice violation, code quality issue

## Detection Rules
<specific patterns to detect>

## Response Actions
<what to do when detected>
```

## JSON Taxonomy Format
```json
{
  "category": "injection|exposure|exploitation|misconfiguration",
  "severity": "critical|high|medium|low",
  "description": "<what was found>",
  "evidence": "<code or log snippet>",
  "remediation": "<how to fix>"
}
```

## Review Checklist
1. **Injection**: SQL, command, template, LDAP injection
2. **Exposure**: Secrets in code, PII in logs, debug endpoints
3. **Exploitation**: Buffer overflow, deserialization, SSRF
4. **Misconfiguration**: Debug mode, verbose errors, weak defaults

## Audit Trail Format
```json
{
  "review_id": "<uuid>",
  "timestamp": "<iso8601>",
  "reviewer": "<cluster name>",
  "files_reviewed": ["<path>"],
  "findings": ["<finding 1>", "<finding 2>"],
  "verdict": "pass|revise",
  "summary": "<overall assessment>"
}
```
