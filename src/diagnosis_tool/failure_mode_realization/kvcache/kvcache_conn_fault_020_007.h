#pragma once

#include "../../failure_mode.h"

namespace diag {
class KvcacheConnFault020_007 : public FailureMode {
public:
    KvcacheConnFault020_007() noexcept = default;
    bool IsValid(const std::vector<std::string> &fields) override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
} // namespace diag
