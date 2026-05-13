#pragma once

#include "../../failure_mode.h"

namespace diag {
class Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi : public FailureMode {
public:
    Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi() noexcept = default;
    bool IsValid(std::string &logContent) override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
} // namespace diag
