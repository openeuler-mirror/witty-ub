#include <iostream>
#include "diagnosis_result.h"

namespace brpc {
    void DiagnosisResult::OutputResult() {
        cout << result;
    }
}