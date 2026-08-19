# Job Exclusions

This file defines technologies, development ecosystems, and job types that should generally be avoided during automated job discovery.

This file is not a general technology reference. Its purpose is specifically to help the job-search system distinguish between:

1. Jobs that match the current professional software-engineering background documented in `Documentation/current-skills.md`.
2. Jobs containing incidental technologies outside that background.
3. Jobs whose primary development stack is outside the current professional skill set and therefore should normally be excluded from job results.

The job scanner should eventually use both `Documentation/current-skills.md` and `Documentation/job-exclusions.md` when evaluating discovered positions.

## Important Classification Rule

An excluded technology appearing anywhere in a job description must not automatically cause the job to be rejected.

Determine whether the excluded technology represents the primary engineering stack or a meaningful required responsibility.

For example, a Senior Full Stack Developer position with primary requirements of C#, .NET, React, TypeScript, and Azure should not be rejected merely because the description also mentions that the organization maintains some Java applications.

However, a Senior Software Engineer position with primary requirements of Java, Spring Boot, Hibernate, JPA, and Kafka should normally be rejected, even if React appears as a preferred or incidental skill.

# Excluded Development Ecosystems

## Java / JVM

The following technologies should be treated as indicators of a Java/JVM-centered position:

* Java
* Jakarta EE
* Java EE
* J2EE
* Spring
* Spring Boot
* Spring MVC
* Spring Security
* Spring Cloud
* Hibernate
* JPA
* Maven
* Gradle
* Tomcat
* WildFly
* JBoss
* Quarkus
* Micronaut
* Struts
* JSF
* Thymeleaf
* Kotlin when used as a JVM/backend language
* Groovy
* Grails

A position primarily requiring this ecosystem should normally be excluded.

## Ruby

The following technologies should be treated as indicators of a Ruby-centered position:

* Ruby
* Ruby on Rails
* Rails
* Sinatra
* Hanami
* Active Record
* RSpec
* Minitest
* Bundler
* RubyGems
* Rake
* Puma
* Sidekiq
* Hotwire
* Turbo
* Stimulus when specifically used as part of a Rails stack
* ERB
* Haml

A position primarily requiring Ruby or Ruby on Rails should normally be excluded.

## Native iOS

The following technologies should be treated as indicators of native Apple application development:

* Swift
* Objective-C
* SwiftUI
* UIKit
* AppKit
* Xcode
* Cocoa
* Cocoa Touch
* CocoaPods
* Core Data
* Core Animation
* Core Location
* Core Bluetooth
* Combine
* CloudKit
* StoreKit
* TestFlight
* XCTest
* iOS SDK
* iPadOS SDK
* watchOS
* tvOS
* visionOS
* Metal

Positions primarily focused on native iOS, iPadOS, watchOS, macOS, tvOS, or visionOS development should normally be excluded.

## Android

The following technologies should be treated as indicators of native Android development:

* Android
* Android SDK
* Android Studio
* Kotlin when used for Android development
* Java when used for Android development
* Jetpack
* Jetpack Compose
* Android Jetpack
* Room
* ViewModel
* LiveData
* WorkManager
* Retrofit
* Dagger
* Hilt
* Espresso
* Robolectric
* Google Play Services
* Google Play Console

Positions primarily focused on Android application development should normally be excluded.

## Cross-Platform Mobile

Treat the following technologies as indicators of mobile-development positions:

* React Native
* Flutter
* Dart
* Xamarin
* .NET MAUI
* Ionic
* Capacitor
* Cordova
* PhoneGap
* NativeScript
* Expo

These distinctions are particularly important for technologies that superficially overlap with current skills.

`React` is a current skill. `React Native` should not automatically be treated as equivalent React experience.

`.NET` is a current skill. `.NET MAUI` and `Xamarin` should not automatically be treated as matching .NET web/backend experience.

A position primarily requiring React Native, MAUI, Xamarin, Flutter, or another mobile framework should normally be excluded.

# Mobile-Specific Job Indicators

The following concepts should increase confidence that a position is primarily a mobile-development position:

* Native Mobile Development
* Mobile Application Development
* iOS Development
* Android Development
* App Store Deployment
* Google Play Deployment
* APNs
* Firebase Cloud Messaging
* Mobile Deep Linking
* Mobile Device APIs
* Mobile Offline Storage
* Mobile UI Development

These terms alone should not necessarily reject a position.

Use them together with the job title, required technologies, responsibilities, and primary engineering stack.

# Shared / Neutral Technologies

Some technologies are widely used across .NET, Java, Ruby, mobile, and other development ecosystems.

They must not be used by themselves to determine that a position belongs to an excluded ecosystem.

Examples include:

* AWS
* Azure
* Docker
* Kubernetes
* SQL
* SQL Server
* REST
* REST APIs
* Microservices
* CI/CD
* Git
* Cloud Infrastructure
* Distributed Systems
* API Development
* Authentication
* OAuth
* OpenID Connect
* Agile
* Automated Testing

For example:

