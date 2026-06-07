---
title: "Gaps in Operational Visibility for Post-Quantum Cryptographic Readiness in Networked Computing Environments"
abbrev: "PQC Readiness Observability Gaps"
docname: draft-vicente-pquip-pqc-readiness-gaps-01
category: info
submissiontype: independent
ipr: trust200902
area: Security
workgroup: Post-Quantum Use In Protocols
keyword:
  - post-quantum
  - PQC
  - observability
  - PKI
  - telemetry
  - CNSA 2.0
  - HNDL

author:
  -
    ins: B. Vicente
    name: Brian Vicente
    organization: Sanctum SecOps LLC
    email: bvicente@sanctumsecops.com
    city: Pine City
    region: NY
    country: United States of America

normative:
  RFC2119:
  RFC8174:
  RFC5280:
  RFC8555:
  RFC7011:
  RFC7696:
  RFC9794:
  RFC6960:
  RFC6277:
  RFC9162:

informative:
  RFC9763:
  HYBRID-TLS:
    title: "Hybrid key exchange in TLS 1.3"
    author:
      - ins: D. Stebila
    seriesinfo:
      Internet-Draft: draft-ietf-tls-hybrid-design-16
    date: 2025
    target: https://datatracker.ietf.org/doc/html/draft-ietf-tls-hybrid-design-16
  MOSCA:
    title: "Cybersecurity in an Era with Quantum Computers: Will We Be Ready?"
    author:
      - ins: M. Mosca
    seriesinfo:
      IEEE Security and Privacy: "16(5):38-41"
    date: 2018
  CNSA20:
    title: "Commercial National Security Algorithm Suite 2.0"
    author:
      - org: NSA
    seriesinfo:
      NSA: CNSA 2.0
    date: September 2022
  NIST-PQC:
    title: "Post-Quantum Cryptography Standards: FIPS 203, 204, 205"
    author:
      - org: NIST
    seriesinfo:
      NIST: FIPS 203/204/205
    date: August 2024

--- abstract

Network operators, PKI administrators, and compliance officers currently lack standardized mechanisms for continuously observing the post-quantum cryptographic (PQC) readiness posture of networked computing infrastructure. Existing network monitoring standards, PKI management protocols, and certificate status protocols do not define data models, collection methods, or scoring frameworks for assessing whether TLS endpoints, certificate authority infrastructure, and associated protocol components have migrated to quantum-resistant algorithms. This document describes the observability gap and derives the functional requirements that a standards-based PQC readiness monitoring framework must satisfy.

--- middle

# Introduction

The migration from classical to post-quantum cryptographic algorithms
is operationally complex.  An organization may operate hundreds or
thousands of TLS endpoints, certificate authority responders, API
gateways, and load balancers, each independently negotiating
cryptographic algorithms.  Compliance with mandates such as NSA CNSA
2.0 requires not only deploying PQC-capable infrastructure but also
verifying, continuously, that deployed infrastructure is actually
using PQC algorithms in practice.

Existing network monitoring frameworks — including IPFIX [RFC7011],
SNMP-based management, and flow-based telemetry — do not define data
models or collection semantics for cryptographic algorithm metadata

extracted from live protocol negotiations.  Certificate management
protocols such as ACME [RFC8555] and OCSP [RFC6960] convey
certificate status but not operational algorithm usage at runtime.

This document identifies the functional requirements that a
standards-compliant PQC readiness observability framework must
satisfy, describes gaps in existing standards, and motivates future
protocol work.  No new protocol mechanisms are specified.

## Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and
"OPTIONAL" in this document are to be interpreted as described in BCP
14 [RFC2119] [RFC8174] when, and only when, they appear in all
capitals.

# Problem Statement

## The Operational Visibility Gap

An administrator seeking to determine the PQC readiness posture of
their infrastructure today must manually inspect individual TLS
handshakes, parse certificate chain metadata, and cross-reference
OCSP and CRL signing algorithms.  No existing standard defines:

*  A telemetry data model for cryptographic algorithm observations
   extracted from live network protocol negotiations.

*  A readiness classification taxonomy distinguishing quantum-
   vulnerable, hybrid-transitional, and fully PQC-compliant
   configurations.

*  A method for aggregating per-endpoint algorithm observations into
   an organization-level PQC readiness metric suitable for reporting
   to management or regulators.

*  A mechanism for mapping observed algorithm posture against
   regulatory compliance deadline frameworks and generating gap
   analyses.

## Hybrid Algorithm Complexity

The IETF hybrid key exchange draft [HYBRID-TLS] and RFC 9794
[RFC9794] define hybrid cryptographic configurations combining
classical and PQC algorithms (e.g., X25519+ML-KEM-768, ECDSA-P256+ML-
DSA-65).  These hybrid configurations occupy a transitional security
posture — stronger than purely classical configurations but not yet
fully PQC-compliant.  Existing monitoring tools provide no mechanism
to detect hybrid configurations, distinguish them from classical or
fully PQC configurations, or assign them an appropriate intermediate
compliance status.

## Algorithm Agility Without Visibility

