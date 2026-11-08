# Publish at docs/product/features/<scope>.feature beside PRD.md.
# Given is the persona and initial data, When the ordered actions, Then the assertions in order.
# Background steps are Given steps of every scenario. And/But continue the previous keyword.
# Each scenario has exactly one @TEST tag naming its Test Obligations row.
# Scenario id is <TEST-ID>/<slug of the scenario name>.
# @platform:, @auth: and @env: tags override the run profile for that scenario only.
@PRD-001
Feature: [Capability in the owner's words]

  Background:
    Given [persona] of [tenant and account state]
    And [initial data every scenario starts from]

  @TEST-001 @platform:web @auth:mock
  Scenario: [Observable success outcome]
    When [persona] [first action]
    And [next action]
    Then [first assertion the persona can observe]
    And [second assertion]

  @TEST-002
  Scenario: [Refused or recovered outcome]
    When [persona] [action that must be refused]
    Then [refusal the persona sees]
    But [data that stays unchanged]
