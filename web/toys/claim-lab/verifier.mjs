const VERDICTS = new Set(["untested", "supported", "weakened", "rejected", "unresolved"]);
const CLASSIFICATIONS = new Set(["observation", "hypothesis", "model", "established-result"]);
const REPRODUCTION_STATES = new Set(["not-run", "partial", "reproduced", "failed"]);

function present(value) {
  return typeof value === "string" && value.trim().length > 0;
}

export function verifyClaim(claim, schema) {
  const errors = [];
  const required = Array.isArray(schema?.required) ? schema.required : [];

  if (!claim || typeof claim !== "object" || Array.isArray(claim)) {
    return { valid: false, errors: ["Claim must be a JSON object."], checks: 1 };
  }

  required.forEach((field) => {
    if (!(field in claim)) errors.push(`Missing required field: ${field}`);
  });

  if (!present(claim.id)) errors.push("id must be a non-empty string.");
  if (!present(claim.proposition) || claim.proposition.trim().length < 10) {
    errors.push("proposition must be a specific statement of at least 10 characters.");
  }
  if (!CLASSIFICATIONS.has(claim.classification)) {
    errors.push("classification is not recognized.");
  }
  if (!present(claim.falsification?.condition) || !present(claim.falsification?.measurement)) {
    errors.push("falsification requires both a defeat condition and a measurement.");
  }
  if (!Array.isArray(claim.protocol?.procedure) || claim.protocol.procedure.length < 2) {
    errors.push("protocol requires at least two procedure steps.");
  }
  if (!present(claim.protocol?.success_threshold) || !present(claim.protocol?.failure_threshold)) {
    errors.push("protocol requires success and failure thresholds.");
  }
  if (!Array.isArray(claim.evidence)) errors.push("evidence must be an array.");
  if (!Number.isInteger(claim.reproduction?.attempts) || claim.reproduction.attempts < 0) {
    errors.push("reproduction attempts must be a non-negative integer.");
  }
  if (!Number.isInteger(claim.reproduction?.independent_attempts) ||
      claim.reproduction.independent_attempts < 0) {
    errors.push("independent reproduction attempts must be a non-negative integer.");
  }
  if (!REPRODUCTION_STATES.has(claim.reproduction?.status)) {
    errors.push("reproduction status is not recognized.");
  }
  if (!Array.isArray(claim.criticism) || claim.criticism.length < 1) {
    errors.push("at least one criticism or limitation is required.");
  }
  if (!VERDICTS.has(claim.verdict)) errors.push("verdict is not recognized.");
  if (!Array.isArray(claim.history) || claim.history.length < 1) {
    errors.push("at least one history entry is required.");
  }
  if (!present(claim.human_authority?.owner) ||
      claim.human_authority?.promotion_required !== true) {
    errors.push("human authority and an explicit promotion gate are required.");
  }

  const attempts = claim.reproduction?.attempts ?? 0;
  const independent = claim.reproduction?.independent_attempts ?? 0;
  const evidenceCount = Array.isArray(claim.evidence) ? claim.evidence.length : 0;
  if (independent > attempts) {
    errors.push("independent attempts cannot exceed total attempts.");
  }
  if (claim.verdict === "supported" && evidenceCount === 0) {
    errors.push("a supported verdict requires evidence.");
  }
  if (claim.reproduction?.status === "reproduced" && independent === 0) {
    errors.push("a reproduced status requires an independent attempt.");
  }

  return { valid: errors.length === 0, errors, checks: 16 };
}

async function runCli() {
  const { readFile } = await import("node:fs/promises");
  const base = new URL(".", import.meta.url);
  const schema = JSON.parse(await readFile(new URL("claim-schema.json", base), "utf8"));
  const claim = JSON.parse(await readFile(new URL("example-claim.json", base), "utf8"));
  const result = verifyClaim(claim, schema);

  const missingFalsifier = structuredClone(claim);
  delete missingFalsifier.falsification;
  const badVerdict = structuredClone(claim);
  badVerdict.verdict = "proven-by-monad";
  const mutationsRejected =
    !verifyClaim(missingFalsifier, schema).valid &&
    !verifyClaim(badVerdict, schema).valid;

  console.log(JSON.stringify({
    example_valid: result.valid,
    checks: result.checks,
    controlled_mutations_rejected: mutationsRejected,
    errors: result.errors
  }, null, 2));

  if (!result.valid || !mutationsRejected) process.exitCode = 1;
}

if (typeof process !== "undefined" && process.argv?.[1] &&
    import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  runCli().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
