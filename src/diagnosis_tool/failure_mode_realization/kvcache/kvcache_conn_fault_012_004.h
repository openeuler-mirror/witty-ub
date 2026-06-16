#pragma once

#include "../../failure_mode.h"

namespace diag {
class KvcacheConnFault012_004 : public FailureMode {
public:
    KvcacheConnFault012_004() noexcept = default;
    bool IsValid() override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
} // namespace diag