* Java + Spring Boot + AWS + Kubernetes is still primarily a Java position.
* C# + .NET + React + AWS + Kubernetes is potentially a strong match.

AWS and Kubernetes do not determine the primary software-development ecosystem.

# Job Title Analysis

Do not determine job relevance from the title alone.

Generic titles such as:

* Software Engineer
* Senior Software Engineer
* Staff Software Engineer
* Full Stack Engineer
* Backend Engineer
* Application Developer

provide insufficient information by themselves.

Inspect the actual technology requirements and responsibilities.

For example, `Senior Software Engineer` could represent:

* C#/.NET
* Java/Spring
* Ruby/Rails
* Python
* iOS
* Android
* React Native
* another ecosystem entirely

Determine the primary engineering stack before deciding whether the job belongs in job results.

# Excluded Employer Types

Recruiting, staffing, placement, and consulting firms should normally be excluded when they are the listed hiring company rather than the direct employer.

Indicators include:

* Staffing agency
* Staffing firm
* Staffing services
* Technology staffing
* IT staffing
* Recruiting agency
* Recruiting firm
* Recruitment agency
* Recruitment firm
* Talent agency
* Talent solutions
* Workforce solutions
* Staff augmentation
* Contract staffing
* Placement services
* Professional staffing
* Consulting and staffing
* Technology consulting and staffing

Known excluded examples:

* Synersys Technologies

These employers should generally be treated as bogus or low-value job postings because they often represent intermediary listings rather than direct hiring opportunities.

Acceptable recruiting agencies:

* Apex Systems
* TEKsystems
* Kforce Technology Staffing

These agencies should not be automatically excluded. If the scanner cannot derive a useful careers URL for one of them, it should flag the company for manual verification instead.

# Exclusion Decision Rules

When evaluating a discovered job, classify its primary engineering ecosystem before calculating skill compatibility.

Use three possible outcomes:

## INCLUDE

Use when the primary stack substantially aligns with `Documentation/current-skills.md`.

Example:

* C#
* .NET
* React
* TypeScript
* Azure

## EXCLUDE

Use when the primary required engineering stack substantially aligns with an excluded ecosystem.

Examples:

* Java + Spring Boot + Hibernate
* Ruby + Rails
* Swift + SwiftUI + UIKit
* Kotlin + Android + Jetpack Compose
* React Native + iOS + Android
* Flutter + Dart

## REVIEW

Use when the primary stack cannot confidently be determined or the position contains a meaningful mixture of matching and excluded technologies.

Do not automatically discard REVIEW positions. They should remain available for later evaluation.

# Required vs Preferred

Give substantially more weight to required technologies than preferred technologies.

For example:

Required:

* C#
* .NET
* React
* Azure

Preferred:

* Java experience

should normally remain an INCLUDE.

However:

Required:

* Java
* Spring Boot
* Hibernate

Preferred:

* C#
* React

should normally be an EXCLUDE.

# Primary Stack Rule

When determining whether to exclude a job, evaluate:

1. Job title
2. Required technologies
3. Required professional experience
4. Core responsibilities
5. Technologies repeatedly emphasized throughout the description
6. Preferred technologies
7. Incidental technology mentions

Weight them approximately in that order.

Do not perform simple keyword counting.

Determine what technologies the developer would actually spend most of their time using.

# Future Job Database Usage

This documentation is intended to support future job-scanning functionality.

Future implementations may use `Documentation/current-skills.md` to determine:

* Positive skill matches
* Relevant technologies
* Relevant architecture experience
* Job compatibility

And `Documentation/job-exclusions.md` to determine:

* Primary-stack incompatibility
* Jobs to avoid
* Mobile-development positions
* Java/JVM positions
* Ruby positions
* Other explicitly excluded development ecosystems

The combination should allow the system to distinguish between:

`This job mentions technologies I don't know`

and:

`This job fundamentally requires a development stack I don't use.`

Those are not the same condition.

# Future Job Record Classification

Design this documentation so future job-scanning functionality can reasonably produce classifications such as:

`INCLUDE`

`EXCLUDE`

`REVIEW`

Future job records may eventually contain fields such as:

```json
{
  "classification": "INCLUDE",
  "primaryStack": [
    "C#",
    ".NET",
    "React",
    "Azure"
  ],
  "matchedSkills": [
    "C#",
    ".NET",
    "React",
    "Azure"
  ],
  "excludedSkillsFound": [],
  "exclusionReason": null
}
```

An excluded example could eventually resemble:

```json
{
  "classification": "EXCLUDE",
  "primaryStack": [
    "Java",
    "Spring Boot",
    "Hibernate"
  ],
  "matchedSkills": [
    "React",
    "AWS"
  ],
  "excludedSkillsFound": [
    "Java",
    "Spring Boot",
    "Hibernate"
  ],
  "exclusionReason": "Primary backend stack is Java/Spring rather than the candidate's current development stack."
}
```

These are examples for future functionality.

Do not modify the current Job Database implementation as part of this task.