RFC 7696 [RFC7696] provides protocol design guidelines for algorithm
agility — enabling selection of algorithms without hard-coded
dependencies.  However, algorithm agility without operational
visibility creates a compliance risk: infrastructure that is
algorithm-agile by design may silently negotiate quantum-vulnerable
algorithms in production, with no monitoring system capable of
detecting this condition.

# Terminology

PQC Readiness:  The degree to which a networked computing
   environment's cryptographic algorithm usage in active protocol
   negotiations and certificate infrastructure is consistent with
   post-quantum cryptographic requirements.

Quantum-Vulnerable Algorithm:  A cryptographic algorithm whose
   security is broken or significantly weakened by a CRQC, including
   RSA, ECDSA, ECDH, and DSA.

Hybrid-Transitional Configuration:  A cryptographic configuration
   combining a classical algorithm and a post-quantum algorithm as
   defined in [RFC9794].

PQC-Compliant Algorithm:  A cryptographic algorithm standardized by
   NIST in FIPS 203, FIPS 204, or FIPS 205 (ML-KEM, ML-DSA, or SLH-
   DSA), used without classical algorithm dependency.

CRQC:  Cryptographically Relevant Quantum Computer, as defined in
   context of Mosca's inequality [MOSCA].

HNDL:  Harvest Now, Decrypt Later.  A threat model in which an
   adversary records encrypted data today for future decryption once
   a CRQC becomes available.

Algorithm Observation Point:  A network location at which
   cryptographic protocol metadata — cipher suite, key exchange
   algorithm, signature algorithm — can be passively observed from
   live protocol negotiations without decrypting application
   payloads.

# Gaps in Existing Standards

## OCSP Algorithm Agility (RFC 6277)

RFC 6277 [RFC6277] specifies rules for server signature algorithm
selection in OCSP responses.  While this enables algorithm agility in
certificate status responses, it does not define a mechanism for
monitoring whether OCSP responders are issuing responses signed with
PQC algorithms, or for aggregating OCSP signing algorithm
observations across an infrastructure.

## Certificate Transparency (RFC 9162)

RFC 9162 [RFC9162] defines Certificate Transparency (CT) as an
append-only log mechanism for public accountability of CA issuance.
CT logs record issued certificates but do not provide:

*  Real-time observation of the algorithms actually negotiated in
   live TLS handshakes.

*  Aggregated readiness metrics across an organization's
   infrastructure.

*  Mapping of observed posture against compliance deadline profiles.

## IPFIX and Flow Telemetry (RFC 7011)

The IP Flow Information Export (IPFIX) protocol [RFC7011] defines a
framework for exporting flow-based network telemetry.  The IPFIX
information elements do not include fields for cryptographic
algorithm identifiers observed in TLS handshakes, preventing existing
flow telemetry infrastructure from being used for PQC readiness
monitoring without extension.

## TLS 1.3 Hybrid Key Exchange

The IETF draft for hybrid key exchange in TLS 1.3 [HYBRID-TLS]
defines NamedGroup code points for hybrid constructions such as
X25519MLKEM768.  While this enables hybrid key exchange negotiation,
no monitoring standard defines how to collect, aggregate, or report
on the prevalence and distribution of these hybrid algorithm
selections across a deployed infrastructure.

# Functional Requirements for a PQC Readiness Observability Framework

## Telemetry Collection

REQ-OBS-1: The framework MUST define a data model for cryptographic
algorithm observations extracted from live network protocol
negotiations, including at minimum: cipher suite identifiers, key
exchange algorithm identifiers, digital signature algorithm
identifiers, and certificate chain algorithm attributes.

REQ-OBS-2: The framework MUST support passive observation of
cryptographic protocol metadata without requiring decryption of
application-layer payload data.

REQ-OBS-3: The framework SHOULD support observation at multiple
infrastructure tiers, including TLS termination points, certificate
authority endpoints, OCSP responders, CRL distribution points, API
gateways, and load balancers.

## Algorithm Classification

REQ-CLASS-1: The framework MUST classify each observed cryptographic
algorithm into one of at least three readiness categories: quantum-
vulnerable, hybrid-transitional, and PQC-compliant.

REQ-CLASS-2: The framework MUST correctly identify and classify
hybrid cryptographic configurations as defined in [RFC9794],
including at minimum ML-KEM-based hybrid key exchange and ML-DSA-
based hybrid signature configurations.

## Readiness Assessment

REQ-SCORE-1: The framework SHOULD support computation of a per-
endpoint readiness metric derived from the classified algorithms
observed at that endpoint.

REQ-SCORE-2: The framework SHOULD support computation of an aggregate
organizational readiness metric from per-endpoint observations, with
the ability to weight endpoints by operational criticality.

REQ-SCORE-3: The framework MUST support time-series storage of
readiness observations to enable historical trend analysis of PQC
migration progress.

## Compliance Mapping

REQ-COMP-1: The framework MUST support mapping of per-endpoint
readiness observations against configurable compliance deadline
profiles, including at minimum the CNSA 2.0 migration timeline.

REQ-COMP-2: The framework MUST generate gap reports identifying
endpoints and certificate infrastructure components that require
algorithm migration before applicable deadlines.

