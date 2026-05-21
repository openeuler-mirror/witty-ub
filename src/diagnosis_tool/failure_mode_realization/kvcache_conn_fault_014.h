#pragma once

#include "../failure_mode.h"
namespace diag {
class KvcacheConnFault014 : public FailureMode {
public:
    KvcacheConnFault014() noexcept;
    bool IsValid() override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
}