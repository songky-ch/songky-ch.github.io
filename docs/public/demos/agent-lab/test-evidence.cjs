const assert=require('node:assert/strict');
const {evaluate:e,calibration,modules}=require('./evidence-core.js');
let cases=0;for(const m of modules)for(let c=0;c<m.cases.length;c++){const r=e(m.id,c);assert.equal(r.events.length,3);assert.ok(Object.keys(r.result).length);cases++;}
assert.equal(cases,42);
assert.equal(e('rewrite',1).result.decision,'USE_ORIGINAL');assert.equal(e('rewrite',1).input.similarity_fixture,.99);
assert.deepEqual(e('rewrite',2).result.changed_fields,['timeout_seconds']);assert.equal(e('rewrite',3).result.decision,'ASK_USER');
for(const c of [1,2,3])assert.equal(e('pdf',c).result.normalized_limit_ms,null);
assert.equal(e('multi',1).result.accept_submission,false);assert.equal(e('multi',2).result.decision,'REVIEW_CONFLICT');
assert.equal(e('checkpoint',0).result.new_create_requests,0);assert.equal(e('checkpoint',1).result.next_action,'STOP_AND_RECONCILE');assert.equal(e('checkpoint',2).result.next_action,'REPLAY_SAME_OPERATION_KEY');
assert.equal(e('memory',1).result.acknowledged,false);assert.equal(e('memory',2).result.cache_update,'IGNORE_OLD_EVENT');
assert.equal(e('intent',3).result.fallback_rate,.4);assert.equal(e('intent',3).result.quality_cannot_be_inferred_from_rate,true);
assert.equal(e('rageval',0).result.recall,.5);assert.equal(e('rageval',0).result.faithfulness,.5);assert.equal(e('rageval',1).result.faithfulness,null);assert.equal(e('rageval',1).result.recall,.5);assert.equal(e('rageval',2).result.recall,null);assert.equal(e('rageval',3).result.unsupported_claim_rate,null);
assert.deepEqual(e('redtech',0).result,e('redtech',6).result);assert.deepEqual(e('redtech',0).input.semantic_input,e('redtech',6).input.semantic_input);
assert.equal(e('redtech',0).result.dimensions[1].score,0);for(const c of [1,2,3]){assert.equal(e('redtech',c).result.dimensions[1].score,null);assert.equal(e('redtech',c).result.coverage,2/3);}
assert.equal(e('redtech',4).result.requested,2);assert.equal(e('redtech',4).result.coverage,1);assert.equal(e('redtech',5).result.status,'REPLAY_REJECTED');
const k=calibration([0,0,1,2],[0,1,1,2]);assert.equal(k.agreement,.75);assert.equal(k.zero_recall,.5);assert.ok(Math.abs(k.linear_weighted_kappa-5/7)<1e-12);assert.deepEqual(k.matrix,[[1,1,0],[0,1,0],[0,0,1]]);
assert.equal(e('redtech',7).result.calibration.linear_weighted_kappa,null);assert.equal(e('redtech',7).result.calibration.zero_recall,null);
console.log(JSON.stringify({modules:modules.length,scenarios:cases,invariants:'passed',calibration:k}));
