#pragma once

#include "../../failure_mode.h"

namespace diag {
class Urma0365UrmaCmdAllocJfcFunctionFailure : public FailureMode {
public:
    Urma0365UrmaCmdAllocJfcFunctionFailure() noexcept = default;
    bool IsValid(std::string &logContent) override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
} // namespace diag
