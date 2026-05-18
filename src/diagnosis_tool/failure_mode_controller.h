#ifndef FAILURE_MODE_CONTROLLER_H
#define FAILURE_MODE_CONTROLLER_H
#pragma once

#include <memory>
#include <unordered_map>
#include <unordered_set>
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
    void AddSubFailureModeInView(const std::string& subFailureModeId);
    void AddHitCount();
    std::unordered_set<std::string>& GetSubFailureModesInView();
    int GetHitCount();

private:
    std::shared_ptr<FailureMode> failureMode;
    std::unordered_set<std::string> subFailureModesInView;    // dynamic view; for urma
    int hitCount = 0;
};

} // namespace diag
#endif