import axios from 'axios';
import { IntentObject, ExecutionObject, DriftAnalysis } from '../schemas';

const REASONING_API = 'http://localhost:8000/analyze';

const scenarios: Array<{ label: string; intent: IntentObject; execution: ExecutionObject }> = [
  require('../../../shared/mock/scenario1_aligned.json'),
  require('../../../shared/mock/scenario2_scope_creep.json'),
  require('../../../shared/mock/scenario3_policy_violation.json'),
];

async function run() {
  for (const scenario of scenarios) {
    console.log(`\n${'─'.repeat(60)}`);
    console.log(`▶  ${scenario.label}`);
    console.log('─'.repeat(60));

    try {
      const response = await axios.post<DriftAnalysis>(REASONING_API, {
        intent: scenario.intent,
        execution: scenario.execution,
      });
      const result = response.data;
      console.log(`Drift detected : ${result.drift_detected}`);
      console.log(`Severity       : ${result.severity}`);
      console.log(`Reasoning      : ${result.reasoning}`);
    } catch (err: any) {
      const detail = err.response?.data ?? err.message;
      console.log(`ERROR          : ${JSON.stringify(detail)}`);
    }
  }
}

run().catch(console.error);