## Remediation Guidance

REQ-REM-1: The framework SHOULD produce prioritized remediation
guidance identifying which endpoints require migration action,
ordered by the combination of compliance deadline proximity and
operational risk exposure.

REQ-REM-2: The framework SHOULD support analysis of the dependency
relationships between endpoints to assist operators in planning safe
migration sequences.

# IPR Considerations

The author may hold or apply for patents covering subject matter related to
this document. Disclosure of any such patents will be made in accordance with
the procedures defined in BCP 79. Publication of this Internet-Draft does not
constitute any patent license, express or implied, from the author. License
terms, if any, are not yet known.

This work product is the original work of the named author and is offered to
the IETF community as an Independent Submission. No portion of this document
is offered as a trade secret. All technical disclosures herein are intended
as public prior art as of the publication date of the initial -00 revision.

# Security Considerations

The primary threat model motivating this document is HNDL:
adversaries that capture data encrypted with quantum-vulnerable
algorithms today can decrypt it once a CRQC becomes available.  For
PKI infrastructure, the additional concern is that a CA signing key
protected by a quantum-vulnerable algorithm compromises the entire
certificate hierarchy under that key, affecting all relying parties.

Mosca's inequality [MOSCA] quantifies the urgency: if the estimated
time to CRQC is less than the sum of the time required to complete
migration and the required confidentiality lifetime of the protected
data, then the organization is already at risk.  A readiness
observability framework enables operators to measure their current
posture against this threshold continuously.

Passive observation of cryptographic metadata from live network
traffic introduces a privacy consideration: the metadata observed
(certificate fingerprints, endpoint identifiers, algorithm
selections) may be sensitive in some deployment contexts.
Implementations MUST apply appropriate access controls to telemetry
collection and storage infrastructure.

A readiness observability framework MUST NOT require decryption of
application-layer payload data.  Observation MUST be limited to
cryptographic protocol metadata visible in plaintext during the
handshake phase.

# IANA Considerations

This document has no IANA actions.  Future work specifying a concrete
PQC readiness telemetry data model may require IANA registration of
new IPFIX Information Elements or YANG data model namespaces.

# References

## Normative References

[RFC2119]  Bradner, S., "Key words for use in RFCs to Indicate
           Requirement Levels", BCP 14, RFC 2119, March 1997,
           <https://www.rfc-editor.org/rfc/rfc2119>.

[RFC8174]  Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC
           2119 Key Words", RFC 8174, May 2017,
           <https://www.rfc-editor.org/rfc/rfc8174>.

[RFC5280]  Cooper, D., "Internet X.509 PKI Certificate and CRL
           Profile", RFC 5280, May 2008,
           <https://www.rfc-editor.org/rfc/rfc5280>.

[RFC8555]  Barnes, R., "Automatic Certificate Management Environment
           (ACME)", RFC 8555, March 2019,
           <https://www.rfc-editor.org/rfc/rfc8555>.

[RFC7011]  Claise, B., "Specification of the IP Flow Information
           Export (IPFIX) Protocol", RFC 7011, September 2013,
           <https://www.rfc-editor.org/rfc/rfc7011>.

[RFC7696]  Housley, R., "Guidelines for Cryptographic Algorithm
           Agility", RFC 7696, November 2015,
           <https://www.rfc-editor.org/rfc/rfc7696>.

[RFC9794]  Hale, N., "Terminology for Post-Quantum Traditional Hybrid
           Schemes", RFC 9794, June 2025,
           <https://www.rfc-editor.org/rfc/rfc9794>.

[RFC6960]  Santesson, S., "X.509 Internet PKI Online Certificate
           Status Protocol (OCSP)", RFC 6960, June 2013,
           <https://www.rfc-editor.org/rfc/rfc6960>.

[RFC6277]  Santesson, S., "Online Certificate Status Protocol
           Algorithm Agility", RFC 6277, June 2011,
           <https://www.rfc-editor.org/rfc/rfc6277>.

[RFC9162]  Laurie, B., "Certificate Transparency Version 2.0",
           RFC 9162, December 2021,
           <https://www.rfc-editor.org/rfc/rfc9162>.

## Informative References

[RFC9763]  Ounsworth, M., "Related Certificates for Use in Multiple
           Authentications", RFC 9763, April 2025,
           <https://www.rfc-editor.org/rfc/rfc9763>.

[HYBRID-TLS]
           Stebila, D., "Hybrid key exchange in TLS 1.3", Work in
           Progress, Internet-Draft, draft-ietf-tls-hybrid-design-16,
           2025, <https://datatracker.ietf.org/doc/html/draft-ietf-
           tls-hybrid-design-16>.

[MOSCA]    Mosca, M., "Cybersecurity in an Era with Quantum
           Computers: Will We Be Ready?", IEEE Security and
           Privacy 16(5):38-41, 2018.

[CNSA20]   NSA, "Commercial National Security Algorithm Suite 2.0",
           NSA CNSA 2.0, September 2022.

[NIST-PQC] NIST, "Post-Quantum Cryptography Standards: FIPS 203, 204,
           205", NIST FIPS 203/204/205, August 2024.

--- back
