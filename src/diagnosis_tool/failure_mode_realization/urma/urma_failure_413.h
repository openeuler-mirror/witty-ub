#pragma once

#include "../../failure_mode.h"

namespace diag {
class UrmaFailure413 : public FailureMode {
public:
    UrmaFailure413() noexcept = default;
    bool IsValid() override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
} // namespace diag
