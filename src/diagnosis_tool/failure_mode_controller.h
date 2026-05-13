#ifndef FAILURE_MODE_CONTROLLER_H
#define FAILURE_MODE_CONTROLLER_H
#pragma once

#include <memory>
#include <unordered_map>
#include "failure_mode.h"

namespace diag {

enum class StepType {
    FALLBACK, // 回退
    NONLEAF,  // 非叶子，继续遍历下级故障模式
    LEAF      // 叶子，最终结果
};

class FailureModeController {
public:
    explicit FailureModeController(std::shared_ptr<FailureMode> failureModeInput): failureMode(failureModeInput) {}
    StepType GetNextStep();
    std::shared_ptr<FailureMode> GetFailureMode();

private:
    std::shared_ptr<FailureMode> failureMode;
    std::string logContent;
};

} // namespace diag
#endif