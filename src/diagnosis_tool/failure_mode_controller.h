#pragma once

#include <memory>
#include <unordered_map>
#include "failure_mode.h"

namespace diag {

enum class StepType {
    Fallback,   // 回退
    NonLeaf,    // 非叶子，继续遍历下级故障模式
    Leaf        // 叶子，最终结果
};

class FailureModeController {
public:
    FailureModeController(std::shared_ptr<FailureMode> failureMode_)
        : failureMode(failureMode_){}
    StepType GetNextStep();
    std::shared_ptr<FailureMode> GetFailureMode();
private:
    std::shared_ptr<FailureMode> failureMode;
};

}